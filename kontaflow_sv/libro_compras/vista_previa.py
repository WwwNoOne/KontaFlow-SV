"""Filas y totales de la vista previa del Libro de Compras sobre los borradores autorizados de un mes.

Solo lee. Los importes son los ya guardados en cada DTE y se manejan siempre como ``Decimal``.
"""

from __future__ import annotations

from decimal import Decimal

import frappe

from kontaflow_sv.libro_compras.consulta import DOCTYPE, consultar_borradores

# Columnas monetarias de la vista previa, en el orden en que se presentan
COLUMNAS_MONETARIAS = ("total_gravada", "total_exenta", "total_no_suj", "iva")

# Fila de la vista previa. Además de las columnas del libro, lleva la trazabilidad del DTE (código de
# generación, sello y NRC del proveedor); el sello o el NRC pueden venir vacíos (``None``).
COLUMNAS = (
	"name",
	"fecha_emision",
	"codigo_generacion",
	"numero_control",
	"sello_recibido",
	"emisor_nombre",
	"emisor_nit",
	"emisor_nrc",
	*COLUMNAS_MONETARIAS,
	"advertencias",
)


def vista_previa(company: str, mes: str) -> dict:
	"""``{"filas": [...], "totales": {...}}`` de los borradores de ``company`` en ``mes`` (``"AAAA-MM"``).

	Cada fila trae ``COLUMNAS``; los importes son ``Decimal`` y ``advertencias`` es una lista de textos
	(vacía si no hay). ``totales`` suma con ``Decimal`` las cuatro columnas monetarias de todas las filas.
	Los permisos, la validación del mes y el orden son los de ``consultar_borradores``.
	"""
	registros = consultar_borradores(company, mes)
	importes = _importes_exactos([r.name for r in registros])

	filas = []
	totales = dict.fromkeys(COLUMNAS_MONETARIAS, Decimal(0))
	for r in registros:
		fila = {columna: r.get(columna) for columna in COLUMNAS if columna not in COLUMNAS_MONETARIAS}
		fila["advertencias"] = (r.advertencias or "").splitlines()
		for columna in COLUMNAS_MONETARIAS:
			fila[columna] = importes[r.name][columna]
			totales[columna] += fila[columna]
		filas.append({columna: fila[columna] for columna in COLUMNAS})
	return {"filas": filas, "totales": totales}


def _importes_exactos(nombres: list[str]) -> dict[str, dict[str, Decimal]]:
	"""Importes guardados, leídos como texto decimal para no pasar por ``float``.

	Frappe convierte los ``DECIMAL`` de MariaDB en ``float`` y ``get_list`` no admite ``CAST``. Por eso
	los importes se leen aparte, **solo** para los nombres que ya devolvió la consulta autorizada.
	"""
	if not nombres:
		return {}
	columnas = ", ".join(f"CAST(`{c}` AS CHAR) AS `{c}`" for c in COLUMNAS_MONETARIAS)
	filas = frappe.db.sql(
		f"SELECT `name`, {columnas} FROM `tab{DOCTYPE}` WHERE `name` IN %(nombres)s",
		{"nombres": tuple(nombres)},
		as_dict=True,
	)
	importes = {f.name: {c: Decimal(f[c]) for c in COLUMNAS_MONETARIAS} for f in filas}
	faltan = set(nombres) - set(importes)
	if faltan:  # los DTE no se borran; si faltara alguno, mejor fallar que dar totales incompletos
		raise RuntimeError(f"No se pudieron leer los importes de {len(faltan)} DTE de la consulta.")
	return importes
