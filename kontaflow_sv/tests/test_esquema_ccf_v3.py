"""Cotejo del parser con el JSON Schema de CCF v3, caso por caso.

El esquema no forma parte del repositorio (es un archivo de Hacienda). Para ejecutar estas pruebas hay
que indicar su ubicación; sin ella se omiten:

    KF_ESQUEMA_CCF_V3=/ruta/a/fe-ccf-v3-copia-publica.json bench --site kf.localhost run-tests ...

Cada caso comprueba que el esquema y el parser opinan lo mismo, de modo que el parser no sea más
estricto que el esquema en lo que valida ni más laxo en lo que el esquema rechaza. Las diferencias
que se mantienen a propósito están listadas aparte y también se verifican.
"""

import json
import os
import unittest
from decimal import Decimal

from frappe.tests import UnitTestCase

from kontaflow_sv.ingesta.dte_compra import DTEInvalido, parsear_ccf_v3
from kontaflow_sv.tests.utilidades import codigo, construir_ccf

try:
	from jsonschema import Draft7Validator, FormatChecker
except ImportError:  # pragma: no cover
	Draft7Validator = None

RUTA_ESQUEMA = os.environ.get("KF_ESQUEMA_CCF_V3")
D = Decimal


def _tributos(codigo_tributo, valor="1.00"):
	return [
		{"codigo": "20", "descripcion": "Impuesto al Valor Agregado 13%", "valor": D("2.04")},
		{"codigo": codigo_tributo, "descripcion": "Tributo de prueba", "valor": D(valor)},
	]


