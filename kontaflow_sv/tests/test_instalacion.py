import frappe
from frappe.tests import IntegrationTestCase


class TestInstalacion(IntegrationTestCase):
	"""Prueba mínima de KF-01: la app y su dependencia están instaladas en el sitio."""

	def test_apps_instaladas(self):
		apps = frappe.get_installed_apps()
		self.assertIn("kontaflow_sv", apps)
		self.assertIn("erpnext", apps)

	def test_modulo_registrado(self):
		self.assertTrue(frappe.db.exists("Module Def", "KontaFlow SV"))
