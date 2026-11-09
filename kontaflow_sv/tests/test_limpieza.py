"""La limpieza de las pruebas exige alcance. No usan base de datos."""

from frappe.tests import UnitTestCase

from kontaflow_sv.tests.limpieza import borrar_dte


class TestLimpiezaAcotada(UnitTestCase):
	def test_se_niega_a_borrar_sin_alcance(self):
		for empresas in ([], [""], [None], ["KF Prueba A", ""]):
			with self.subTest(empresas=empresas):
				with self.assertRaises(ValueError):
					borrar_dte(empresas)