@unittest.skipUnless(
	RUTA_ESQUEMA and os.path.exists(RUTA_ESQUEMA) and Draft7Validator,
	"Defina KF_ESQUEMA_CCF_V3 con la ruta del esquema fe-ccf-v3 (y tenga jsonschema instalado)",
)
class TestCotejoConEsquemaCCFv3(UnitTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		with open(RUTA_ESQUEMA, encoding="utf-8") as f:
			esquema = json.load(f, parse_float=Decimal)  # Decimal: con float, multipleOf da falsos positivos
		cls.claves = set(esquema["properties"])
		cls.validador = Draft7Validator(esquema, format_checker=FormatChecker())

	def segun_esquema(self, texto) -> bool:
		doc = json.loads(texto, parse_float=Decimal)
		# Se valida solo el DTE; un documento recibido trae además claves de Hacienda (sello, respuestas)
		dte = {k: v for k, v in doc.items() if k in self.claves}
		return not list(self.validador.iter_errors(dte))

	def segun_parser(self, texto) -> bool:
		try:
			parsear_ccf_v3(texto)
		except DTEInvalido:
			return False
		return True

	def comprobar(self, casos, esperado_esquema, esperado_parser):
		for nombre, texto in casos.items():
			with self.subTest(nombre):
				self.assertEqual(self.segun_esquema(texto), esperado_esquema, "esquema")
				self.assertEqual(self.segun_parser(texto), esperado_parser, "parser")

	# --- la base de las pruebas es un CCF v3 válido
	def test_el_fixture_base_es_un_ccf_v3_valido(self):
		self.assertTrue(self.segun_esquema(construir_ccf()))
		self.assertTrue(self.segun_parser(construir_ccf()))

	# --- lo que el esquema acepta, el parser también
	def test_documentos_validos_que_el_parser_acepta(self):
		resumen_con = lambda **kw: {  # noqa: E731
			"resumen.montoTotalOperacion": D("17.72"),
			"resumen.totalPagar": D("17.72"),
			**kw,
		}
		self.comprobar(
			{
				"nombre de emisor de 200 caracteres": construir_ccf(**{"emisor.nombre": "E" * 200}),
				"nombre de receptor de 250 caracteres": construir_ccf(**{"receptor.nombre": "R" * 250}),
				"abono no gravado negativo": construir_ccf(
					**{"cuerpoDocumento.0.noGravado": D("-5.25"), "resumen.totalNoGravado": D("-5.25")}
				),
				"descripción de tributo de 150 caracteres": construir_ccf(
					**{"resumen.tributos": [{"codigo": "20", "descripcion": "T" * 150, "valor": D("2.04")}]}
				),
				"importe grande con 8 decimales": construir_ccf(
					**{
						"cuerpoDocumento.0.ventaGravada": D("5000000.12345678"),
						"resumen.totalGravada": D("5000015.50"),
						"resumen.subTotalVentas": D("5000015.50"),
						"resumen.subTotal": D("5000015.50"),
						"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("650002.02")}],
						"resumen.montoTotalOperacion": D("5650017.52"),
						"resumen.totalPagar": D("5650017.52"),
					}
				),
			},
			esperado_esquema=True,
			esperado_parser=True,
		)
		# Tributos informativos: el esquema no restringe el código en el resumen y el parser no los suma
		casos = {}
		for cod in ("C5", "C6", "C7", "19", "28", "A9"):
			casos[f"tributo informativo {cod}"] = construir_ccf(
				**resumen_con(**{"resumen.tributos": _tributos(cod)})
			)
		self.comprobar(casos, esperado_esquema=True, esperado_parser=True)

	# --- lo que el esquema rechaza, el parser también
	def test_documentos_invalidos_que_el_parser_rechaza(self):
		self.comprobar(
			{
				"otro tipo de DTE": construir_ccf(**{"identificacion.tipoDte": "05"}),
				"otra versión": construir_ccf(**{"identificacion.version": 4}),
				"ambiente desconocido": construir_ccf(**{"identificacion.ambiente": "09"}),
				"moneda distinta de USD": construir_ccf(**{"identificacion.tipoMoneda": "EUR"}),
				"numeroControl con formato incorrecto": construir_ccf(
					**{"identificacion.numeroControl": "DTE-01-M001P001-000000000000001"}
				),
				"codigoGeneracion que no es UUID": construir_ccf(
					**{"identificacion.codigoGeneracion": "123"}
				),
				"hora inexistente": construir_ccf(**{"identificacion.horEmi": "25:00:00"}),
				"ventaGravada negativa": construir_ccf(**{"cuerpoDocumento.0.ventaGravada": D("-0.3")}),
				"precio unitario negativo": construir_ccf(**{"cuerpoDocumento.0.precioUni": D("-0.1")}),
				"cantidad cero": construir_ccf(**{"cuerpoDocumento.0.cantidad": D("0")}),
				"totalExenta negativo": construir_ccf(**{"resumen.totalExenta": D("-1")}),
				"valor de tributo negativo": construir_ccf(
					**{"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("-2.04")}]}
				),
				"monto total en cero": construir_ccf(**{"resumen.montoTotalOperacion": D("0")}),
				"3 decimales en el resumen": construir_ccf(**{"resumen.totalPagar": D("17.725")}),
				"9 decimales en un ítem": construir_ccf(**{"cuerpoDocumento.0.precioUni": D("0.123456789")}),
				"nombre de emisor de 201 caracteres": construir_ccf(**{"emisor.nombre": "E" * 201}),
				"nombre de receptor de 251 caracteres": construir_ccf(**{"receptor.nombre": "R" * 251}),
				"descripción de tributo de 151 caracteres": construir_ccf(
					**{"resumen.tributos": [{"codigo": "20", "descripcion": "T" * 151, "valor": D("2.04")}]}
				),
				"sin ítems": construir_ccf(cuerpoDocumento=[]),
			},
			esperado_esquema=False,
			esperado_parser=False,
		)

	def _ccf_con_n_items(self, n):
		"""CCF coherente con ``n`` ítems exentos de 0.01: solo la cantidad de ítems puede hacerlo inválido."""
		from kontaflow_sv.tests.utilidades import a_json

		doc = json.loads(construir_ccf(), parse_float=Decimal)
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
		"""``maxItems`` del esquema: 2000 se acepta y 2001 se rechaza, en el esquema y en el parser."""
		self.comprobar(
			{"2000 ítems": self._ccf_con_n_items(2000)}, esperado_esquema=True, esperado_parser=True
		)
		self.comprobar(
			{"2001 ítems": self._ccf_con_n_items(2001)}, esperado_esquema=False, esperado_parser=False
		)

	# --- diferencias que se mantienen a propósito (el parser es más tolerante que el esquema)
	def test_diferencias_intencionales(self):
		"""El parser normaliza estos formatos en lugar de rechazarlos; el esquema no los admite."""
		self.comprobar(
			{
				"codigoGeneracion en minúsculas": construir_ccf(
					**{"identificacion.codigoGeneracion": codigo(0xABCDEF).lower()}
				),
				"NIT del receptor con guiones": construir_ccf(**{"receptor.nit": "0000-000000-000-2"}),
			},
			esperado_esquema=False,
			esperado_parser=True,
		)
