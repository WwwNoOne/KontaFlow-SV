"""Pruebas de KF-06.1 con notas de crédito y débito ficticias."""

import json
import os
from decimal import Decimal
from zipfile import ZipFile

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from jsonschema import Draft7Validator, FormatChecker

from kontaflow_sv.api import ingestar_dte_compra
from kontaflow_sv.ingesta.dte_compra import DTEInvalido, hash_contenido, parsear_dte_compra
from kontaflow_sv.ingesta.servicio import DOCTYPE
from kontaflow_sv.tests.fixtures import FixturesDePrueba, nc_con_importes, nd_con_importes
from kontaflow_sv.tests.limpieza import borrar_dte
from kontaflow_sv.tests.utilidades import NIT_EMPRESA_A, NIT_EMPRESA_B, a_json, codigo, construir_ccf

D = Decimal
NOTAS = {"05": nc_con_importes, "06": nd_con_importes}


def _doc(fixture):
	return json.loads(fixture(), parse_float=D)


class TestNotasV4(UnitTestCase):
	def test_despacha_nc_y_nd_y_lee_el_iva_declarado(self):
		for tipo, fixture in NOTAS.items():
			with self.subTest(tipo=tipo):
				doc = _doc(fixture)
				doc["resumen"]["tributos"] = None
				if tipo == "06":
					doc["resumen"]["numPagoElectronico"] = "PAGO DE PRUEBA"
				resultado = parsear_dte_compra(a_json(doc))
				self.assertEqual(resultado["identificacion"]["tipo_dte"], tipo)
				self.assertEqual(resultado["receptor"]["nit"], NIT_EMPRESA_A)
				self.assertEqual(resultado["resumen"]["iva"], D("12.00"))
				self.assertEqual(resultado["items"][0]["iva"], D("12.00"))
				self.assertEqual(resultado["documentos_relacionados"][0]["numero_documento"], codigo(500))
				self.assertTrue(any("13 %" in aviso for aviso in resultado["advertencias"]))
				self.assertEqual(
					resultado["resumen"].get("num_pago_electronico"),
					"PAGO DE PRUEBA" if tipo == "06" else None,
				)

	def test_numero_control_del_tipo(self):
		for tipo, fixture in NOTAS.items():
			doc = _doc(fixture)
			doc["identificacion"]["numeroControl"] = "DTE-03-M001P001-000000000000001"
			with self.subTest(tipo=tipo), self.assertRaisesRegex(DTEInvalido, f"numeroControl.*DTE-{tipo}"):
				parsear_dte_compra(a_json(doc))

	def test_tipo_y_version_no_admitidos(self):
		for tipo, version, mensaje in (
			("14", 4, "tipo de DTE"),
			("05", 3, "se admiten: 4"),
			("06", 3, "se admiten: 4"),
		):
			doc = _doc(nc_con_importes)
			doc["identificacion"].update(tipoDte=tipo, version=version)
			with self.subTest(tipo=tipo), self.assertRaisesRegex(DTEInvalido, mensaje):
				parsear_dte_compra(a_json(doc))

	def test_documento_relacionado_obligatorio_y_valido(self):
		for fixture in NOTAS.values():
			doc = _doc(fixture)
			relacionado = doc.pop("documentoRelacionado")[0]
			for invalido in (
				{},
				{"documentoRelacionado": []},
				{"documentoRelacionado": [relacionado] * 51},
				{"documentoRelacionado": [relacionado | {"fechaEmision": "2026-02-30"}]},
				{"documentoRelacionado": [relacionado | {"numeroDocumento": "1" * 37}]},
				{"documentoRelacionado": [relacionado | {"tipoGeneracion": True}]},
			):
				with (
					self.subTest(fixture=fixture.__name__),
					self.assertRaisesRegex(DTEInvalido, "documentoRelacionado"),
				):
					parsear_dte_compra(a_json(doc | invalido))

	def test_importes_negativos_y_cuadre_de_ventas(self):
		for fixture in NOTAS.values():
			for campo, valor, mensaje in (
				("totalIva", D("-1"), "totalIva.*negativo"),
				("ivaRete", D("-1"), "ivaRete.*negativo"),
				("totalGravada", D("99"), "totalGravada.*suma de los ítems"),
			):
				doc = _doc(fixture)
				doc["resumen"][campo] = valor
				with self.subTest(campo=campo), self.assertRaisesRegex(DTEInvalido, mensaje):
					parsear_dte_compra(a_json(doc))

	def test_rechaza_subtotal_ventas_inflado(self):
		for tipo, fixture in NOTAS.items():
			doc = _doc(fixture)
			doc["resumen"].update(subTotalVentas=1000, montoTotalOperacion=1012, totalPagar=1012)
			with (
				self.subTest(tipo=tipo),
				self.assertRaisesRegex(DTEInvalido, r"resumen\.subTotalVentas.*\(1000\).*\(100\.00\)"),
			):
				parsear_dte_compra(a_json(doc))

	def test_acepta_subtotal_ventas_correcto(self):
		for tipo, fixture in NOTAS.items():
			with self.subTest(tipo=tipo):
				resumen = parsear_dte_compra(fixture())["resumen"]
				self.assertEqual(resumen["sub_total_ventas"], D("100.00"))

	def test_rechaza_referencia_de_item_ajena(self):
		for tipo, fixture in NOTAS.items():
			doc = _doc(fixture)
			doc["cuerpoDocumento"][0].update(numItem=7, numeroDocumento="REFERENCIA-AJENA")
			with (
				self.subTest(tipo=tipo),
				self.assertRaisesRegex(DTEInvalido, r"ítem 7.*numeroDocumento.*REFERENCIA-AJENA"),
			):
				parsear_dte_compra(a_json(doc))

	def test_acepta_referencia_de_item_declarada(self):
		for tipo, fixture in NOTAS.items():
			with self.subTest(tipo=tipo):
				resultado = parsear_dte_compra(fixture())
				self.assertEqual(resultado["items"][0]["numero_documento"], codigo(500))

	def test_importes_obligatorios_en_las_notas(self):
		for fixture in NOTAS.values():
			for seccion, campo in (("resumen", "totalIva"), ("cuerpoDocumento", "ventaExenta")):
				doc = _doc(fixture)
				datos = doc[seccion] if seccion == "resumen" else doc[seccion][0]
				del datos[campo]
				with (
					self.subTest(fixture=fixture.__name__, campo=campo),
					self.assertRaisesRegex(DTEInvalido, f"Falta .*{campo}"),
				):
					parsear_dte_compra(a_json(doc))

	def test_monto_operacion_y_diferencias_de_iva(self):
		doc = _doc(nd_con_importes)
		doc["resumen"]["montoTotalOperacion"] = D("130")
		with self.assertRaisesRegex(DTEInvalido, "montoTotalOperacion.*no cuadra"):
			parsear_dte_compra(a_json(doc))
		doc["resumen"]["montoTotalOperacion"] = D("112")
		doc["resumen"]["tributos"][0]["valor"] = D("13")
		doc["cuerpoDocumento"][0]["totalIva"] = D("11")
		resultado = parsear_dte_compra(a_json(doc))
		self.assertEqual(resultado["resumen"]["iva"], D("12"))
		self.assertTrue(any("suma del IVA de los ítems" in aviso for aviso in resultado["advertencias"]))
		self.assertTrue(any("no coincide con el tributo 20" in aviso for aviso in resultado["advertencias"]))

	def test_suma_decimal_de_los_items(self):
		doc = _doc(nc_con_importes)
		item = doc["cuerpoDocumento"][0]
		doc["cuerpoDocumento"] = [
			item | {"numItem": i, "ventaGravada": D("0.10"), "totalIva": D("0.013")} for i in range(1, 11)
		]
		# La diferencia exacta de un centavo cae dentro de la tolerancia.
		doc["resumen"].update(
			totalGravada=D("1.01"),
			subTotalVentas=D("1.01"),
			totalIva=D("0.13"),
			montoTotalOperacion=D("1.14"),
			totalPagar=D("1.14"),
			tributos=None,
		)
		self.assertEqual(parsear_dte_compra(a_json(doc))["resumen"]["total_gravada"], D("1.01"))

	def test_el_fixture_de_cada_nota_valida_con_su_esquema_oficial(self):
		ruta = os.environ.get("KF_ESQUEMAS_ZIP")
		if not ruta:
			self.skipTest("Defina KF_ESQUEMAS_ZIP")
		with ZipFile(ruta) as archivo:
			for tipo, miembro in (("05", "fe-nc-v4.json"), ("06", "fe-nd-v4.json")):
				with self.subTest(tipo=tipo):
					esquema = json.loads(archivo.read(f"svfe-json-schemas/v4/{miembro}"), parse_float=D)
					validador = Draft7Validator(esquema, format_checker=FormatChecker())
					validador.validate(_doc(NOTAS[tipo]))

	def test_limites_de_items_y_bytes(self):
		doc = _doc(nd_con_importes)
		doc["cuerpoDocumento"] *= 2001
		with self.assertRaisesRegex(DTEInvalido, "máximo de 2000 ítems"):
			parsear_dte_compra(a_json(doc))
		with self.assertRaisesRegex(DTEInvalido, "tamaño máximo"):
			parsear_dte_compra(nd_con_importes() + " " * 2_000_000)


