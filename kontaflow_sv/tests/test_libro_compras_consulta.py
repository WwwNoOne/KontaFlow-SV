"""Pruebas de la consulta de borradores por empresa y mes (KF-04.1). Datos ficticios."""

from datetime import date

import frappe
from frappe.tests import IntegrationTestCase

from kontaflow_sv.ingesta import servicio
from kontaflow_sv.libro_compras import consulta
from kontaflow_sv.tests.fixtures import FixturesDePrueba
from kontaflow_sv.tests.limpieza import borrar_dte
from kontaflow_sv.tests.utilidades import NIT_EMPRESA_A, NIT_EMPRESA_B, construir_ccf

DOCTYPE = "KontaFlow DTE Compra"


class TestPeriodoDelMes(IntegrationTestCase):
	def test_limites_del_mes(self):
		casos = {
			"2026-09": (date(2026, 9, 1), date(2026, 10, 1)),
			"2026-12": (date(2026, 12, 1), date(2027, 1, 1)),
			"2026-01": (date(2026, 1, 1), date(2026, 2, 1)),
			"2028-02": (date(2028, 2, 1), date(2028, 3, 1)),
		}
		for mes, esperado in casos.items():
			with self.subTest(mes=mes):
				self.assertEqual(consulta.periodo_del_mes(mes), esperado)

	def test_mes_invalido(self):
		for mes in (
			"2026-13",
			"2026-00",
			"2026-9",
			"26-09",
			"2026/09",
			"2026-09-01",
			" 2026-09",
			"2026-09\n",
			"",
			None,
			202609,
			date(2026, 9, 1),
			"0000-01",
			"9999-12",
		):
			with self.subTest(mes=mes):
				with self.assertRaises(frappe.ValidationError):
					consulta.periodo_del_mes(mes)


