"""Empresas y usuarios de prueba con identificadores propios de cada ejecución.

Un nombre fijo no acredita que el registro sea de la prueba: en un sitio compartido puede existir ya una
empresa con ese nombre. Por eso cada ejecución usa un token propio, **aborta** si el nombre o la
abreviatura ya existen (no reutiliza ni modifica lo preexistente) y al terminar elimina únicamente lo que
ella misma creó.
"""

import json
import uuid
from dataclasses import dataclass
from decimal import Decimal

import frappe

from kontaflow_sv.tests.limpieza import borrar_dte
from kontaflow_sv.tests.utilidades import NIT_EMPRESA_A, a_json, codigo, construir_ccf


class FixtureYaExiste(RuntimeError):
	"""El nombre reservado para un fixture ya está en uso: no se toca lo preexistente."""


@dataclass(frozen=True)
class Empresa:
	name: str
	abbr: str
	nit: str | None


class FixturesDePrueba:
	"""Crea y registra lo que necesita una clase de pruebas; ``limpiar`` elimina solo lo registrado."""

	def __init__(self, token: str | None = None):
		self.token = (token or uuid.uuid4().hex[:6]).upper()
		self.empresas: list[Empresa] = []
		self.usuarios: list[str] = []

	def nombres_de_empresas(self) -> list[str]:
		return [e.name for e in self.empresas]

	def preparar(self):
		"""Datos base que ERPNext da por existentes al crear una Company (el sitio de prueba no pasó por el
		asistente). Si falta, se crea; si existe, no se toca.

		El tipo de almacén «Transit» es un dato obligatorio de ERPNext («required by the system»): el
		sistema no deja eliminarlo, así que no se intenta retirarlo. Es la única cosa que estas pruebas
		dejan en el sitio, y solo cuando faltaba."""
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)

	def empresa(self, etiqueta: str, nit: str | None) -> Empresa:
		nombre = f"KF Prueba {etiqueta} {self.token}"
		abreviatura = f"{etiqueta}{self.token}"
		if frappe.db.exists("Company", nombre) or frappe.db.exists("Company", {"abbr": abreviatura}):
			raise FixtureYaExiste(
				f"La empresa «{nombre}» (abreviatura {abreviatura}) ya existe; no se reutiliza ni se modifica."
			)
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": nombre,
				"abbr": abreviatura,
				"default_currency": "USD",
				"country": "El Salvador",
				"tax_id": nit,
			}
		).insert(ignore_permissions=True)
		empresa = Empresa(nombre, abreviatura, nit)
		self.empresas.append(empresa)
		return empresa

	def usuario(self, etiqueta: str, empresa: str, rol: str) -> str:
		"""Usuario con un único rol y permiso solo sobre ``empresa``. Devuelve su correo."""
		correo = f"kf.{etiqueta}.{self.token.lower()}@example.com"
		if frappe.db.exists("User", correo):
			raise FixtureYaExiste(f"El usuario {correo} ya existe; no se reutiliza ni se modifica.")
		frappe.get_doc(
			{
				"doctype": "User",
				"email": correo,
				"first_name": "Prueba",
				"send_welcome_email": 0,
				"roles": [{"role": rol}],
			}
		).insert(ignore_permissions=True)
		self.usuarios.append(correo)
		frappe.get_doc(
			{"doctype": "User Permission", "user": correo, "allow": "Company", "for_value": empresa}
		).insert(ignore_permissions=True)
		return correo

	def limpiar(self):
		"""Elimina lo que este objeto creó, en orden inverso, y nada más. No confirma la transacción."""
		for correo in reversed(self.usuarios):
			frappe.db.delete("User Permission", {"user": correo})
			if frappe.db.exists("User", correo):
				frappe.delete_doc("User", correo, force=True, ignore_permissions=True)
		for empresa in reversed(self.empresas):
			borrar_dte([empresa.name])
			if frappe.db.exists("Company", empresa.name):
				frappe.delete_doc("Company", empresa.name, force=True, ignore_permissions=True)
		self.usuarios.clear()
		self.empresas.clear()


def nc_con_importes(n=1, receptor_nit=NIT_EMPRESA_A, *, gravada="100.00", iva="12.00"):
	"""Nota de crédito v4 ficticia; el IVA por defecto permite comprobar advertencias."""
	return _nota_con_importes("05", n, receptor_nit, gravada, iva)


def nd_con_importes(n=2, receptor_nit=NIT_EMPRESA_A, *, gravada="100.00", iva="12.00"):
	"""Nota de débito v4 ficticia."""
	return _nota_con_importes("06", n, receptor_nit, gravada, iva)


def _nota_con_importes(tipo, n, receptor_nit, gravada, iva):
	doc = json.loads(construir_ccf(n, receptor_nit, version_dte=4), parse_float=Decimal)
	for clave in ("otrosDocumentos", "selloRecibido"):
		del doc[clave]
	doc["identificacion"].update(tipoDte=tipo, numeroControl=f"DTE-{tipo}-M001P001-{n:015d}", fusion=None)
	emisor = doc["emisor"]
	del emisor["codEstable"], emisor["codPuntoVenta"]
	receptor = doc["receptor"]
	receptor.update(tipoDocumento="36", numDocumento=receptor.pop("nit"))
	codigo_relacionado = codigo(500)
	doc["documentoRelacionado"] = [
		{
			"tipoDocumento": "03",
			"tipoGeneracion": 2,
			"numeroDocumento": codigo_relacionado,
			"fechaEmision": "2026-09-01",
		}
	]
	gravada, iva = Decimal(gravada), Decimal(iva)
	item = doc["cuerpoDocumento"][0]
	del item["psv"]
	item.update(
		cantidad=1,
		precioUni=gravada,
		ventaGravada=gravada,
		numeroDocumento=codigo_relacionado,
		ivaPerci=0,
		ivaRete=0,
		totalIva=iva,
	)
	doc["cuerpoDocumento"] = [item]
	resumen = doc["resumen"]
	for clave in (
		"subTotal",
		"descuNoSuj",
		"descuExenta",
		"descuGravada",
		"porcentajeDescuento",
		"saldoFavor",
		"pagos",
	):
		del resumen[clave]
	if tipo == "05":
		del resumen["numPagoElectronico"]
	resumen.update(
		totalGravada=gravada,
		subTotalVentas=gravada,
		totalIva=iva,
		codigoRetencionMH=None,
		tributos=[{"codigo": "20", "descripcion": "IVA", "valor": iva}],
		montoTotalOperacion=gravada + iva,
		totalPagar=gravada + iva,
	)
	return a_json(doc)
