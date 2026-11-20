"""Pruebas del archivo y de la descarga de KF-05 con datos ficticios."""

import json
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree
from zipfile import ZipFile

import frappe
from frappe.handler import execute_cmd
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils.response import build_response
from openpyxl import load_workbook
from werkzeug.wrappers import Request

from kontaflow_sv.ingesta.servicio import ingestar_dte_compra
from kontaflow_sv.libro_compras.consulta import DOCTYPE
from kontaflow_sv.tests.fixtures import FixturesDePrueba
from kontaflow_sv.tests.limpieza import borrar_dte
from kontaflow_sv.tests.test_libro_compras_vista_previa import ccf_con_importes
from kontaflow_sv.tests.utilidades import NIT_EMPRESA_A, NIT_EMPRESA_B, codigo

D = Decimal
MES = "2026-09"
API = "kontaflow_sv.api.exportar_libro_compras"
XML = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
PLANTILLA = Path(__file__).resolve().parents[2] / "docs" / "formato-libros-contables.xlsx"
TRIBUTOS = [
	{"codigo": "20", "descripcion": "IVA", "valor": D("12.00")},
	{"codigo": "D1", "descripcion": "FOVIAL", "valor": D("0.21")},
	{"codigo": "C8", "descripcion": "COTRANS", "valor": D("0.32")},
	{"codigo": "C5", "descripcion": "Informativo", "valor": D("8.90")},
]


def _celda_xml(contenido: bytes, ref: str):
	with ZipFile(BytesIO(contenido)) as archivo:
		xml = ElementTree.fromstring(archivo.read("xl/worksheets/sheet1.xml"))
	return xml.find(f".//x:c[@r='{ref}']", XML)


class TestExportacionPura(UnitTestCase):
	def test_signo_ccf_y_rechazo_de_tipos_sin_regla(self):
		from kontaflow_sv.libro_compras.exportacion import _signo

		self.assertEqual(_signo("03"), 1)
		for tipo in ("05", "06", "14", "99"):
			with self.subTest(tipo=tipo), self.assertRaisesRegex(frappe.ValidationError, f"signo.*{tipo}"):
				_signo(tipo)

	def test_el_signo_afecta_todos_los_importes_y_el_total(self):
		from kontaflow_sv.libro_compras import exportacion as exp

		importes = dict.fromkeys((*exp.IMPORTES_DTE, "fovial", "cotrans"), D("2"))
		with patch.object(exp, "_signo", return_value=-1):
			montos = exp._importes_con_signo("05", importes)
		self.assertEqual(montos, dict.fromkeys(importes, D("-2")) | {"total_compras": D("-6")})

	def test_nombre_sanea_caracteres_reservados(self):
		from kontaflow_sv.libro_compras.exportacion import _nombre_archivo

		nombre = _nombre_archivo("Compañía: A/B*", MES)
		self.assertEqual(nombre, "Compania_ A_B__Libro de compras_2026-09_borradores.xlsx")

	def test_importe_con_mas_digitos_que_la_precision_de_float(self):
		from kontaflow_sv.libro_compras.exportacion import _crear_xlsx

		archivo = _crear_xlsx({}, [{"total_gravada": D("123456789012345.68"), "total_no_suj": D(0)}])
		celda = _celda_xml(archivo, "J8")
		self.assertEqual(celda.get("t"), "n")
		self.assertEqual(celda.findtext("x:v", namespaces=XML), "123456789012345.68")

	def test_nota_no_sujetas_en_singular_y_plural(self):
		from kontaflow_sv.libro_compras.exportacion import _nota_no_sujetas

		filas = []
		for n, importe in enumerate(("0", "2.10", "3.05"), start=1):
			ccf = json.loads(ccf_con_importes(n, MES + "-15", no_suj=importe), parse_float=D)
			filas.append({"total_no_suj": ccf["resumen"]["totalNoSuj"]})
		self.assertIsNone(_nota_no_sujetas(filas[:1]))
		self.assertEqual(
			_nota_no_sujetas(filas[:2]), "Compras no sujetas no incluidas: 1 documento por $2,10"
		)
		self.assertEqual(_nota_no_sujetas(filas), "Compras no sujetas no incluidas: 2 documentos por $5,15")

	def test_formato_de_duplicados_cubre_solo_el_detalle(self):
		from kontaflow_sv.libro_compras.exportacion import _crear_xlsx

		filas = []
		for n in range(1, 41):
			ccf = json.loads(ccf_con_importes(n, MES + "-15"))
			filas.append(
				{"numero_documento": ccf["identificacion"]["codigoGeneracion"], "total_no_suj": D(0)}
			)
		for cantidad, rango in ((1, "C8"), (35, "C8:C42"), (40, "C8:C47")):
			with self.subTest(cantidad=cantidad):
				archivo = _crear_xlsx({}, filas[:cantidad])
				formatos = load_workbook(BytesIO(archivo)).active.conditional_formatting
				duplicados = [
					str(formato.sqref)
					for formato in formatos
					for regla in formatos[formato]
					if regla.type == "duplicateValues"
				]
				self.assertEqual(duplicados, [rango])


