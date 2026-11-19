"""Pruebas del reporte del Libro de Compras por la vía que usa Frappe Desk (KF-04.3)."""

import json
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.desk.query_report import get_script, run
from frappe.tests import IntegrationTestCase
from frappe.utils.response import as_json

from kontaflow_sv.ingesta.servicio import ingestar_dte_compra
from kontaflow_sv.libro_compras.consulta import DOCTYPE
from kontaflow_sv.libro_compras.vista_previa import COLUMNAS, COLUMNAS_MONETARIAS, vista_previa
from kontaflow_sv.tests.fixtures import FixturesDePrueba
from kontaflow_sv.tests.limpieza import borrar_dte
from kontaflow_sv.tests.test_libro_compras_vista_previa import ccf_con_importes
from kontaflow_sv.tests.utilidades import NIT_EMPRESA_A, NIT_EMPRESA_B

REPORTE = "Vista previa del Libro de Compras"
MES = "2026-09"


class TestLibroComprasReporte(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.fx = FixturesDePrueba()
		cls.addClassCleanup(cls.fx.limpiar)
		cls.fx.preparar()
		cls.empresa_a = cls.fx.empresa("A", NIT_EMPRESA_A).name
		cls.empresa_b = cls.fx.empresa("B", NIT_EMPRESA_B).name
		cls.contador_a = cls.fx.usuario("contador", cls.empresa_a, "Accounts User")
		cls.compras_a = cls.fx.usuario("compras", cls.empresa_a, "Purchase User")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		borrar_dte(self.fx.nombres_de_empresas())
		self.filtros = {"company": self.empresa_a, "mes": MES}

	def _ingestar(self, n, fecha="2026-09-15", *, empresa=None, **importes):
		empresa = empresa or self.empresa_a
		nit = NIT_EMPRESA_A if empresa == self.empresa_a else NIT_EMPRESA_B
		texto = ccf_con_importes(n, fecha, receptor_nit=nit, **importes)
		return ingestar_dte_compra(empresa, texto)["name"]

	def _ejecutar(self, **filtros):
		return run(REPORTE, filters=json.dumps(self.filtros | filtros))

	def _totales_en_json(self):
		with patch.object(frappe.local, "response", frappe._dict()):
			frappe.response["message"] = self._ejecutar()
			respuesta = json.loads(as_json().get_data(), parse_float=Decimal)
		return respuesta["message"]["result"][-1]

	def test_columnas_y_enlace_al_borrador(self):
		nombre = self._ingestar(1, gravada="100.00", iva="12.00")
		resultado = self._ejecutar()
		columnas = resultado["columns"]
		self.assertEqual(tuple(c["fieldname"] for c in columnas), COLUMNAS)
		self.assertEqual(
			[c["label"] for c in columnas],
			[
				"Borrador",
				"Fecha de emisión",
				"Código de generación",
				"Número de control",
				"Sello de recepción",
				"Proveedor",
				"NIT del emisor",
				"NRC del emisor",
				"Gravadas",
				"Exentas",
				"No sujetas",
				"IVA del DTE",
				"Advertencias",
			],
		)
		self.assertEqual(columnas[0]["fieldtype"], "Link")
		self.assertEqual(columnas[0]["options"], DOCTYPE)
		self.assertEqual(resultado["result"][0]["name"], nombre)
		self.assertEqual(resultado["result"][0]["iva"], Decimal("12.00"))
		for columna in columnas:
			if columna["fieldname"] in COLUMNAS_MONETARIAS:
				self.assertEqual(columna["fieldtype"], "Currency")
				self.assertEqual(columna["precision"], 2)
				for fila in resultado["result"]:
					self.assertEqual(fila[columna["options"]], "USD")

	def test_filtros_obligatorios_en_desk(self):
		script = get_script(REPORTE)["script"]
		self.assertRegex(
			script,
			r'fieldname:\s*"company"[^}]*fieldtype:\s*"Link"[^}]*options:\s*"Company"[^}]*reqd:\s*1\b',
		)
		self.assertRegex(script, r'fieldname:\s*"mes"[^}]*fieldtype:\s*"Data"[^}]*reqd:\s*1\b')

	def test_detalle_y_un_total_de_v3_y_v4(self):
		self._ingestar(1, gravada="1.10", exenta="2.30")
		self._ingestar(2, "2026-09-30", gravada="2.20", no_suj="0.40", version_dte=4)
		self._ingestar(3, "2026-10-01", gravada="20.00")
		self._ingestar(4, empresa=self.empresa_b, gravada="300.00")
		esperado = vista_previa(self.empresa_a, MES)
		resultado = self._ejecutar()
		self.assertFalse(resultado["add_total_row"])
		primera, segunda, total = resultado["result"]
		self.assertEqual(
			[{campo: fila[campo] for campo in COLUMNAS} for fila in (primera, segunda)],
			[fila | {"advertencias": "; ".join(fila["advertencias"])} for fila in esperado["filas"]],
		)
		self.assertEqual(total["emisor_nombre"], "Total")
		self.assertFalse(total.get("name"))
		self.assertEqual({campo: total[campo] for campo in COLUMNAS_MONETARIAS}, esperado["totales"])
		self.assertEqual(total["total_gravada"], Decimal("3.30"))

	def test_advertencias_se_unen_y_el_aviso_cuenta_borradores(self):
		self._ingestar(
			1,
			gravada="100.00",
			iva="12.00",
			**{
				"resumen.tributos": [
					{"codigo": "20", "descripcion": "IVA 13%", "valor": Decimal("12.00")},
					{"codigo": "ZZ", "descripcion": "Tributo ficticio", "valor": Decimal("1.00")},
				],
				"resumen.montoTotalOperacion": Decimal("113.00"),
				"resumen.totalPagar": Decimal("113.00"),
			},
		)
		self._ingestar(2, "2026-09-16", gravada="1.10")
		advertencias = vista_previa(self.empresa_a, MES)["filas"][0]["advertencias"]
		self.assertEqual(len(advertencias), 2)
		resultado = self._ejecutar()
		self.assertEqual(resultado["result"][0]["advertencias"], "; ".join(advertencias))
		self.assertEqual(resultado["result"][1]["advertencias"], "")
		self.assertEqual(resultado["message"], "1 borrador tiene advertencias")

	def test_periodo_vacio(self):
		self._ingestar(1, "2026-08-31", gravada="1.10")
		resultado = self._ejecutar()
		self.assertEqual(resultado["result"], [])
		self.assertEqual(resultado["message"], "No hay borradores de CCF para la empresa y el mes indicados")

	def test_filtros_obligatorios_en_ejecucion_directa(self):
		for filtros, mensaje in (
			({}, "Indique la empresa."),
			({"mes": MES}, "Indique la empresa."),
			({"company": self.empresa_a}, "Indique el mes con el formato AAAA-MM"),
			({"company": self.empresa_a, "mes": "2026-13"}, "Indique el mes con el formato AAAA-MM"),
		):
			with self.subTest(filtros=filtros), self.assertRaisesRegex(frappe.ValidationError, mensaje):
				run(REPORTE, filters=filtros)

	def test_permisos_y_aislamiento_por_empresa(self):
		propio = self._ingestar(1, gravada="1.10")
		self._ingestar(1, empresa=self.empresa_b, gravada="2.20")
		frappe.set_user(self.contador_a)
		detalle, total = self._ejecutar()["result"]
		self.assertEqual(detalle["name"], propio)
		self.assertEqual(total["total_gravada"], Decimal("1.10"))
		mensajes = []
		for empresa in (self.empresa_b, f"Empresa inexistente {self.fx.token}"):
			with self.assertRaises(frappe.PermissionError) as error:
				self._ejecutar(company=empresa)
			mensajes.append(str(error.exception))
		self.assertEqual(mensajes[0], mensajes[1])

	def test_sin_rol_del_reporte(self):
		frappe.set_user(self.compras_a)
		self.assertTrue(frappe.has_permission("Company", "read", self.empresa_a))
		with self.assertRaises(frappe.PermissionError):
			self._ejecutar()

	def test_diez_importes_de_diez_centavos_en_json(self):
		for n in range(1, 11):
			self._ingestar(n, gravada="0.10")
		self.assertEqual(self._totales_en_json()["total_gravada"], Decimal("1.00"))

	def test_total_grande_conserva_los_centavos_en_json(self):
		self._ingestar(1, gravada="7654321098.76")
		self._ingestar(2, gravada="7654321098.76")
		self._ingestar(3, gravada="0.01")
		total = self._totales_en_json()
		self.assertEqual(total["total_gravada"], Decimal("15308642197.53"))
		self.assertEqual(total["iva"], Decimal("1990123485.68"))

	def test_solo_lectura(self):
		self._ingestar(1, gravada="1.10")
		filtros = {"company": self.empresa_a}
		antes = frappe.get_all(DOCTYPE, filters=filtros, fields=["name", "modified"])
		self._ejecutar()
		self.assertEqual(frappe.get_all(DOCTYPE, filters=filtros, fields=["name", "modified"]), antes)
