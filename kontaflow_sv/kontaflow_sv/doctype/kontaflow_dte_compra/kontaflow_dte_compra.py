import json

import frappe
from frappe import _
from frappe.model.document import Document

_CAMPOS_META = {
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
	"parent",
	"parenttype",
	"parentfield",
	"doctype",
}


def _firma(doc) -> str:
	"""Contenido del documento y de sus filas, para detectar cualquier cambio posterior a la ingesta."""
	datos = {k: v for k, v in doc.as_dict(no_nulls=False).items() if k not in _CAMPOS_META}
	for clave, valor in list(datos.items()):
		if isinstance(valor, list):
			datos[clave] = [{k: v for k, v in fila.items() if k not in _CAMPOS_META} for fila in valor]
	return json.dumps(datos, default=str, sort_keys=True)


class KontaFlowDTECompra(Document):
	"""DTE de compra recibido. Es un borrador: no genera asientos ni facturas.

	El nombre es ``<abreviatura de la empresa>-<codigoGeneracion>``. La abreviatura de Company es
	única, así que la clave primaria de la base de datos garantiza un solo registro por
	(empresa, codigoGeneracion), incluso con inserciones concurrentes.
	"""

	def autoname(self):
		abreviatura = frappe.get_cached_value("Company", self.company, "abbr")
		self.name = f"{abreviatura}-{self.codigo_generacion}"

	def validate(self):
		# Los datos fiscales salen del parser, no de la captura manual: sin esa marca no se crea ni se edita.
		if self.is_new():
			if not self.flags.ingesta_validada:
				frappe.throw(
					_("Los DTE de compra se registran mediante la ingesta, no se crean a mano."),
					title=_("Registro no permitido"),
				)
		else:
			antes = self.get_doc_before_save()
			if antes is not None and _firma(antes) != _firma(self):
				frappe.throw(
					_("El DTE recibido no se puede modificar: se conserva tal como llegó."),
					title=_("Registro no permitido"),
				)
		if self.estado != "Borrador":
			frappe.throw(_("En esta etapa el DTE solo puede estar en Borrador."))