class TestConsultaDeBorradores(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Empresas y usuarios propios de esta ejecución; al terminar se elimina solo lo creado aquí.
		cls.fx = FixturesDePrueba()
		cls.addClassCleanup(cls.fx.limpiar)
		cls.fx.preparar()
		cls.empresa_a = cls.fx.empresa("A", NIT_EMPRESA_A).name
		cls.empresa_b = cls.fx.empresa("B", NIT_EMPRESA_B).name
		cls.gerente_a = cls.fx.usuario("gerente", cls.empresa_a, "Accounts Manager")
		cls.contador_a = cls.fx.usuario("contador", cls.empresa_a, "Accounts User")
		cls.sistema_a = cls.fx.usuario("sistema", cls.empresa_a, "System Manager")
		# Puede leer la empresa (ERPNext lo concede a Purchase User) pero no el DocType de los DTE
		cls.compras_a = cls.fx.usuario("compras", cls.empresa_a, "Purchase User")

	def setUp(self):
		frappe.set_user("Administrator")
		borrar_dte(self.fx.nombres_de_empresas())

	def tearDown(self):
		frappe.set_user("Administrator")

	def _ingestar(self, n: int, fecha: str, empresa=None, version: int = 3) -> str:
		empresa = empresa or self.empresa_a
		nit = NIT_EMPRESA_A if empresa == self.empresa_a else NIT_EMPRESA_B
		texto = construir_ccf(n, receptor_nit=nit, version_dte=version, **{"identificacion.fecEmi": fecha})
		return servicio.ingestar_dte_compra(empresa, texto)["name"]

	def _nombres(self, empresa, mes) -> list[str]:
		return [f.name for f in consulta.consultar_borradores(empresa, mes)]

	# --- período
	def test_limites_del_mes_en_la_base_de_datos(self):
		self._ingestar(1, "2026-08-31")
		primero = self._ingestar(2, "2026-09-01")
		ultimo = self._ingestar(3, "2026-09-30")
		self._ingestar(4, "2026-10-01")
		self.assertEqual(self._nombres(self.empresa_a, "2026-09"), [primero, ultimo])

	def test_diciembre_no_incluye_enero_del_anio_siguiente(self):
		diciembre = self._ingestar(1, "2026-12-31")
		enero = self._ingestar(2, "2027-01-01")
		self.assertEqual(self._nombres(self.empresa_a, "2026-12"), [diciembre])
		self.assertEqual(self._nombres(self.empresa_a, "2027-01"), [enero])

	def test_periodo_vacio(self):
		self._ingestar(1, "2026-09-15")
		self.assertEqual(consulta.consultar_borradores(self.empresa_a, "2026-07"), [])

	def test_mes_invalido_no_consulta(self):
		self._ingestar(1, "2026-09-15")
		for mes in ("2026-13", "2026-9", None, ""):
			with self.subTest(mes=mes):
				with self.assertRaises(frappe.ValidationError):
					consulta.consultar_borradores(self.empresa_a, mes)

	def test_empresa_obligatoria(self):
		for empresa in ("", None):
			with self.subTest(empresa=empresa):
				with self.assertRaises(frappe.ValidationError) as cm:
					consulta.consultar_borradores(empresa, "2026-09")
				self.assertNotIsInstance(cm.exception, frappe.PermissionError)

	# --- contenido y orden
	def test_incluye_v3_y_v4(self):
		v3 = self._ingestar(1, "2026-09-10", version=3)
		v4 = self._ingestar(2, "2026-09-11", version=4)
		filas = consulta.consultar_borradores(self.empresa_a, "2026-09")
		self.assertEqual([(f.name, f.version) for f in filas], [(v3, 3), (v4, 4)])
		for fila in filas:
			self.assertEqual(fila.company, self.empresa_a)
			self.assertEqual(fila.tipo_dte, "03")
			self.assertEqual(set(fila), set(consulta.CAMPOS))

	def test_orden_por_fecha_y_nombre_independiente_del_orden_de_ingesta(self):
		# Se ingesta al revés del orden esperado para que el orden de creación no lo enmascare
		tarde = self._ingestar(1, "2026-09-20")
		mismo_dia = [self._ingestar(n, "2026-09-05") for n in (4, 3, 2)]
		esperado = [*sorted(mismo_dia), tarde]
		self.assertEqual(self._nombres(self.empresa_a, "2026-09"), esperado)
		self.assertEqual(sorted(mismo_dia)[0], mismo_dia[-1])  # el desempate por nombre sí actúa

	def test_sin_limite_de_filas(self):
		nombres = [self._ingestar(n, "2026-09-15") for n in range(1, 26)]
		self.assertEqual(self._nombres(self.empresa_a, "2026-09"), sorted(nombres))

	def test_la_consulta_no_modifica_registros(self):
		nombre = self._ingestar(1, "2026-09-15")
		antes = frappe.db.get_value(DOCTYPE, nombre, ["modified", "dte_sha256"])
		consulta.consultar_borradores(self.empresa_a, "2026-09")
		self.assertEqual(frappe.db.get_value(DOCTYPE, nombre, ["modified", "dte_sha256"]), antes)
		self.assertEqual(frappe.db.count(DOCTYPE, {"company": self.empresa_a}), 1)

	# --- aislamiento y permisos
	def test_aislamiento_entre_empresas(self):
		propio = self._ingestar(1, "2026-09-15")
		ajeno = self._ingestar(1, "2026-09-15", empresa=self.empresa_b)  # mismo código, otra empresa
		self.assertEqual(self._nombres(self.empresa_a, "2026-09"), [propio])
		self.assertEqual(self._nombres(self.empresa_b, "2026-09"), [ajeno])

	def test_usuarios_autorizados_ven_su_empresa(self):
		nombre = self._ingestar(1, "2026-09-15")
		self._ingestar(2, "2026-09-15", empresa=self.empresa_b)
		for usuario in (self.gerente_a, self.contador_a, self.sistema_a):
			with self.subTest(usuario=usuario):
				frappe.set_user(usuario)
				self.assertEqual(self._nombres(self.empresa_a, "2026-09"), [nombre])

	def test_empresa_ajena_o_inexistente_da_el_mismo_error_de_permiso(self):
		self._ingestar(1, "2026-09-15", empresa=self.empresa_b)
		mensajes = set()
		for usuario in (self.gerente_a, self.contador_a, self.sistema_a):
			frappe.set_user(usuario)
			for empresa in (self.empresa_b, "Empresa que no existe"):
				with self.subTest(usuario=usuario, empresa=empresa):
					with self.assertRaises(frappe.PermissionError) as cm:
						consulta.consultar_borradores(empresa, "2026-09")
					mensajes.add(str(cm.exception))
		self.assertEqual(len(mensajes), 1)

	def test_sin_permiso_sobre_el_doctype(self):
		self._ingestar(1, "2026-09-15")
		frappe.set_user(self.compras_a)
		self.assertTrue(frappe.has_permission("Company", "read", self.empresa_a))
		with self.assertRaises(frappe.PermissionError):
			consulta.consultar_borradores(self.empresa_a, "2026-09")
