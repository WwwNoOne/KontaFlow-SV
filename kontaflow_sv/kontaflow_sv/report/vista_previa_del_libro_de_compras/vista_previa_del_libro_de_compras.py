"""Reporte de solo lectura sobre los borradores del Libro de Compras."""

from decimal import Decimal

import frappe
from frappe import _

from kontaflow_sv.libro_compras.consulta import DOCTYPE
from kontaflow_sv.libro_compras.vista_previa import COLUMNAS, COLUMNAS_MONETARIAS, vista_previa

_CENTAVO = Decimal("0.01")


def execute(filters=None):
	filtros = filters or {}
	company = filtros.get("company")
	# La vista previa valida los filtros y permisos antes de leer cualquier importe.
	resultado = vista_previa(company, filtros.get("mes"))
	columnas = _columnas()
	if not resultado["filas"]:
		return columnas, [], _("No hay borradores de CCF para la empresa y el mes indicados")

	moneda = frappe.get_cached_value("Company", company, "default_currency")
	filas = []
	con_advertencias = 0
	for fila in resultado["filas"]:
		advertencias = fila["advertencias"]
		if advertencias:
			con_advertencias += 1
		filas.append(fila | _importes(fila, moneda) | {"advertencias": "; ".join(advertencias)})

	filas.append({"emisor_nombre": _("Total"), **_importes(resultado["totales"], moneda)})
	mensaje = None
	if con_advertencias == 1:
		mensaje = _("1 borrador tiene advertencias")
	elif con_advertencias > 1:
		mensaje = _("{0} borradores tienen advertencias").format(con_advertencias)
	return columnas, filas, mensaje


def _importes(fila, moneda):
	return {
		"currency": moneda,
		**{campo: fila[campo].quantize(_CENTAVO) for campo in COLUMNAS_MONETARIAS},
	}


def _columnas():
	etiquetas = {
		"name": (_("Borrador"), 180),
		"fecha_emision": (_("Fecha de emisión"), 120),
		"codigo_generacion": (_("Código de generación"), 285),
		"numero_control": (_("Número de control"), 250),
		"sello_recibido": (_("Sello de recepción"), 275),
		"emisor_nombre": (_("Proveedor"), 240),
		"emisor_nit": (_("NIT del emisor"), 135),
		"emisor_nrc": (_("NRC del emisor"), 125),
		"total_gravada": (_("Gravadas"), 145),
		"total_exenta": (_("Exentas"), 145),
		"total_no_suj": (_("No sujetas"), 145),
		"iva": (_("IVA del DTE"), 145),
		"advertencias": (_("Advertencias"), 440),
	}
	tipos = {
		"name": {"fieldtype": "Link", "options": DOCTYPE},
		"fecha_emision": {"fieldtype": "Date"},
		**{
			campo: {"fieldtype": "Currency", "options": "currency", "precision": 2}
			for campo in COLUMNAS_MONETARIAS
		},
	}
	return [
		{
			"fieldname": campo,
			"label": etiquetas[campo][0],
			"width": etiquetas[campo][1],
			**tipos.get(campo, {"fieldtype": "Data"}),
		}
		for campo in COLUMNAS
	]
