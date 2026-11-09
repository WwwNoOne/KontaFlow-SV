import frappe

from kontaflow_sv.ingesta.servicio import ingestar_dte_compra as _ingestar_dte_compra


@frappe.whitelist(methods=["POST"])
def ingestar_dte_compra(company: str, dte_json: str) -> dict:
	"""Registra un DTE de compra (CCF v3 o v4, JSON) como borrador de la empresa indicada.

	La versión se toma de ``identificacion.version``; cualquier otra se rechaza.
	"""
	return _ingestar_dte_compra(company, dte_json)
