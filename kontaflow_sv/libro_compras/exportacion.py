"""Genera el Libro de Compras de los borradores autorizados, sin modificar el sitio."""

import re
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unicodedata import normalize

import frappe
from frappe import _
from openpyxl import load_workbook

from kontaflow_sv.libro_compras.consulta import DOCTYPE, consultar_borradores
from kontaflow_sv.libro_compras.vista_previa import COLUMNAS_MONETARIAS

_PLANTILLA = Path(__file__).with_name("plantilla_libro_compras.xlsx")
_PRIMER_DETALLE = 8
_FILA_TOTAL_PLANTILLA = 44
_FILAS_EJEMPLO = _FILA_TOTAL_PLANTILLA - _PRIMER_DETALLE - 1
_MESES = (
	"ENERO",
	"FEBRERO",
	"MARZO",
	"ABRIL",
	"MAYO",
	"JUNIO",
	"JULIO",
	"AGOSTO",
	"SEPTIEMBRE",
	"OCTUBRE",
	"NOVIEMBRE",
	"DICIEMBRE",
)
_TRIBUTOS = {"D1": "fovial", "C8": "cotrans"}
_CERO = Decimal(0)

# Columnas contables de A a T. None indica que no hay un dato aplicable al CCF.
COLUMNAS = (
	"correlativo",  # A
	"fecha_emision",  # B
	"numero_documento",  # C
	"emisor_nrc",  # D
	"emisor_nit",  # E
	"emisor_nombre",  # F
	"total_exenta",  # G
	None,  # H
	None,  # I
	"total_gravada",  # J
	None,  # K
	None,  # L
	"iva",  # M
	"fovial",  # N
	"cotrans",  # O
	None,  # P
	"iva_percibido",  # Q
	"total_compras",  # R
	"iva_retenido",  # S
	None,  # T
)
IMPORTES_DTE = (*COLUMNAS_MONETARIAS, "iva_percibido", "iva_retenido")


def generar_libro_compras(company: str, mes: str) -> tuple[str, bytes]:
	borradores = consultar_borradores(company, mes)
	frappe.has_permission(DOCTYPE, "export", throw=True)
	if not borradores:
		frappe.throw(_("No hay borradores de CCF para la empresa y el mes indicados"))

	importes, nrc = _leer_importes([borrador.name for borrador in borradores])
	filas = []
	for correlativo, borrador in enumerate(borradores, start=1):
		montos = _importes_con_signo(borrador.tipo_dte, importes[borrador.name])
		filas.append(
			{
				**borrador,
				**montos,
				"correlativo": correlativo,
				"numero_documento": _numero_documento(borrador),
			}
		)

	nombre_empresa, nit = frappe.db.get_value("Company", company, ["company_name", "tax_id"])
	cabecera = {
		"A1": nombre_empresa,
		"B3": _MESES[int(mes[5:]) - 1],
		"Q3": int(mes[:4]),
		"B4": nit,
		"Q4": nrc,
	}
	return _nombre_archivo(company, mes), _crear_xlsx(cabecera, filas)


def _numero_documento(borrador: dict) -> str:
	return borrador["codigo_generacion"]


def _signo(tipo_dte: str) -> int:
	if tipo_dte == "03":
		return 1
	raise frappe.ValidationError(f"No hay una regla de signo para el tipo de DTE {tipo_dte}.")


def _total_compras_ccf(importes: dict[str, Decimal]) -> Decimal:
	# G:M incluye exentas, gravadas y crédito fiscal. Las subcolumnas vacías aportan cero.
	return sum((importes.get(campo, _CERO) for campo in COLUMNAS[6:13]), _CERO)


def _importes_con_signo(tipo_dte: str, importes: dict[str, Decimal]) -> dict[str, Decimal]:
	signo = _signo(tipo_dte)
	montos = {campo: importe * signo for campo, importe in importes.items()}
	montos["total_compras"] = _total_compras_ccf(montos)
	return montos


