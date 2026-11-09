"""Limpieza acotada para las pruebas que dejan datos en la base de datos."""

import frappe

DOCTYPE = "KontaFlow DTE Compra"
HIJAS = ("KontaFlow DTE Compra Item", "KontaFlow DTE Compra Tributo")


def borrar_dte(empresas: list[str], nombres: list[str] | None = None) -> int:
	"""Borra los DTE de prueba (y sus filas hijas) de las ``empresas`` indicadas.

	Nunca toca registros de otras empresas: el alcance es obligatorio. Si se indican ``nombres``, solo
	se borran esos registros dentro de esas empresas. Devuelve cuántos DTE borró. No confirma la
	transacción: eso lo decide quien llama.
	"""
	if not empresas or not all(isinstance(e, str) and e for e in empresas):
		raise ValueError("borrar_dte exige indicar las empresas de prueba; no borra sin alcance")
	filtros = {"company": ["in", list(empresas)]}
	if nombres is not None:
		filtros["name"] = ["in", list(nombres)]
	registros = frappe.get_all(DOCTYPE, filters=filtros, pluck="name")
	if not registros:
		return 0
	for hija in HIJAS:
		frappe.db.delete(hija, {"parent": ["in", registros], "parenttype": DOCTYPE})
	frappe.db.delete(DOCTYPE, {"name": ["in", registros]})
	return len(registros)