class TestDescargaLibroCompras(IntegrationTestCase):
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
		self.filtros = {"company": self.empresa_a, "mes": MES}

	def _ingestar(self, n, fecha="2026-09-15", *, empresa=None, **importes):
		empresa = empresa or self.empresa_a
		nit = NIT_EMPRESA_A if empresa == self.empresa_a else NIT_EMPRESA_B
		return ingestar_dte_compra(empresa, ccf_con_importes(n, fecha, receptor_nit=nit, **importes))

	def _descargar(self, filtros=None):
		filtros = self.filtros if filtros is None else filtros
		with (
			patch.object(frappe.local, "request", Request.from_values(method="POST"), create=True),
			patch.object(frappe.local, "form_dict", frappe._dict(filtros)),
			patch.object(frappe.local, "response", frappe._dict()),
		):
			execute_cmd(API)
			return build_response()

	def _hoja(self, contenido=None):
		libro = load_workbook(BytesIO(self._descargar().data if contenido is None else contenido))
		self.assertEqual(libro.sheetnames, ["LibroCompras"])
		return libro.active

	def _comprobar_pie(self, hoja, fila_total, sumas):
		self.assertEqual(tuple(c.value for c in hoja[fila_total - 1]), (None,) * 20)
		self.assertEqual(
			tuple(c.value for c in hoja[fila_total]),
			(None, None, None, None, "TOTAL", None, *sumas),
		)
		self.assertEqual(hoja[f"E{fila_total + 3}"].value, "__________________________")
		self.assertEqual(hoja[f"E{fila_total + 4}"].value, "  Nombre y Firma de Contador")
		self.assertEqual(sum(c.value == "TOTAL" for c in hoja["E"]), 1)
		self.assertFalse(any(c.data_type == "f" for fila in hoja.iter_rows() for c in fila))
		self.assertFalse(
			any(c.value is not None for fila in hoja.iter_rows(min_row=fila_total + 6) for c in fila)
		)

	def test_columnas_plantilla_mapeo_y_descarga(self):
		primero = self._ingestar(
			1,
			"2026-09-01",
			gravada="100.00",
			exenta="5.05",
			no_suj="2.10",
			iva="12.00",
			**{
				"resumen.ivaPerci1": D("1.20"),
				"resumen.ivaRete1": D("0.80"),
				"resumen.tributos": TRIBUTOS,
				"resumen.montoTotalOperacion": D("119.68"),
				"resumen.totalPagar": D("120.08"),
			},
		)
		self._ingestar(2, "2026-09-30", gravada="10.00", version_dte=4)
		self._ingestar(3, "2026-10-01", gravada="30.00")
		doc = frappe.get_doc(DOCTYPE, primero["name"])
		self.assertCountEqual([t.codigo for t in doc.tributos], ["20", "D1", "C8", "C5"])

		respuesta = self._descargar()
		self.assertEqual(
			respuesta.mimetype, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
		)
		self.assertIn(
			f"{self.empresa_a}_Libro de compras_{MES}_borradores.xlsx",
			respuesta.headers["Content-Disposition"],
		)
		hoja = self._hoja(respuesta.data)
		referencia = load_workbook(PLANTILLA)["LibroCompras"]
		self.assertEqual(hoja.max_column, 20)
		self.assertEqual(len(hoja.merged_cells.ranges), 15)
		self.assertEqual(hoja.merged_cells.ranges, referencia.merged_cells.ranges)
		cabecera = {"A1": self.empresa_a, "B3": "SEPTIEMBRE", "Q3": 2026, "B4": NIT_EMPRESA_A, "Q4": "200002"}
		for fila in referencia.iter_rows(max_row=7):
			for celda in fila:
				actual = hoja[celda.coordinate]
				self.assertEqual(actual.value, cabecera.get(celda.coordinate, celda.value))
				self.assertEqual(actual._style, celda._style)
		for letra, dimension in referencia.column_dimensions.items():
			self.assertEqual(hoja.column_dimensions[letra].width, dimension.width)
		for actual, modelo in ((8, 8), (9, 8), (11, 44), (14, 47), (15, 48)):
			self.assertEqual([c._style for c in hoja[actual]], [c._style for c in referencia[modelo]])

		self.assertEqual(
			tuple(c.value for c in hoja[8]),
			(
				1,
				datetime(2026, 9, 1),
				codigo(1),
				"100001",
				"00000000000001",
				"PROVEEDOR DE PRUEBA, S.A. DE C.V.",
				5.05,
				None,
				None,
				100,
				None,
				None,
				12,
				0.21,
				0.32,
				None,
				1.2,
				117.05,
				0.8,
				None,
			),
		)
		self.assertEqual(hoja["J8"].data_type, "n")
		self.assertEqual((hoja["A9"].value, hoja["C9"].value), (2, codigo(2)))
		self.assertEqual([hoja[f"{letra}9"].value for letra in "NOP"], [None, None, None])
		self._comprobar_pie(hoja, 11, (5.05, 0, 0, 110, 0, 0, 13.3, 0.21, 0.32, 0, 1.2, 128.35, 0.8, 0))
		self.assertEqual(hoja["A16"].value, "Compras no sujetas no incluidas: 1 documento por $2,10")

	def test_mas_de_35_borradores_y_nrc_no_unico(self):
		for n in range(38, 0, -1):
			cabecera = {"receptor.nrc": "200003"} if n == 38 else {}
			self._ingestar(n, gravada="1.00", **cabecera)
		hoja = self._hoja()
		self.assertIsNone(hoja["Q4"].value)
		self.assertEqual([hoja[f"A{fila}"].value for fila in range(8, 46)], list(range(1, 39)))
		self.assertEqual([hoja[f"C{fila}"].value for fila in range(8, 46)], [codigo(n) for n in range(1, 39)])
		self._comprobar_pie(hoja, 47, (0, 0, 0, 38, 0, 0, 4.94, 0, 0, 0, 0, 42.94, 0, 0))
		self.assertIsNone(hoja["A52"].value)

	def test_exporta_solo_los_registros_visibles_de_la_empresa(self):
		self._ingestar(1, gravada="10")
		self._ingestar(2, gravada="20")
		frappe.set_user(self.contador)
		get_list = frappe.get_list

		def restringir_registros(doctype, *args, **kwargs):
			filas = get_list(doctype, *args, **kwargs)
			if doctype == DOCTYPE and not kwargs.get("ignore_permissions"):
				return [fila for fila in filas if fila.codigo_generacion == codigo(1)]
			return filas

		with patch.object(frappe, "get_list", side_effect=restringir_registros):
			hoja = self._hoja()
		self.assertEqual(hoja["C8"].value, codigo(1))
		self._comprobar_pie(hoja, 10, (0, 0, 0, 10, 0, 0, 1.3, 0, 0, 0, 0, 11.3, 0, 0))

	def test_diez_importes_fraccionarios_en_el_xml(self):
		for n in range(1, 11):
			self._ingestar(n, gravada="0.10")
		contenido = self._descargar().data
		self.assertEqual(_celda_xml(contenido, "J8").findtext("x:v", namespaces=XML), "0.10")
		self.assertEqual(_celda_xml(contenido, "J19").findtext("x:v", namespaces=XML), "1.00")

	def test_total_grande_en_el_xml(self):
		self._ingestar(1, gravada="7654321098.76")
		self._ingestar(2, gravada="7654321098.76")
		self._ingestar(3, gravada="0.01")
		self.assertEqual(
			_celda_xml(self._descargar().data, "J12").findtext("x:v", namespaces=XML), "15308642197.53"
		)

	def test_filtros_y_periodo_vacio(self):
		self._ingestar(1, "2026-08-31", gravada="5")
		for filtros, mensaje in (
			({"mes": MES}, "Indique la empresa"),
			({"company": self.empresa_a}, "Indique el mes"),
			(self.filtros | {"mes": "2026-13"}, "Indique el mes"),
			(self.filtros, "No hay borradores de CCF para la empresa y el mes indicados"),
		):
			with self.subTest(filtros=filtros), self.assertRaisesRegex(frappe.ValidationError, mensaje):
				self._descargar(filtros)

	def test_aislamiento_y_permiso_de_lectura(self):
		self._ingestar(1, gravada="10")
		self._ingestar(2, empresa=self.empresa_b, gravada="20")
		frappe.set_user(self.contador)
		hoja = self._hoja()
		self.assertEqual(hoja["C8"].value, codigo(1))
		self.assertIsNone(hoja["C9"].value)
		mensajes = []
		for empresa in (self.empresa_b, f"Inexistente {self.fx.token}"):
			with self.assertRaises(frappe.PermissionError) as rechazo:
				self._descargar(self.filtros | {"company": empresa})
			mensajes.append(str(rechazo.exception))
		self.assertEqual(*mensajes)

	def test_usuario_sin_rol_es_rechazado(self):
		self._ingestar(1, gravada="10")
		frappe.set_user(self.compras)
		self.assertTrue(frappe.has_permission("Company", "read", self.empresa_a))
		with self.assertRaises(frappe.PermissionError):
			self._descargar()

	def test_usuario_con_lectura_y_sin_permiso_de_exportacion(self):
		self._ingestar(1, gravada="10")
		frappe.set_user(self.contador)
		permiso_real = frappe.permissions.has_permission
		self.assertTrue(frappe.has_permission(DOCTYPE, "read"))

		def permiso(doctype, ptype="read", *args, **kwargs):
			if doctype == DOCTYPE and ptype == "export":
				return False
			return permiso_real(doctype, ptype, *args, **kwargs)

		with (
			patch.object(frappe.permissions, "has_permission", side_effect=permiso),
			self.assertRaises(frappe.PermissionError),
		):
			self._descargar()

	def test_solo_lectura_y_texto_literal(self):
		self._ingestar(1, gravada="10", **{"emisor.nombre": "=1+1"})
		filtros = {"company": self.empresa_a}
		antes = frappe.get_all(DOCTYPE, filters=filtros, fields=["name", "modified"])
		archivo = self._descargar().data
		self.assertEqual(frappe.get_all(DOCTYPE, filters=filtros, fields=["name", "modified"]), antes)
		proveedor = load_workbook(BytesIO(archivo)).active["F8"]
		self.assertEqual(proveedor.value, "=1+1")
		self.assertEqual(proveedor.data_type, "s")
