"""Cotejo del parser de CCF v4 con el JSON Schema oficial de Hacienda, caso por caso.

A diferencia de v3 (cuya copia pública no figura en el ZIP oficial), el esquema de v4 sale del propio ZIP
de Hacienda. No forma parte del repositorio: hay que indicar su ubicación; sin ella las pruebas se omiten.
Solo se lee el miembro ``fe-ccf-v4.json``, en memoria, sin extraer nada a disco:

    KF_ESQUEMAS_ZIP=/ruta/a/JSON-Schemas-Hacienda.zip bench --site kf.localhost run-tests ...

Cada caso comprueba que el esquema y el parser opinan lo mismo. Las diferencias que se mantienen a
propósito están listadas aparte y también se verifican.
"""

import json
import os
import unittest
import zipfile
from decimal import Decimal

from frappe.tests import UnitTestCase

from kontaflow_sv.ingesta.dte_compra import DTEInvalido, parsear_ccf_v4
from kontaflow_sv.tests.utilidades import ELIMINAR, a_json, codigo, construir_ccf

try:
	from jsonschema import Draft7Validator, FormatChecker
except ImportError:  # pragma: no cover
	Draft7Validator = None

RUTA_ZIP = os.environ.get("KF_ESQUEMAS_ZIP")
MIEMBRO = "svfe-json-schemas/v4/fe-ccf-v4.json"
D = Decimal


def v4(**cambios):
	return construir_ccf(version_dte=4, **cambios)


def _tributos(codigo_tributo, valor="1.00"):
	return [
		{"codigo": "20", "descripcion": "Impuesto al Valor Agregado 13%", "valor": D("2.04")},
		{"codigo": codigo_tributo, "descripcion": "Tributo de prueba", "valor": D(valor)},
	]


