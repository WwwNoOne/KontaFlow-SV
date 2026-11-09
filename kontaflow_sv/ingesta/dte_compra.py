"""Lectura y validación de un DTE de compra: Comprobante de Crédito Fiscal (tipo 03) versión 3.

Este módulo no depende de Frappe: recibe el JSON tal como llegó y devuelve un diccionario ya
validado o lanza ``DTEInvalido``. Todos los importes se leen como ``Decimal`` directamente del texto
del JSON, sin pasar por ``float``, para no perder exactitud.

Reglas (contrastadas con 71 CCF v3 reales; los datos reales no forman parte del repositorio):

* Se rechaza lo estructuralmente inválido: tipo o versión distintos, campos obligatorios ausentes,
  importes negativos, no numéricos o con más decimales de los que se pueden guardar, fechas
  inválidas, ``codigoGeneracion`` o ``numeroControl`` mal formados.
* Se rechazan los cuadres aritméticos que se cumplen en todos los documentos reales:
  totales del resumen frente a la suma de los ítems, y monto total frente a subtotal más tributos
  (tolerancia de 0.01, la del propio redondeo del DTE). Los tributos informativos de la sección 3
  de CAT-015 (C5, C6, C7, 19, ...) no se suman.
* Los importes no pueden ser negativos, salvo ``noGravado`` y ``totalNoGravado`` (abonos).
* Límites: 2000 ítems (``maxItems`` del esquema de CCF v3) y 2 MB por documento (límite provisional
  de KontaFlow, no del esquema fiscal).
* Los cuadres que fallan en documentos reales (IVA al 13 %) no se rechazan: quedan como
  advertencias en el registro.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from decimal import Decimal

TIPO_DTE = "03"
VERSION = 3

TOLERANCIA = Decimal("0.01")
LIMITE_IMPORTE = Decimal("1e10")
DECIMALES_RESUMEN = 2
DECIMALES_ITEM = 8
MAX_BYTES = 2_000_000

# Catálogo CAT-015 de Hacienda (Catálogos de Facturación Electrónica). Los tributos del RESUMEN del DTE
# son de dos clases:
#  - Sección 1, "tributos aplicados por ítems reflejados en el resumen": se suman al monto total.
#  - Sección 3, "impuestos ad-valorem aplicados por ítem de uso informativo reflejados en el resumen":
#    se conservan en el registro pero NO se suman al monto total (el importe ya va en el precio).
# La sección 2 (A8, 57, 90, A6) son tributos del cuerpo del documento, no del resumen.
# El esquema JSON de CCF v3 acepta los códigos de las secciones 1 y 3 como tributos de un ítem
# (enumeración de 43 códigos = secciones 1 y 3 juntas), de modo que los 35 de la sección 3 aplican a v3.
TRIBUTOS_RESUMEN = frozenset({"20", "C3", "59", "71", "D1", "C8", "D5", "D4"})
TRIBUTOS_INFORMATIVOS = frozenset(
	{
		"C5", "C6", "C7", "19", "28", "31", "32", "33", "34", "35", "36", "37", "38", "39",
		"42", "43", "44", "50", "51", "52", "53", "54", "55", "58", "77", "78", "79", "85",
		"86", "91", "92", "A1", "A5", "A7", "A9",
	}
)  # fmt: skip

_RE_CODIGO_GENERACION = re.compile(r"^[0-9A-F]{8}(-[0-9A-F]{4}){3}-[0-9A-F]{12}$")
_RE_NUMERO_CONTROL = re.compile(r"^DTE-03-[A-Z0-9]{8}-[0-9]{15}$")
_RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_HORA = re.compile(r"^\d{2}:\d{2}:\d{2}$")

# Nombres con los que el sello de recepción llega en el JSON recibido. Solo se acepta como dato
# opcional cuando es texto; el resto de variantes (objetos de respuesta de Hacienda) se ignoran.
_CLAVES_SELLO = ("selloRecibido", "selloRecepcion", "SelloRecepcion")


class DTEInvalido(ValueError):
	"""El documento no cumple las reglas de ingesta. El mensaje indica el campo y el motivo."""


def digitos(valor) -> str:
	"""Solo los dígitos de un NIT/DUI, para comparar sin importar guiones ni espacios."""
	return re.sub(r"\D", "", str(valor or ""))


def normalizar_codigo_generacion(valor) -> str:
	return str(valor or "").strip().upper()


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------


def _rechazar_constante(nombre):
	raise DTEInvalido(f"El JSON contiene un valor no permitido: {nombre}")


def leer_json(crudo) -> dict:
	"""Decodifica el JSON con importes decimales exactos. ``crudo`` es ``str`` o ``bytes``."""
	if isinstance(crudo, (bytes, bytearray, str)) and len(crudo) > MAX_BYTES:
		raise DTEInvalido(f"El DTE supera el tamaño máximo de {MAX_BYTES // 1_000_000} MB")
	if isinstance(crudo, (bytes, bytearray)):
		try:
			texto = bytes(crudo).decode("utf-8-sig")
		except UnicodeDecodeError as e:
			raise DTEInvalido("El archivo no está codificado en UTF-8") from e
	elif isinstance(crudo, str):
		texto = crudo.lstrip("﻿")
	else:
		raise DTEInvalido("El contenido del DTE debe ser texto o bytes")

	try:
		datos = json.loads(texto, parse_float=Decimal, parse_constant=_rechazar_constante)
	except json.JSONDecodeError as e:
		raise DTEInvalido(f"JSON inválido: {e.msg} (línea {e.lineno}, columna {e.colno})") from e
	except RecursionError as e:
		raise DTEInvalido("JSON inválido: anidamiento excesivo") from e

	if not isinstance(datos, dict):
		raise DTEInvalido("El JSON debe ser un objeto")
	return datos


def hash_contenido(crudo) -> str:
	"""SHA-256 del contenido recibido, para distinguir un reenvío idéntico de uno distinto."""
	if isinstance(crudo, str):
		crudo = crudo.encode("utf-8")
	return hashlib.sha256(bytes(crudo)).hexdigest()


# ---------------------------------------------------------------------------
# Campos
# ---------------------------------------------------------------------------


def _objeto(padre: dict, clave: str, ruta: str) -> dict:
	valor = padre.get(clave)
	if not isinstance(valor, dict):
		raise DTEInvalido(f"Falta {ruta}{clave} o no es un objeto")
	return valor


def _texto(padre: dict, clave: str, ruta: str, *, obligatorio=True, max_largo=140) -> str | None:
	valor = padre.get(clave)
	if valor is None:
		if obligatorio:
			raise DTEInvalido(f"Falta {ruta}{clave}")
		return None
	if not isinstance(valor, str):
		raise DTEInvalido(f"{ruta}{clave} debe ser texto")
	valor = valor.strip()
	if obligatorio and not valor:
		raise DTEInvalido(f"{ruta}{clave} está vacío")
	if len(valor) > max_largo:
		raise DTEInvalido(f"{ruta}{clave} supera {max_largo} caracteres")
	return valor or None


def _entero(padre: dict, clave: str, ruta: str, *, obligatorio=True) -> int | None:
	valor = padre.get(clave)
	if valor is None:
		if obligatorio:
			raise DTEInvalido(f"Falta {ruta}{clave}")
		return None
	if isinstance(valor, bool) or not isinstance(valor, int):
		raise DTEInvalido(f"{ruta}{clave} debe ser un entero")
	return valor


def _importe(
	padre: dict,
	clave: str,
	ruta: str,
	*,
	decimales: int,
	obligatorio=False,
	positivo=False,
	permitir_negativo=False,
) -> Decimal:
	"""Importe exacto. Si falta y no es obligatorio vale 0. Nunca redondea: lo que no cabe se rechaza.

	``permitir_negativo`` es solo para los campos en que Hacienda admite el signo (abonos no gravados).
	"""
	valor = padre.get(clave)
	if valor is None:
		if obligatorio:
			raise DTEInvalido(f"Falta {ruta}{clave}")
		return Decimal(0)
	if isinstance(valor, bool) or not isinstance(valor, (int, Decimal)):
		raise DTEInvalido(f"{ruta}{clave} debe ser un número")
	valor = Decimal(valor)
	if valor < 0 and not permitir_negativo:
		raise DTEInvalido(f"{ruta}{clave} no puede ser negativo")
	if positivo and valor == 0:
		raise DTEInvalido(f"{ruta}{clave} debe ser mayor que cero")
	if abs(valor) >= LIMITE_IMPORTE:
		raise DTEInvalido(f"{ruta}{clave} excede el máximo permitido")
	if -valor.as_tuple().exponent > decimales:
		raise DTEInvalido(f"{ruta}{clave} tiene más de {decimales} decimales")
	# Frappe guarda los importes a través de float. Si el valor no sobrevive exactamente a esa ida y
	# vuelta (demasiados dígitos significativos), el campo guardaría un valor distinto del recibido.
	if Decimal(repr(float(valor))) != valor:
		raise DTEInvalido(f"{ruta}{clave} tiene demasiados dígitos para guardarse con exactitud")
	return valor


def _fecha(valor: str, ruta: str) -> datetime.date:
	if not _RE_FECHA.match(valor):
		raise DTEInvalido(f"{ruta} debe tener formato AAAA-MM-DD")
	try:
		return datetime.date.fromisoformat(valor)
	except ValueError as e:
		raise DTEInvalido(f"{ruta} no es una fecha válida") from e


def _hora(valor: str, ruta: str) -> str:
	if not _RE_HORA.match(valor):
		raise DTEInvalido(f"{ruta} debe tener formato HH:MM:SS")
	try:
		datetime.time.fromisoformat(valor)
	except ValueError as e:
		raise DTEInvalido(f"{ruta} no es una hora válida") from e
	return valor


# Largos máximos de ``nombre`` según el esquema de CCF v3.
_MAX_NOMBRE = {"emisor": 200, "receptor": 250}


def _parte(padre: dict, clave: str) -> dict:
	"""Emisor o receptor: se conservan solo los datos fiscales necesarios para el borrador."""
	ruta = f"{clave}."
	obj = _objeto(padre, clave, "")
	nit = _texto(obj, "nit", ruta, max_largo=20)
	if len(digitos(nit)) not in (9, 14):
		raise DTEInvalido(f"{ruta}nit debe tener 9 (DUI) o 14 dígitos")
	return {
		"nit": digitos(nit),
		"nrc": _texto(obj, "nrc", ruta, obligatorio=False, max_largo=20),
		"nombre": _texto(obj, "nombre", ruta, max_largo=_MAX_NOMBRE[clave]),
	}


# ---------------------------------------------------------------------------
# Documento completo
# ---------------------------------------------------------------------------


def parsear_ccf_v3(crudo) -> dict:
	"""Valida un CCF v3 y devuelve sus datos normalizados.

	Devuelve un diccionario con: ``identificacion``, ``emisor``, ``receptor``, ``resumen``,
	``items``, ``tributos`` y ``advertencias``. Lanza ``DTEInvalido`` si algo no cumple.
	"""
	datos = leer_json(crudo)

	ident = _objeto(datos, "identificacion", "")
	tipo = ident.get("tipoDte")
	if tipo != TIPO_DTE:
		raise DTEInvalido(f"Solo se admite el tipo de DTE {TIPO_DTE} (recibido: {tipo!r})")
	version = ident.get("version")
	if isinstance(version, bool) or version != VERSION or not isinstance(version, int):
		raise DTEInvalido(f"Solo se admite la versión {VERSION} del DTE {TIPO_DTE} (recibida: {version!r})")

	codigo = normalizar_codigo_generacion(_texto(ident, "codigoGeneracion", "identificacion."))
	if not _RE_CODIGO_GENERACION.match(codigo):
		raise DTEInvalido("identificacion.codigoGeneracion no es un UUID válido")
	numero_control = _texto(ident, "numeroControl", "identificacion.", max_largo=31)
	if not _RE_NUMERO_CONTROL.match(numero_control):
		raise DTEInvalido("identificacion.numeroControl no tiene el formato DTE-03-XXXXXXXX-###############")
	fecha = _fecha(_texto(ident, "fecEmi", "identificacion."), "identificacion.fecEmi")
	hora = _hora(_texto(ident, "horEmi", "identificacion."), "identificacion.horEmi")
	moneda = _texto(ident, "tipoMoneda", "identificacion.", max_largo=3)
	if moneda != "USD":
		raise DTEInvalido(f"Solo se admite moneda USD (recibida: {moneda!r})")
	ambiente = _texto(ident, "ambiente", "identificacion.", max_largo=2)
	if ambiente not in ("00", "01"):
		raise DTEInvalido(f"identificacion.ambiente debe ser 00 o 01 (recibido: {ambiente!r})")

	sello = None
	for clave in _CLAVES_SELLO:
		if isinstance(datos.get(clave), str) and datos[clave].strip():
			sello = datos[clave].strip()[:100]
			break

	emisor = _parte(datos, "emisor")
	receptor = _parte(datos, "receptor")

	# --- Ítems
	cuerpo = datos.get("cuerpoDocumento")
	if not isinstance(cuerpo, list) or not cuerpo:
		raise DTEInvalido("cuerpoDocumento debe ser una lista con al menos un ítem")
	if len(cuerpo) > 2000:
		raise DTEInvalido("cuerpoDocumento supera el máximo de 2000 ítems")

	items = []
	for pos, it in enumerate(cuerpo, start=1):
		ruta = f"cuerpoDocumento[{pos}]."
		if not isinstance(it, dict):
			raise DTEInvalido(f"cuerpoDocumento[{pos}] no es un objeto")
		tributos_item = it.get("tributos")
		if tributos_item is not None and (
			not isinstance(tributos_item, list) or not all(isinstance(t, str) for t in tributos_item)
		):
			raise DTEInvalido(f"{ruta}tributos debe ser una lista de códigos")
		items.append(
			{
				"num_item": _entero(it, "numItem", ruta),
				"tipo_item": _entero(it, "tipoItem", ruta),
				"codigo": _texto(it, "codigo", ruta, obligatorio=False),
				"descripcion": _texto(it, "descripcion", ruta, max_largo=1000),
				"uni_medida": _entero(it, "uniMedida", ruta),
				"cantidad": _importe(
					it, "cantidad", ruta, decimales=DECIMALES_ITEM, obligatorio=True, positivo=True
				),
				"precio_uni": _importe(it, "precioUni", ruta, decimales=DECIMALES_ITEM, obligatorio=True),
				"monto_descu": _importe(it, "montoDescu", ruta, decimales=DECIMALES_ITEM),
				"venta_no_suj": _importe(it, "ventaNoSuj", ruta, decimales=DECIMALES_ITEM),
				"venta_exenta": _importe(it, "ventaExenta", ruta, decimales=DECIMALES_ITEM),
				"venta_gravada": _importe(it, "ventaGravada", ruta, decimales=DECIMALES_ITEM),
				"no_gravado": _importe(
					it, "noGravado", ruta, decimales=DECIMALES_ITEM, permitir_negativo=True
				),
				"tributos": ",".join(tributos_item or []),
			}
		)
	numeros = [i["num_item"] for i in items]
	if len(set(numeros)) != len(numeros):
		raise DTEInvalido("cuerpoDocumento tiene números de ítem repetidos")

	# --- Resumen
	res = _objeto(datos, "resumen", "")

	def imp(clave, **kw):
		return _importe(res, clave, "resumen.", decimales=DECIMALES_RESUMEN, **kw)

	resumen = {
		"total_no_suj": imp("totalNoSuj"),
		"total_exenta": imp("totalExenta"),
		"total_gravada": imp("totalGravada", obligatorio=True),
		"sub_total_ventas": imp("subTotalVentas"),
		"total_descuentos": imp("totalDescu"),
		"sub_total": imp("subTotal", obligatorio=True),
		"iva_percibido": imp("ivaPerci1"),
		"iva_retenido": imp("ivaRete1"),
		"retencion_renta": imp("reteRenta"),
		"monto_total_operacion": imp("montoTotalOperacion", obligatorio=True, positivo=True),
		"total_no_gravado": imp("totalNoGravado", permitir_negativo=True),
		"total_pagar": imp("totalPagar", obligatorio=True),
	}
	descu_gravada = imp("descuGravada")

	lista_tributos = res.get("tributos")
	if lista_tributos is None:
		lista_tributos = []
	if not isinstance(lista_tributos, list):
		raise DTEInvalido("resumen.tributos debe ser una lista")
	tributos = []
	for pos, t in enumerate(lista_tributos, start=1):
		ruta = f"resumen.tributos[{pos}]."
		if not isinstance(t, dict):
			raise DTEInvalido(f"resumen.tributos[{pos}] no es un objeto")
		tributos.append(
			{
				"codigo": _texto(t, "codigo", ruta, max_largo=10),
				"descripcion": _texto(t, "descripcion", ruta, obligatorio=False, max_largo=150),
				"valor": _importe(t, "valor", ruta, decimales=DECIMALES_RESUMEN, obligatorio=True),
			}
		)

	# --- Cuadres que se cumplen en todos los documentos reales: se rechazan
	for campo_item, campo_resumen, etiqueta in (
		("venta_gravada", "total_gravada", "totalGravada"),
		("venta_exenta", "total_exenta", "totalExenta"),
		("venta_no_suj", "total_no_suj", "totalNoSuj"),
	):
		suma = sum((i[campo_item] for i in items), Decimal(0))
		if abs(suma - resumen[campo_resumen]) > TOLERANCIA:
			raise DTEInvalido(
				f"resumen.{etiqueta} ({resumen[campo_resumen]}) no cuadra con la suma de los ítems ({suma})"
			)
	suma_tributos = sum(
		(t["valor"] for t in tributos if t["codigo"] not in TRIBUTOS_INFORMATIVOS), Decimal(0)
	)
	esperado = resumen["sub_total"] + suma_tributos
	if abs(esperado - resumen["monto_total_operacion"]) > TOLERANCIA:
		raise DTEInvalido(
			f"resumen.montoTotalOperacion ({resumen['monto_total_operacion']}) no cuadra con "
			f"subTotal más tributos ({esperado})"
		)

	# --- Cuadres que fallan en documentos reales: advertencias, no rechazo
	advertencias = []
	iva = sum((t["valor"] for t in tributos if t["codigo"] == "20"), Decimal(0))
	iva_esperado = (resumen["total_gravada"] - descu_gravada) * Decimal("0.13")
	if abs(iva_esperado - iva) > TOLERANCIA:
		advertencias.append(
			f"El IVA (tributo 20) es {iva} y el 13 % de la venta gravada neta sería {iva_esperado:.4f}."
		)
	desconocidos = sorted({t["codigo"] for t in tributos} - TRIBUTOS_RESUMEN - TRIBUTOS_INFORMATIVOS)
	if desconocidos:
		advertencias.append(
			"Código(s) de tributo fuera de las secciones 1 y 3 de CAT-015, tratados como tributo que se suma: "
			+ ", ".join(desconocidos)
			+ "."
		)
	resumen["iva"] = iva

	return {
		"identificacion": {
			"codigo_generacion": codigo,
			"numero_control": numero_control,
			"sello_recibido": sello,
			"fecha_emision": fecha,
			"hora_emision": hora,
			"tipo_dte": TIPO_DTE,
			"version": VERSION,
			"moneda": moneda,
			"ambiente": ambiente,
		},
		"emisor": emisor,
		"receptor": receptor,
		"resumen": resumen,
		"items": items,
		"tributos": tributos,
		"advertencias": advertencias,
	}
