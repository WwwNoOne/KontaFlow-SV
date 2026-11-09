"""Ingesta manual de un DTE de compra (CCF v3) como borrador de ``KontaFlow DTE Compra``."""

from __future__ import annotations

import frappe
from frappe import _

from kontaflow_sv.ingesta.dte_compra import (
	DTEInvalido,
	digitos,
	hash_contenido,
	parsear_ccf_v3,
)

DOCTYPE = "KontaFlow DTE Compra"


def ingestar_dte_compra(company: str, crudo) -> dict:
	"""Registra el DTE como borrador y devuelve ``{"resultado", "name", "codigo_generacion"}``.

	``resultado`` es ``"creado"`` o ``"existente"``. Reintentar con el mismo contenido devuelve el
	registro existente sin tocarlo. El mismo ``codigoGeneracion`` con contenido distinto se rechaza.
	No crea asientos, facturas ni ningún otro documento contable.

	Debe ejecutarse en su propia transacción (una solicitud = un DTE). Si dos peticiones ingestan el
	mismo documento a la vez y la base de datos usa aislamiento por instantánea, el motor revierte la
	transacción de la que pierde, incluido cualquier trabajo previo hecho en ella. Un proceso por lotes
	debe confirmar (commit) después de cada DTE.
	"""
	if not company or not isinstance(company, str):
		frappe.throw(_("Indique la empresa."), title=_("DTE inválido"))
	# Mismo error si la empresa no existe o si el usuario no tiene acceso: no revela cuáles hay.
	if not _tiene_acceso(company):
		frappe.throw(_("No tiene acceso a la empresa indicada."), frappe.PermissionError)
	frappe.has_permission(DOCTYPE, "create", throw=True)

	try:
		datos = parsear_ccf_v3(crudo)
		nit_empresa = digitos(frappe.get_cached_value("Company", company, "tax_id"))
		if not nit_empresa:
			raise DTEInvalido("La empresa no tiene NIT configurado (campo Tax ID)")
		if datos["receptor"]["nit"] != nit_empresa:
			raise DTEInvalido("El receptor del DTE no corresponde a la empresa seleccionada")
	except DTEInvalido as e:
		frappe.throw(str(e), title=_("DTE inválido"))

	ident = datos["identificacion"]
	# Se conserva el contenido exactamente como llegó (incluido un BOM UTF-8) y el hash se calcula sobre
	# ese mismo texto: sha256(dte_original.encode("utf-8")) == dte_sha256, reproducible desde lo guardado.
	texto = crudo.decode("utf-8") if isinstance(crudo, (bytes, bytearray)) else crudo
	huella = hash_contenido(texto)
	abreviatura = frappe.get_cached_value("Company", company, "abbr")
	nombre = f"{abreviatura}-{ident['codigo_generacion']}"

	existente = _existente(nombre, huella)
	if existente:
		return existente

	doc = frappe.new_doc(DOCTYPE)
	doc.update(
		{
			"company": company,
			"estado": "Borrador",
			**{k: v for k, v in ident.items()},
			"emisor_nit": datos["emisor"]["nit"],
			"emisor_nrc": datos["emisor"]["nrc"],
			"emisor_nombre": datos["emisor"]["nombre"],
			"receptor_nit": datos["receptor"]["nit"],
			"receptor_nrc": datos["receptor"]["nrc"],
			"receptor_nombre": datos["receptor"]["nombre"],
			**datos["resumen"],
			"advertencias": "\n".join(datos["advertencias"]) or None,
			"dte_sha256": huella,
			"dte_original": texto,
		}
	)
	for item in datos["items"]:
		doc.append("items", item)
	for tributo in datos["tributos"]:
		doc.append("tributos", tributo)
	doc.flags.ingesta_validada = True

	try:
		doc.insert()
	except frappe.DuplicateEntryError, frappe.QueryDeadlockError:
		# Otra petición insertó el mismo documento entre la comprobación y la inserción. El choque llega
		# de dos formas, según el motor (ambas se prueban con peticiones simultáneas reales):
		#  - Aislamiento por instantánea (innodb_snapshot_isolation, por defecto desde MariaDB 11.6):
		#    error 1020 "Record has changed since last read", que Frappe expone como
		#    QueryDeadlockError. El motor REVIERTE LA TRANSACCIÓN COMPLETA y la siguiente lectura ya ve
		#    la fila confirmada.
		#  - Sin él: error 1062 (DuplicateEntryError). La transacción sigue con su instantánea anterior
		#    y no ve la fila de la otra petición, por eso se relee con una conexión nueva.
		existente = _existente(nombre, huella) or _existente(nombre, huella, conexion_propia=True)
		if existente:
			return existente
		raise  # un deadlock genuino, sin registro existente: se informa tal cual
	return {"resultado": "creado", "name": doc.name, "codigo_generacion": ident["codigo_generacion"]}


def _tiene_acceso(company: str) -> bool:
	"""``False`` si la empresa no existe o el usuario no puede leerla: ambos casos se tratan igual."""
	if not frappe.db.exists("Company", company):
		return False
	try:
		return bool(frappe.has_permission("Company", "read", company))
	except frappe.DoesNotExistError:
		return False


def _leer_registro(nombre: str, conexion_propia: bool):
	campos = ["name", "codigo_generacion", "dte_sha256"]
	if not conexion_propia:
		return frappe.db.get_value(DOCTYPE, nombre, campos, as_dict=True)

	# Conexión y transacción nuevas: ven lo ya confirmado, sin alterar la transacción del llamador.
	from frappe.database import get_db

	conf = frappe.local.conf
	db = get_db(
		socket=conf.db_socket,
		host=conf.db_host,
		port=conf.db_port,
		user=conf.db_user or conf.db_name,
		password=conf.db_password,
		cur_db_name=conf.db_name,
	)
	db.connect()
	try:
		return db.get_value(DOCTYPE, nombre, campos, as_dict=True)
	finally:
		db.close()


def _existente(nombre: str, huella: str, conexion_propia: bool = False) -> dict | None:
	registro = _leer_registro(nombre, conexion_propia)
	if not registro:
		return None
	if registro.dte_sha256 != huella:
		frappe.throw(
			_(
				"Ya existe un DTE con ese código de generación y un contenido distinto. "
				"No se sobrescribe el documento recibido."
			),
			frappe.DuplicateEntryError,
			title=_("DTE en conflicto"),
		)
	return {"resultado": "existente", "name": registro.name, "codigo_generacion": registro.codigo_generacion}
