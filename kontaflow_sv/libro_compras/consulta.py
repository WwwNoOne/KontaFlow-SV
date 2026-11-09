"""Consulta de los borradores de DTE de compra de una empresa en un mes (base de la vista previa del
Libro de Compras). Solo lee: no crea, modifica ni borra registros."""

from __future__ import annotations

import re
from datetime import date

import frappe
from frappe import _

from kontaflow_sv.ingesta.servicio import _tiene_acceso

DOCTYPE = "KontaFlow DTE Compra"

# Tipo de DTE que entra en la vista previa: Comprobante de Crédito Fiscal (v3 y v4). Las notas de
# crédito y débito y el sujeto excluido se incorporarán por tipo, con sus propias reglas.
TIPOS_DTE = ("03",)

CAMPOS = (
	"name",
	"company",
	"tipo_dte",
	"version",
	"codigo_generacion",
	"numero_control",
	"fecha_emision",
)

_MES = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def periodo_del_mes(mes) -> tuple[date, date]:
	"""``"AAAA-MM"`` → (primer día del mes, primer día del mes siguiente). El segundo queda excluido."""
	if not isinstance(mes, str) or not _MES.fullmatch(mes):
		frappe.throw(
			_("Indique el mes con el formato AAAA-MM, por ejemplo 2026-09."), title=_("Mes inválido")
		)
	anio, numero = int(mes[:4]), int(mes[5:])
	try:
		inicio = date(anio, numero, 1)
		fin = date(anio + 1, 1, 1) if numero == 12 else date(anio, numero + 1, 1)
	except ValueError:  # año 0000 o diciembre de 9999
		frappe.throw(_("El mes {0} está fuera del rango admitido.").format(mes), title=_("Mes inválido"))
	return inicio, fin


def consultar_borradores(company: str, mes: str) -> list[dict]:
	"""Borradores de CCF de ``company`` con fecha de emisión en ``mes`` (``"AAAA-MM"``).

	Orden estable: fecha de emisión y, a igualdad, nombre del documento. Aplica los permisos del
	usuario: sin acceso a la empresa (o si no existe) se lanza ``frappe.PermissionError`` con el mismo
	mensaje en ambos casos; sin permiso de lectura sobre el DocType, también.
	"""
	if not company or not isinstance(company, str):
		frappe.throw(_("Indique la empresa."), title=_("Empresa obligatoria"))
	inicio, fin = periodo_del_mes(mes)
	if not _tiene_acceso(company):
		frappe.throw(_("No tiene acceso a la empresa indicada."), frappe.PermissionError)
	frappe.has_permission(DOCTYPE, "read", throw=True)

	# get_list (no get_all) aplica de nuevo los permisos del usuario sobre cada registro.
	return frappe.get_list(
		DOCTYPE,
		filters=[
			["company", "=", company],
			["estado", "=", "Borrador"],
			["tipo_dte", "in", TIPOS_DTE],
			["fecha_emision", ">=", inicio],
			["fecha_emision", "<", fin],
		],
		fields=list(CAMPOS),
		order_by="fecha_emision asc, name asc",
		limit=0,  # todas las filas del período, sin paginar (explícito: versiones previas paginaban a 20)
	)
