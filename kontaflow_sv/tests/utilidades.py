"""Constructor de CCF v3 ficticios para las pruebas. Ningún dato corresponde a una persona o empresa real."""

import copy
import json
import uuid
from decimal import Decimal

# NIT de las empresas de prueba (14 dígitos, ficticios)
NIT_EMPRESA_A = "00000000000002"
NIT_EMPRESA_B = "00000000000003"
NIT_PROVEEDOR = "00000000000001"


def codigo(n: int) -> str:
	"""codigoGeneracion ficticio y determinista (UUID en mayúsculas)."""
	return str(uuid.UUID(int=n)).upper()


def a_json(valor) -> str:
	"""Serializa conservando los Decimal tal cual (``json.dumps`` los convertiría en texto)."""
	if isinstance(valor, Decimal):
		return str(valor)
	if isinstance(valor, dict):
		return "{" + ",".join(f"{json.dumps(k)}:{a_json(v)}" for k, v in valor.items()) + "}"
	if isinstance(valor, (list, tuple)):
		return "[" + ",".join(a_json(v) for v in valor) + "]"
	return json.dumps(valor, ensure_ascii=False)


def base_ccf(n: int = 1, receptor_nit: str = NIT_EMPRESA_A) -> dict:
	"""CCF v3 coherente: 2 ítems, IVA 13 %. Los importes incluyen 0.1 y 15.375 para detectar errores de coma flotante."""
	D = Decimal
	return {
		"identificacion": {
			"version": 3,
			"ambiente": "00",
			"tipoDte": "03",
			"numeroControl": f"DTE-03-M001P001-{n:015d}",
			"codigoGeneracion": codigo(n),
			"tipoModelo": 1,
			"tipoOperacion": 1,
			"tipoContingencia": None,
			"motivoContin": None,
			"fecEmi": "2026-09-04",
			"horEmi": "10:30:00",
			"tipoMoneda": "USD",
		},
		"emisor": {
			"nit": NIT_PROVEEDOR,
			"nrc": "100001",
			"nombre": "PROVEEDOR DE PRUEBA, S.A. DE C.V.",
			"codActividad": "62010",
			"descActividad": "Actividad ficticia de prueba",
			"nombreComercial": "PROVEEDOR PRUEBA",
			"tipoEstablecimiento": "01",
			"direccion": {"departamento": "01", "municipio": "01", "complemento": "Calle ficticia 123"},
			"telefono": "22220000",
			"correo": "proveedor@example.com",
			"codEstableMH": "M001",
			"codEstable": "M001",
			"codPuntoVentaMH": "P001",
			"codPuntoVenta": "P001",
		},
		"receptor": {
			"nit": receptor_nit,
			"nrc": "200002",
			"nombre": "EMPRESA DE PRUEBA, S.A. DE C.V.",
			"codActividad": "62020",
			"descActividad": "Actividad ficticia de prueba",
			"nombreComercial": "EMPRESA PRUEBA",
			"direccion": {"departamento": "01", "municipio": "01", "complemento": "Avenida ficticia 456"},
			"telefono": "22221111",
			"correo": "empresa@example.com",
		},
		"documentoRelacionado": None,
		"otrosDocumentos": None,
		"ventaTercero": None,
		"extension": None,
		"apendice": None,
		"cuerpoDocumento": [
			{
				"numItem": 1,
				"tipoItem": 1,
				"codigo": "A-1",
				"descripcion": "Artículo de prueba uno",
				"cantidad": D("3"),
				"uniMedida": 59,
				"precioUni": D("0.1"),
				"montoDescu": D("0"),
				"ventaNoSuj": D("0"),
				"ventaExenta": D("0"),
				"ventaGravada": D("0.3"),
				"tributos": ["20"],
				"noGravado": D("0"),
				"psv": D("0"),
				"numeroDocumento": None,
				"codTributo": None,
			},
			{
				"numItem": 2,
				"tipoItem": 1,
				"codigo": None,
				"descripcion": "Artículo de prueba dos",
				"cantidad": D("1.5"),
				"uniMedida": 59,
				"precioUni": D("10.25"),
				"montoDescu": D("0"),
				"ventaNoSuj": D("0"),
				"ventaExenta": D("0"),
				"ventaGravada": D("15.375"),
				"tributos": ["20"],
				"noGravado": D("0"),
				"psv": D("0"),
				"numeroDocumento": None,
				"codTributo": None,
			},
		],
		"resumen": {
			"totalNoSuj": D("0"),
			"totalExenta": D("0"),
			"totalGravada": D("15.68"),
			"subTotalVentas": D("15.68"),
			"descuNoSuj": D("0"),
			"descuExenta": D("0"),
			"descuGravada": D("0"),
			"porcentajeDescuento": D("0"),
			"totalDescu": D("0"),
			"tributos": [
				{"codigo": "20", "descripcion": "Impuesto al Valor Agregado 13%", "valor": D("2.04")}
			],
			"subTotal": D("15.68"),
			"ivaPerci1": D("0"),
			"ivaRete1": D("0"),
			"reteRenta": D("0"),
			"montoTotalOperacion": D("17.72"),
			"totalNoGravado": D("0"),
			"totalPagar": D("17.72"),
			"totalLetras": "DIECISIETE 72/100 DÓLARES",
			"saldoFavor": D("0"),
			"condicionOperacion": 1,
			"pagos": None,
			"numPagoElectronico": None,
		},
		"selloRecibido": "2026ABCDEF0123456789ABCDEF0123456789ABCD",
	}