def _leer_importes(nombres: list[str]) -> tuple[dict[str, dict[str, Decimal]], str | None]:
	# Lee como texto los DECIMAL de MariaDB y limita ambas consultas a nombres ya autorizados.
	columnas = ", ".join(f"CAST(`{campo}` AS CHAR) AS `{campo}`" for campo in IMPORTES_DTE)
	parametros = {"nombres": tuple(nombres)}
	filas = frappe.db.sql(
		f"SELECT `name`, `receptor_nrc`, {columnas} FROM `tab{DOCTYPE}` WHERE `name` IN %(nombres)s",
		parametros,
		as_dict=True,
	)
	importes = {fila.name: {campo: Decimal(fila[campo]) for campo in IMPORTES_DTE} for fila in filas}
	faltan = set(nombres) - importes.keys()
	if faltan:
		raise RuntimeError(f"No se pudieron leer los importes de {len(faltan)} DTE de la exportación.")

	for tributo in frappe.db.sql(
		"""
		SELECT `parent`, `codigo`, CAST(`valor` AS CHAR) AS `valor`
		FROM `tabKontaFlow DTE Compra Tributo`
		WHERE `parent` IN %(nombres)s AND `parenttype` = %(doctype)s AND `parentfield` = 'tributos'
		  AND `codigo` IN %(codigos)s
		""",
		parametros | {"doctype": DOCTYPE, "codigos": tuple(_TRIBUTOS)},
		as_dict=True,
	):
		montos = importes[tributo.parent]
		campo = _TRIBUTOS[tributo.codigo]
		montos[campo] = montos.get(campo, _CERO) + Decimal(tributo.valor)

	nrcs = {fila.receptor_nrc for fila in filas if fila.receptor_nrc}
	return importes, nrcs.pop() if len(nrcs) == 1 else None


def _nombre_archivo(company: str, mes: str) -> str:
	# La respuesta estándar de Frappe trata el nombre como ASCII con escapes.
	empresa = normalize("NFKD", company).encode("ascii", "ignore").decode("ascii")
	empresa = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", empresa).strip(" .") or "Empresa"
	return f"{empresa}_Libro de compras_{mes}_borradores.xlsx"


def _nota_no_sujetas(filas: list[dict]) -> str | None:
	importes = [fila["total_no_suj"] for fila in filas if fila["total_no_suj"] > _CERO]
	if importes:
		total = format(sum(importes, _CERO), ".2f").replace(".", ",")
		cantidad = len(importes)
		documentos = "documento" if cantidad == 1 else "documentos"
		return f"Compras no sujetas no incluidas: {cantidad} {documentos} por ${total}"
	return None


def _escribir_celda(celda, valor) -> None:
	if isinstance(valor, Decimal):
		# openpyxl escribe el lexema directamente como número en el XML, sin redondear a float.
		celda.value = format(valor, ".2f")
		celda.data_type = "n"
	else:
		celda.value = valor
		if isinstance(valor, str):
			celda.data_type = "s"  # Conserva el texto del DTE incluso si empieza con "=".


def _crear_xlsx(cabecera: dict, filas: list[dict]) -> bytes:
	libro = load_workbook(_PLANTILLA)
	hoja = libro["LibroCompras"]
	for coordenada, valor in cabecera.items():
		_escribir_celda(hoja[coordenada], valor)

	estilos_detalle = [celda._style for celda in hoja[_PRIMER_DETALLE]]
	desplazamiento = len(filas) - _FILAS_EJEMPLO
	# openpyxl desplaza las celdas del pie pero las dimensiones de fila se mueven aparte.
	dimensiones_pie = {
		fila: hoja.row_dimensions.pop(fila) for fila in list(hoja.row_dimensions) if fila >= _PRIMER_DETALLE
	}
	hoja.delete_rows(_PRIMER_DETALLE, _FILAS_EJEMPLO)
	hoja.insert_rows(_PRIMER_DETALLE, len(filas))
	# Las reglas de duplicados de la plantilla comparten el mismo estilo.
	formatos = hoja.conditional_formatting
	regla_duplicados = formatos[f"C{_PRIMER_DETALLE}"][0]
	for formato in list(formatos):
		reglas = formatos[formato]
		restantes = [regla for regla in reglas if regla.type != "duplicateValues"]
		if restantes:
			reglas[:] = restantes
		else:
			del formatos[str(formato.sqref)]
	ultimo_detalle = _PRIMER_DETALLE + len(filas) - 1
	formatos.add(f"C{_PRIMER_DETALLE}:C{ultimo_detalle}", regla_duplicados)

	for fila, dimension in dimensiones_pie.items():
		dimension.index = fila + desplazamiento
		hoja.row_dimensions[dimension.index] = dimension

	for numero, fila in enumerate(filas, start=_PRIMER_DETALLE):
		for columna, (campo, estilo) in enumerate(zip(COLUMNAS, estilos_detalle, strict=True), start=1):
			celda = hoja.cell(numero, columna)
			celda._style = estilo
			_escribir_celda(celda, fila.get(campo))

	numero_total = _FILA_TOTAL_PLANTILLA + desplazamiento
	for columna, campo in enumerate(COLUMNAS[6:], start=7):
		total = sum((fila.get(campo, _CERO) for fila in filas), _CERO)
		_escribir_celda(hoja.cell(numero_total, columna), total)

	nota = _nota_no_sujetas(filas)
	if nota:
		hoja.cell(numero_total + 5, 1, nota)

	with BytesIO() as salida:
		libro.save(salida)
		return salida.getvalue()