class TestIngestaNotasV4(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.fx = FixturesDePrueba()
		cls.addClassCleanup(cls.fx.limpiar)
		cls.fx.preparar()
		cls.empresa_a = cls.fx.empresa("A", NIT_EMPRESA_A).name
		cls.empresa_b = cls.fx.empresa("B", NIT_EMPRESA_B).name
		cls.contador = cls.fx.usuario("contador", cls.empresa_a, "Accounts User")
		cls.compras = cls.fx.usuario("compras", cls.empresa_a, "Purchase User")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		borrar_dte(self.fx.nombres_de_empresas())

	def test_borradores_con_importes_y_referencias(self):
		for tipo, fixture in NOTAS.items():
			original = fixture()
			if tipo == "06":
				datos = _doc(fixture)
				datos["documentoRelacionado"].append(
					{
						"tipoDocumento": "03",
						"tipoGeneracion": 1,
						"numeroDocumento": "00017",
						"fechaEmision": "2026-09-02",
					}
				)
				original = a_json(datos)
			name = ingestar_dte_compra(self.empresa_a, original)["name"]
			doc = frappe.get_doc(DOCTYPE, name)
			self.assertEqual((doc.tipo_dte, doc.version, doc.estado), (tipo, 4, "Borrador"))
			self.assertEqual(
				(doc.total_gravada, doc.iva, doc.items[0].iva, doc.tributos[0].valor), (100, 12, 12, 12)
			)
			self.assertEqual(doc.items[0].numero_documento, codigo(500))
			self.assertIn("13 %", doc.advertencias)
			self.assertEqual((doc.dte_original, doc.dte_sha256), (original, hash_contenido(original)))
			rel = doc.documentos_relacionados
			self.assertEqual(len(rel), 1 if tipo == "05" else 2)
			self.assertEqual(
				(
					rel[0].tipo_documento,
					rel[0].tipo_generacion,
					rel[0].numero_documento,
					str(rel[0].fecha_emision),
				),
				("03", 2, codigo(500), "2026-09-01"),
			)
			if tipo == "06":
				self.assertEqual(rel[1].numero_documento, "00017")

	def test_idempotencia_conflicto_y_aislamiento(self):
		for n, fixture in enumerate(NOTAS.values(), start=1):
			original = fixture(n)
			primero = ingestar_dte_compra(self.empresa_a, original)
			reintento = ingestar_dte_compra(self.empresa_a, original)
			self.assertEqual((reintento["resultado"], reintento["name"]), ("existente", primero["name"]))
			for conflicto in (fixture(n, iva="13.00"), construir_ccf(n, version_dte=4)):
				with self.assertRaises(frappe.DuplicateEntryError):
					ingestar_dte_compra(self.empresa_a, conflicto)
			ajeno = ingestar_dte_compra(self.empresa_b, fixture(n, NIT_EMPRESA_B))
			self.assertNotEqual(primero["name"], ajeno["name"])
			self.assertEqual(frappe.db.get_value(DOCTYPE, primero["name"], "dte_original"), original)

	def test_receptor_ajeno_y_permisos(self):
		frappe.set_user(self.contador)
		for fixture in NOTAS.values():
			with self.assertRaisesRegex(frappe.ValidationError, "receptor.*no corresponde"):
				ingestar_dte_compra(self.empresa_a, fixture(receptor_nit=NIT_EMPRESA_B))
			with self.assertRaises(frappe.PermissionError):
				ingestar_dte_compra(self.empresa_b, fixture(receptor_nit=NIT_EMPRESA_B))
			self.assertEqual(ingestar_dte_compra(self.empresa_a, fixture())["resultado"], "creado")
		frappe.set_user(self.compras)
		with self.assertRaises(frappe.PermissionError):
			ingestar_dte_compra(self.empresa_a, nc_con_importes(20))