def _a_v4(doc: dict) -> dict:
	"""Convierte el CCF v3 base en un CCF v4 (cambios según los esquemas JSON de Hacienda)."""
	doc["identificacion"]["version"] = 4
	for clave in ("codEstableMH", "codPuntoVentaMH", "tipoEstablecimiento"):
		del doc["emisor"][clave]  # el emisor de v4 ya no los trae
	del doc["extension"]  # v4 eliminó la sección extension
	for parte in ("emisor", "receptor"):
		doc[parte]["direccion"]["distrito"] = "01"  # v4 añadió el distrito a la dirección
	resumen = doc["resumen"]
	resumen["ivaPerci"] = resumen.pop("ivaPerci1")
	resumen["ivaRete"] = resumen.pop("ivaRete1")
	del resumen["reteRenta"]  # v4 eliminó la retención de renta del resumen
	resumen["observaciones"] = None
	return doc


def construir_ccf(n: int = 1, receptor_nit: str = NIT_EMPRESA_A, version_dte: int = 3, **cambios) -> str:
	"""Devuelve el JSON del CCF (``version_dte`` 3 o 4). ``cambios`` usa rutas con punto, p. ej.
	``{"resumen.totalPagar": Decimal("1")}``.

	Un valor ``ELIMINAR`` quita la clave; ``cuerpoDocumento.0.cantidad`` llega a un ítem por posición.
	En v4 el resumen usa ``ivaPerci`` e ``ivaRete`` (v3: ``ivaPerci1`` e ``ivaRete1``).
	"""
	datos = copy.deepcopy(base_ccf(n, receptor_nit))
	if version_dte == 4:
		datos = _a_v4(datos)
	elif version_dte != 3:
		raise ValueError(f"version_dte debe ser 3 o 4 (recibida: {version_dte})")
	for ruta, valor in cambios.items():
		partes = ruta.split(".")
		destino = datos
		for p in partes[:-1]:
			destino = destino[int(p)] if isinstance(destino, list) else destino[p]
		ultima = int(partes[-1]) if isinstance(destino, list) else partes[-1]
		if valor is ELIMINAR:
			del destino[ultima]
		else:
			destino[ultima] = valor
	return a_json(datos)


class _Eliminar:
	def __repr__(self):
		return "ELIMINAR"


ELIMINAR = _Eliminar()


# Copia independiente de CAT-015 (Catálogos de Facturación Electrónica de Hacienda), para que un cambio
# accidental en las constantes del parser no pase inadvertido.
CAT_015_SECCION_1 = ("20", "C3", "59", "71", "D1", "C8", "D5", "D4")  # tributos del resumen: se suman
CAT_015_SECCION_2 = ("A8", "57", "90", "A6")  # del cuerpo del documento, no del resumen
CAT_015_SECCION_3 = (  # de uso informativo: no se suman
	"C5", "C6", "C7", "19", "28", "31", "32", "33", "34", "35", "36", "37", "38", "39", "42", "43",
	"44", "50", "51", "52", "53", "54", "55", "58", "77", "78", "79", "85", "86", "91", "92", "A1",
	"A5", "A7", "A9",
)  # fmt: skip
