"""Los fixtures de las pruebas no reutilizan, modifican ni borran lo que ya existe en el sitio.

Regresión de KF-02-R: las pruebas buscaban una ``Company`` por un nombre fijo, la reutilizaban (incluso le
cambiaban el NIT) y luego la borraban con ``force``. Un nombre fijo no acredita que el registro sea de la
prueba. Estas pruebas no confirman nada: todo se revierte al terminar la clase.
"""

import frappe
from frappe.tests import IntegrationTestCase

from kontaflow_sv.ingesta import servicio
from kontaflow_sv.tests.fixtures import FixturesDePrueba, FixtureYaExiste
from kontaflow_sv.tests.utilidades import NIT_EMPRESA_A, construir_ccf

DOCTYPE = "KontaFlow DTE Compra"
NIT_PREEXISTENTE = "00000000000008"
TOKEN = "COLISN"  # fuerza que el fixture quiera usar justo el nombre de la empresa preexistente


class TestFixturesSeguros(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.preparador = FixturesDePrueba(token="PREPAR")
		cls.preparador.preparar()  # el tipo de almacén que ERPNext exige al crear una Company

	def setUp(self):
		# Dentro de una clase los datos de una prueba persisten en la siguiente: cada una se revierte
		self.addCleanup(frappe.db.rollback, save_point="fixtures_seguros")
		frappe.db.savepoint("fixtures_seguros")

	def _empresa_preexistente(self, nombre=None, abreviatura=None):
		"""Una empresa que 'ya estaba en el sitio', creada fuera de la fábrica bajo prueba."""
		nombre = nombre or f"KF Prueba A {TOKEN}"
		abreviatura = abreviatura or f"A{TOKEN}"
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": nombre,
				"abbr": abreviatura,
				"default_currency": "USD",
				"country": "El Salvador",
				"tax_id": NIT_PREEXISTENTE,
			}
		).insert(ignore_permissions=True)
		dte = servicio.ingestar_dte_compra(nombre, construir_ccf(80, receptor_nit=NIT_PREEXISTENTE))
		return nombre, dte["name"]

	def _intacta(self, nombre, dte):
		self.assertTrue(frappe.db.exists("Company", nombre), "la empresa preexistente desapareció")
		self.assertEqual(
			frappe.db.get_value("Company", nombre, "tax_id"), NIT_PREEXISTENTE, "se modificó su NIT"
		)
		self.assertTrue(frappe.db.exists(DOCTYPE, dte), "su DTE desapareció")
		self.assertEqual(frappe.db.count("KontaFlow DTE Compra Item", {"parent": dte}), 2)
		self.assertEqual(frappe.db.count("KontaFlow DTE Compra Tributo", {"parent": dte}), 1)

	def test_empresa_preexistente_con_el_mismo_nombre_no_se_reutiliza_ni_se_modifica(self):
		nombre, dte = self._empresa_preexistente()
		fx = FixturesDePrueba(token=TOKEN)
		with self.assertRaises(FixtureYaExiste):
			fx.empresa("A", NIT_EMPRESA_A)  # querría usar el nombre y el NIT de otra empresa
		self.assertEqual(fx.empresas, [], "no debe registrar como suya una empresa que no creó")
		fx.limpiar()
		self._intacta(nombre, dte)

	def test_empresa_preexistente_con_la_misma_abreviatura_tampoco(self):
		nombre, dte = self._empresa_preexistente(nombre="Otra empresa cualquiera", abreviatura=f"A{TOKEN}")
		fx = FixturesDePrueba(token=TOKEN)
		with self.assertRaises(FixtureYaExiste):
			fx.empresa("A", NIT_EMPRESA_A)  # el nombre difiere, la abreviatura coincide
		fx.limpiar()
		self._intacta(nombre, dte)

	def test_empresa_preexistente_con_el_mismo_nombre_y_otra_abreviatura_tampoco(self):
		nombre, dte = self._empresa_preexistente(abreviatura="OTRAABR")
		fx = FixturesDePrueba(token=TOKEN)
		with self.assertRaises(FixtureYaExiste):
			fx.empresa("A", NIT_EMPRESA_A)  # la abreviatura es libre, pero el nombre ya está en uso
		self.assertEqual(fx.empresas, [])
		fx.limpiar()
		self._intacta(nombre, dte)

	def test_usuario_preexistente_no_se_reutiliza_ni_se_modifica(self):
		correo = f"kf.a.{TOKEN.lower()}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": correo,
				"first_name": "Preexistente",
				"send_welcome_email": 0,
				"roles": [{"role": "Accounts User"}],
			}
		).insert(ignore_permissions=True)
		fx = FixturesDePrueba(token=TOKEN)
		empresa = fx.empresa("B", NIT_EMPRESA_A)
		with self.assertRaises(FixtureYaExiste):
			fx.usuario("a", empresa.name, "System Manager")
		fx.limpiar()
		self.assertTrue(frappe.db.exists("User", correo), "se borró un usuario preexistente")
		self.assertEqual(
			[r.role for r in frappe.get_doc("User", correo).roles],
			["Accounts User"],
			"se modificaron sus roles",
		)
		self.assertFalse(frappe.db.exists("Company", empresa.name), "debía borrar la empresa que sí creó")

	def test_limpiar_solo_elimina_lo_que_creo_el_fixture(self):
		preexistente, dte = self._empresa_preexistente()
		fx = FixturesDePrueba(token="PROPIO")
		propia = fx.empresa("A", NIT_EMPRESA_A)
		propio = servicio.ingestar_dte_compra(propia.name, construir_ccf(1))
		self.assertTrue(frappe.db.exists(DOCTYPE, propio["name"]))
		fx.limpiar()
		self.assertFalse(frappe.db.exists("Company", propia.name))
		self.assertFalse(frappe.db.exists(DOCTYPE, propio["name"]))
		self.assertEqual(frappe.db.count("KontaFlow DTE Compra Item", {"parent": propio["name"]}), 0)
		self._intacta(preexistente, dte)

	def test_limpiar_funciona_cuando_el_fixture_creo_el_tipo_de_almacen(self):
		"""Si «Transit» faltaba y lo creó el fixture, limpiar no debe fallar (ERPNext no deja borrarlo)."""
		frappe.db.delete("Warehouse Type", {"name": "Transit"})  # se revierte con el savepoint de la prueba
		fx = FixturesDePrueba(token="NUEVO1")
		fx.preparar()
		self.assertTrue(frappe.db.exists("Warehouse Type", "Transit"))
		empresa = fx.empresa("A", NIT_EMPRESA_A)
		fx.limpiar()  # antes lanzaba ValidationError y dejaba la limpieza a medias
		self.assertFalse(frappe.db.exists("Company", empresa.name))

	def test_dos_ejecuciones_no_comparten_nombres(self):
		a, b = FixturesDePrueba(), FixturesDePrueba()
		self.assertNotEqual(a.token, b.token)
		ea, eb = a.empresa("A", NIT_EMPRESA_A), b.empresa("A", NIT_EMPRESA_A)
		self.assertNotEqual(ea.name, eb.name)
		self.assertNotEqual(ea.abbr, eb.abbr)
		a.limpiar()
		b.limpiar()