@unittest.skipUnless(
	RUTA_ZIP and os.path.exists(RUTA_ZIP) and Draft7Validator,
	"Defina KF_ESQUEMAS_ZIP con la ruta de JSON-Schemas-Hacienda.zip (y tenga jsonschema instalado)",
)
class TestCotejoConEsquemaCCFv4(UnitTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		with zipfile.ZipFile(RUTA_ZIP) as zip_hacienda:
			contenido = zip_hacienda.read(MIEMBRO)  # solo este miembro, en memoria
		esquema = json.loads(contenido.decode("utf-8"), parse_float=Decimal)
		cls.claves = set(esquema["properties"])
		cls.validador = Draft7Validator(esquema, format_checker=FormatChecker())

	def segun_esquema(self, texto) -> bool:
		doc = json.loads(texto, parse_float=Decimal)
		dte = {k: v for k, v in doc.items() if k in self.claves}  # solo el DTE, sin sello ni respuestas
		return not list(self.validador.iter_errors(dte))

	def segun_parser(self, texto) -> bool:
		try:
			parsear_ccf_v4(texto)
		except DTEInvalido:
			return False
		return True

	def comprobar(self, casos, esperado_esquema, esperado_parser):
		for nombre, texto in casos.items():
			with self.subTest(nombre):
				self.assertEqual(self.segun_esquema(texto), esperado_esquema, "esquema")
				self.assertEqual(self.segun_parser(texto), esperado_parser, "parser")

	def test_el_fixture_base_es_un_ccf_v4_valido(self):
		self.assertTrue(self.segun_esquema(v4()))
		self.assertTrue(self.segun_parser(v4()))

	def test_documentos_validos_que_el_parser_acepta(self):
		resumen_con = lambda **kw: {  # noqa: E731
			"resumen.montoTotalOperacion": D("17.72"),
			"resumen.totalPagar": D("17.72"),
			**kw,
		}
		cero = {
			"resumen.subTotal": D("0"),
			"resumen.tributos": [],
			"resumen.montoTotalOperacion": D("0"),
			"resumen.totalPagar": D("0"),
		}
		casos = {
			"nombre de emisor de 250 caracteres": v4(**{"emisor.nombre": "E" * 250}),
			"nombre de receptor de 250 caracteres": v4(**{"receptor.nombre": "R" * 250}),
			"descripción de tributo de 300 caracteres": v4(
				**{"resumen.tributos": [{"codigo": "20", "descripcion": "T" * 300, "valor": D("2.04")}]}
			),
			"descripción de ítem de 1500 caracteres": v4(**{"cuerpoDocumento.0.descripcion": "X" * 1500}),
			"abono no gravado negativo": v4(
				**{"cuerpoDocumento.0.noGravado": D("-5.25"), "resumen.totalNoGravado": D("-5.25")}
			),
			"monto total en cero (v4: minimum 0)": v4(**cero),
			"IVA retenido y percibido": v4(**{"resumen.ivaRete": D("0.75"), "resumen.ivaPerci": D("1.25")}),
			"NIT con guiones (v4 no fija patrón)": v4(**{"receptor.nit": "0000-000000-000-2"}),
			"ivaRete con ceros finales (0.7500)": v4(**{"resumen.ivaRete": D("0.7500")}),
			"precio unitario con ceros finales (0.100000000)": v4(
				**{"cuerpoDocumento.0.precioUni": D("0.100000000")}
			),
			"cantidad con ceros finales (3.000000000)": v4(
				**{"cuerpoDocumento.0.cantidad": D("3.000000000")}
			),
		}
		for cod in ("C5", "C6", "C7", "19", "28", "A9"):
			casos[f"tributo informativo {cod}"] = v4(**resumen_con(**{"resumen.tributos": _tributos(cod)}))
		self.comprobar(casos, esperado_esquema=True, esperado_parser=True)

	def test_documentos_invalidos_que_el_parser_rechaza(self):
		self.comprobar(
			{
				"otro tipo de DTE": v4(**{"identificacion.tipoDte": "05"}),
				"declara versión 3": v4(**{"identificacion.version": 3}),
				"ambiente desconocido": v4(**{"identificacion.ambiente": "09"}),
				"moneda distinta de USD": v4(**{"identificacion.tipoMoneda": "EUR"}),
				"numeroControl con la estructura de v3": v4(
					**{"identificacion.numeroControl": "DTE-03-ABCD1234-000000000000001"}
				),
				"numeroControl con tipo de establecimiento inválido": v4(
					**{"identificacion.numeroControl": "DTE-03-X001P001-000000000000001"}
				),
				"codigoGeneracion que no es UUID": v4(**{"identificacion.codigoGeneracion": "123"}),
				"hora inexistente": v4(**{"identificacion.horEmi": "25:00:00"}),
				"ventaGravada negativa": v4(**{"cuerpoDocumento.0.ventaGravada": D("-0.3")}),
				"precio unitario negativo": v4(**{"cuerpoDocumento.0.precioUni": D("-0.1")}),
				"cantidad cero": v4(**{"cuerpoDocumento.0.cantidad": D("0")}),
				"totalExenta negativo": v4(**{"resumen.totalExenta": D("-1")}),
				"monto total negativo": v4(**{"resumen.montoTotalOperacion": D("-1")}),
				"valor de tributo negativo": v4(
					**{"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("-2.04")}]}
				),
				"3 decimales en el resumen": v4(**{"resumen.totalPagar": D("17.725")}),
				"9 decimales en un ítem": v4(**{"cuerpoDocumento.0.precioUni": D("0.123456789")}),
				"nombre de emisor de 251 caracteres": v4(**{"emisor.nombre": "E" * 251}),
				"nombre de receptor de 251 caracteres": v4(**{"receptor.nombre": "R" * 251}),
				"descripción de tributo de 301 caracteres": v4(
					**{"resumen.tributos": [{"codigo": "20", "descripcion": "T" * 301, "valor": D("2.04")}]}
				),
				"descripción de ítem de 1501 caracteres": v4(**{"cuerpoDocumento.0.descripcion": "X" * 1501}),
				"sin ítems": v4(cuerpoDocumento=[]),
				"IVA percibido ausente": v4(**{"resumen.ivaPerci": ELIMINAR}),
				"IVA retenido ausente": v4(**{"resumen.ivaRete": ELIMINAR}),
				"IVA retenido nulo": v4(**{"resumen.ivaRete": None}),
				"IVA percibido nulo": v4(**{"resumen.ivaPerci": None}),
				"nombres de v3 en lugar de los de v4": self._con_nombres_de_v3(),
			},
			esperado_esquema=False,
			esperado_parser=False,
		)

	def _con_nombres_de_v3(self):
		doc = json.loads(v4(), parse_float=Decimal)
		resumen = doc["resumen"]
		del resumen["ivaPerci"], resumen["ivaRete"]
		resumen["ivaPerci1"], resumen["ivaRete1"] = D("1.25"), D("0.75")
		return a_json(doc)

	def test_cada_importe_obligatorio_del_resumen_se_exige_en_ambos(self):
		"""Si el esquema lo exige y falta (o es nulo), el parser también lo rechaza: no vale 0 en silencio."""
		obligatorios = (
			"totalNoSuj", "totalExenta", "totalGravada", "subTotalVentas", "descuGravada", "totalDescu",
			"subTotal", "ivaPerci", "ivaRete", "montoTotalOperacion", "totalNoGravado", "totalPagar",
		)  # fmt: skip
		casos = {}
		for campo in obligatorios:
			casos[f"{campo} ausente"] = v4(**{f"resumen.{campo}": ELIMINAR})
			casos[f"{campo} nulo"] = v4(**{f"resumen.{campo}": None})
		self.comprobar(casos, esperado_esquema=False, esperado_parser=False)

	def test_ceros_finales_no_cambian_el_valor_pero_los_digitos_de_mas_si(self):
		self.comprobar(
			{
				"ivaRete 0.7501": v4(**{"resumen.ivaRete": D("0.7501")}),
				"precioUni 0.1000000001": v4(**{"cuerpoDocumento.0.precioUni": D("0.1000000001")}),
			},
			esperado_esquema=False,
			esperado_parser=False,
		)

	def _ccf_con_n_items(self, n):
		"""CCF v4 coherente con ``n`` ítems exentos de 0.01: solo la cantidad de ítems puede invalidarlo."""
		doc = json.loads(v4(), parse_float=Decimal)
		item = {**doc["cuerpoDocumento"][0]}
		item.update(
			cantidad=D("1"), precioUni=D("0.01"), ventaGravada=D("0"), ventaExenta=D("0.01"), tributos=None
		)
		doc["cuerpoDocumento"] = [{**item, "numItem": i} for i in range(1, n + 1)]
		total = D("0.01") * n
		doc["resumen"].update(
			totalGravada=D("0"),
			totalExenta=total,
			subTotalVentas=total,
			subTotal=total,
			tributos=[],
			montoTotalOperacion=total,
			totalPagar=total,
		)
		return a_json(doc)

	def test_limite_de_2000_items_en_ambos_lados(self):
		self.comprobar(
			{"2000 ítems": self._ccf_con_n_items(2000)}, esperado_esquema=True, esperado_parser=True
		)
		self.comprobar(
			{"2001 ítems": self._ccf_con_n_items(2001)}, esperado_esquema=False, esperado_parser=False
		)

	# --- diferencias que se mantienen a propósito
	def test_diferencias_intencionales(self):
		self.comprobar(
			{
				"codigoGeneracion en minúsculas": v4(
					**{"identificacion.codigoGeneracion": codigo(0xABCDEF).lower()}
				)
			},
			esperado_esquema=False,
			esperado_parser=True,  # el parser lo normaliza a mayúsculas
		)
		self.comprobar(
			{"NIT del receptor de 3 dígitos": v4(**{"receptor.nit": "123"})},
			esperado_esquema=True,  # v4 solo pide texto
			esperado_parser=False,  # el parser exige 9 o 14 dígitos para compararlo con el de la empresa
		)
