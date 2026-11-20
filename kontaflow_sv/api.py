import frappe

from kontaflow_sv.ingesta.servicio import ingestar_dte_compra as _ingestar_dte_compra
from kontaflow_sv.libro_compras.exportacion import generar_libro_compras


@frappe.whitelist(methods=["POST"])
def ingestar_dte_compra(company: str, dte_json: str) -> dict:
	"""Registra un DTE de compra (CCF v3 o v4, JSON) como borrador de la empresa indicada.

	La versión se toma de ``identificacion.version``; cualquier otra se rechaza.
	"""
	return _ingestar_dte_compra(company, dte_json)


@frappe.whitelist(methods=["POST"])
def exportar_libro_compras(company: str = "", mes: str = "") -> None:
	"""Descarga los borradores de CCF del período en un libro de Excel."""
	nombre, contenido = generar_libro_compras(company, mes)
	frappe.response.update(
		type="download",
		filename=nombre,
		filecontent=contenido,
		content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	)
