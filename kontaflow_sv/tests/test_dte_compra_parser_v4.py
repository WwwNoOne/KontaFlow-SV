"""Pruebas del parser de CCF v4 y del selector de versión. No usan base de datos."""

import json
from decimal import Decimal
from unittest import mock

from frappe.tests import UnitTestCase

from kontaflow_sv.ingesta import catalogos, dte_compra
from kontaflow_sv.ingesta.dte_compra import (
	DTEInvalido,
	_escala,
	parsear_ccf_v3,
	parsear_ccf_v4,
	parsear_dte_compra,
)
from kontaflow_sv.tests.utilidades import (
	CAT_015_SECCION_1,
	CAT_015_SECCION_2,
	CAT_015_SECCION_3,
	ELIMINAR,
	a_json,
	codigo,
	construir_ccf,
)

D = Decimal


def v4(**cambios):
	return construir_ccf(version_dte=4, **cambios)


class TestParserCCFv4(UnitTestCase):
	def rechaza(self, texto, fragmento, funcion=parsear_ccf_v4):
		with self.assertRaises(DTEInvalido) as cm:
			funcion(texto)
		self.assertIn(fragmento, str(cm.exception))

	# --- aceptación y datos propios de v4
	def test_acepta_ccf_v4_valido(self):
		r = parsear_ccf_v4(v4())
		self.assertEqual(r["identificacion"]["version"], 4)
		self.assertEqual(r["identificacion"]["tipo_dte"], "03")
		self.assertEqual(r["identificacion"]["codigo_generacion"], codigo(1))
		self.assertEqual(len(r["items"]), 2)
		self.assertEqual(r["advertencias"], [])

	def test_importes_exactos_como_en_v3(self):
		r = parsear_ccf_v4(v4())
		self.assertIs(type(r["items"][0]["precio_uni"]), Decimal)
		self.assertEqual(r["items"][0]["precio_uni"], D("0.1"))
		self.assertEqual(r["items"][1]["venta_gravada"], D("15.375"))
		self.assertEqual(r["resumen"]["monto_total_operacion"], D("17.72"))
		self.assertEqual(r["resumen"]["iva"], D("2.04"))

	def test_el_resumen_usa_los_nombres_de_v4(self):
		r = parsear_ccf_v4(v4(**{"resumen.ivaPerci": D("1.25"), "resumen.ivaRete": D("0.75")}))
		self.assertEqual(r["resumen"]["iva_percibido"], D("1.25"))
		self.assertEqual(r["resumen"]["iva_retenido"], D("0.75"))
		self.assertEqual(r["resumen"]["retencion_renta"], D(0))  # v4 ya no trae reteRenta

	def test_los_nombres_de_v3_no_se_leen_en_un_documento_v4(self):
		"""``ivaRete1`` y ``reteRenta`` ya no existen en v4: no se toman por error como importes."""
		datos = json.loads(v4(), parse_float=D)
		datos["resumen"]["ivaRete1"] = D("9.99")
		datos["resumen"]["reteRenta"] = D("8.88")
		r = parsear_ccf_v4(a_json(datos))
		self.assertEqual(r["resumen"]["iva_retenido"], D(0))
		self.assertEqual(r["resumen"]["retencion_renta"], D(0))

	# --- importes obligatorios del resumen en v4 (KF-03-R): ausentes o nulos no valen 0 en silencio
	IMPORTES_OBLIGATORIOS_V4 = (
		"totalNoSuj",
		"totalExenta",
		"totalGravada",
		"subTotalVentas",
		"descuGravada",
		"totalDescu",
		"subTotal",
		"ivaPerci",
		"ivaRete",
		"montoTotalOperacion",
		"totalNoGravado",
		"totalPagar",
	)

	def test_v4_exige_los_importes_obligatorios_del_resumen(self):
		for campo in self.IMPORTES_OBLIGATORIOS_V4:
			for etiqueta, valor in (("ausente", ELIMINAR), ("nulo", None)):
				with self.subTest(campo=campo, caso=etiqueta):
					self.rechaza(v4(**{f"resumen.{campo}": valor}), f"Falta resumen.{campo}")

	def test_v4_con_los_nombres_de_v3_se_rechaza_en_lugar_de_perder_la_retencion(self):
		"""Caso de KF-03-R: ``ivaRete1`` = 0.75 en un v4 se aceptaba y la retención quedaba en 0."""
		datos = json.loads(v4(), parse_float=D)
		resumen = datos["resumen"]
		del resumen["ivaPerci"], resumen["ivaRete"]
		resumen["ivaPerci1"], resumen["ivaRete1"] = D("1.25"), D("0.75")
		self.rechaza(a_json(datos), "Falta resumen.ivaPerci")

	def test_v3_conserva_su_tolerancia_a_importes_ausentes(self):
		"""Decisión consciente: v3 trata como 0 un importe ausente (compatibilidad con lo ya ingestado)."""
		r = parsear_ccf_v3(construir_ccf(**{"resumen.ivaRete1": ELIMINAR, "resumen.ivaPerci1": ELIMINAR}))
		self.assertEqual((r["resumen"]["iva_retenido"], r["resumen"]["iva_percibido"]), (D(0), D(0)))

	# --- ceros decimales finales (KF-03-R): el valor es el mismo, el esquema los acepta
	def test_ceros_decimales_finales_no_son_decimales_de_mas(self):
		r = parsear_ccf_v4(
			v4(
				**{
					"resumen.ivaRete": D("0.7500"),
					"cuerpoDocumento.0.precioUni": D("0.100000000"),
					"cuerpoDocumento.0.cantidad": D("3.000000000"),
					"resumen.totalPagar": D("17.7200"),
				}
			)
		)
		self.assertEqual(r["resumen"]["iva_retenido"], D("0.75"))
		self.assertEqual(r["items"][0]["precio_uni"], D("0.1"))
		self.assertEqual(r["items"][0]["cantidad"], D("3"))
		self.assertEqual(r["resumen"]["total_pagar"], D("17.72"))

	def test_los_digitos_significativos_de_mas_siguen_rechazados(self):
		self.rechaza(v4(**{"resumen.ivaRete": D("0.7501")}), "más de 2 decimales")
		self.rechaza(v4(**{"cuerpoDocumento.0.precioUni": D("0.123456789")}), "más de 8 decimales")
		self.rechaza(v4(**{"cuerpoDocumento.0.precioUni": D("0.1000000001")}), "más de 8 decimales")
		self.rechaza(v4(**{"cuerpoDocumento.0.precioUni": D("1.0000000000000001")}), "más de 8 decimales")

	def test_ceros_finales_tambien_en_v3(self):
		r = parsear_ccf_v3(
			construir_ccf(
				**{"resumen.ivaRete1": D("0.7500"), "cuerpoDocumento.0.precioUni": D("0.100000000")}
			)
		)
		self.assertEqual(r["resumen"]["iva_retenido"], D("0.75"))
		self.rechaza(
			construir_ccf(**{"resumen.ivaRete1": D("0.7501")}), "más de 2 decimales", funcion=parsear_ccf_v3
		)

	def test_escala_efectiva_de_un_importe(self):
		casos = {
			"0": 0, "0.0000": 0, "0.7500": 2, "0.75": 2, "0.100000000": 1, "1E+2": 0, "1.0": 0, "10": 0,
			"0.123456789": 9, "1E-400": 400, "100.50": 1, "0.7501": 4, "-0.5000": 1,
			# termina en 0 (escala 29); sin redondeo a 28 dígitos
			"1234567890.123456789012345678901234567890": 29,
		}  # fmt: skip
		for texto, esperado in casos.items():
			with self.subTest(texto):
				self.assertEqual(_escala(D(texto)), esperado)

	def test_no_exige_extension_ni_los_campos_que_v4_elimino(self):
		datos = json.loads(v4())
		self.assertNotIn("extension", datos)
		self.assertNotIn("codEstableMH", datos["emisor"])
		parsear_ccf_v4(v4())

	def test_monto_total_en_cero_se_admite_en_v4_y_no_en_v3(self):
		"""v3: exclusiveMinimum 0; v4: minimum 0 (esquemas de Hacienda)."""
		cero = {
			"resumen.subTotal": D("0"),
			"resumen.tributos": [],
			"resumen.montoTotalOperacion": D("0"),
			"resumen.totalPagar": D("0"),
		}
		self.assertEqual(parsear_ccf_v4(v4(**cero))["resumen"]["monto_total_operacion"], D("0"))
		self.rechaza(construir_ccf(**cero), "mayor que cero", funcion=parsear_ccf_v3)

	# --- tipo y versión
	def test_rechaza_otro_tipo_y_otra_version(self):
		self.rechaza(v4(**{"identificacion.tipoDte": "05"}), "tipo de DTE 03")
		for version in (3, 5, 1, D("4.0"), True, "4", None):
			with self.subTest(version=version):
				self.rechaza(v4(**{"identificacion.version": version}), "versión 4")

	def test_cada_parser_rechaza_la_version_del_otro(self):
		self.rechaza(construir_ccf(), "versión 4", funcion=parsear_ccf_v4)
		self.rechaza(v4(), "versión 3", funcion=parsear_ccf_v3)

	# --- numeroControl: v4 exige otra estructura
	def test_numero_control_de_v4(self):
		for tipo in "MBSP":
			with self.subTest(tipo):
				parsear_ccf_v4(
					v4(**{"identificacion.numeroControl": f"DTE-03-{tipo}001P001-000000000000001"})
				)
		for malo in (
			"DTE-03-ABCD1234-000000000000001",  # válido en v3, no en v4
			"DTE-03-X001P001-000000000000001",
			"DTE-03-M001Q001-000000000000001",
			"DTE-03-M01P001-0000000000000001",
			"DTE-01-M001P001-000000000000001",
		):
			with self.subTest(malo):
				self.rechaza(v4(**{"identificacion.numeroControl": malo}), "numeroControl")

	def test_el_numero_control_de_v3_sigue_aceptando_su_formato(self):
		parsear_ccf_v3(construir_ccf(**{"identificacion.numeroControl": "DTE-03-ABCD1234-000000000000001"}))

	# --- límites propios de cada versión
	def test_limites_de_v4_frente_a_v3(self):
		casos = {
			"nombre del emisor": ("emisor.nombre", 250, 200),
			"descripción de tributo": (None, 300, 150),
			"descripción de ítem": ("cuerpoDocumento.0.descripcion", 1500, 1000),
		}
		for nombre, (ruta, max_v4, max_v3) in casos.items():
			with self.subTest(nombre):

				def cambios(n, ruta=ruta):
					if ruta is None:
						return {
							"resumen.tributos": [{"codigo": "20", "descripcion": "T" * n, "valor": D("2.04")}]
						}
					return {ruta: "X" * n}

				parsear_ccf_v4(v4(**cambios(max_v4)))
				self.rechaza(v4(**cambios(max_v4 + 1)), f"supera {max_v4}")
				parsear_ccf_v3(construir_ccf(**cambios(max_v3)))
				self.rechaza(construir_ccf(**cambios(max_v3 + 1)), f"supera {max_v3}", funcion=parsear_ccf_v3)

	def test_nombre_del_receptor_250_en_ambas_versiones(self):
		parsear_ccf_v4(v4(**{"receptor.nombre": "R" * 250}))
		self.rechaza(v4(**{"receptor.nombre": "R" * 251}), "supera 250")

	# --- reglas comunes que v4 hereda
	def test_abono_no_gravado_negativo(self):
		r = parsear_ccf_v4(
			v4(**{"cuerpoDocumento.0.noGravado": D("-5.25"), "resumen.totalNoGravado": D("-5.25")})
		)
		self.assertEqual(r["items"][0]["no_gravado"], D("-5.25"))
		self.rechaza(v4(**{"cuerpoDocumento.0.ventaGravada": D("-0.3")}), "negativo")

	def test_cuadres(self):
		self.rechaza(v4(**{"resumen.totalGravada": D("16.00")}), "totalGravada")
		self.rechaza(v4(**{"resumen.montoTotalOperacion": D("20.00")}), "montoTotalOperacion")
		parsear_ccf_v4(v4(**{"resumen.totalGravada": D("15.67")}))  # diferencia de redondeo

	def test_iva_distinto_del_13_es_advertencia(self):
		texto = v4(
			**{
				"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("3.00")}],
				"resumen.montoTotalOperacion": D("18.68"),
				"resumen.totalPagar": D("18.68"),
			}
		)
		self.assertEqual(len(parsear_ccf_v4(texto)["advertencias"]), 1)

	def _con_tributo(self, cod, monto_total):
		return v4(
			**{
				"resumen.tributos": [
					{"codigo": "20", "descripcion": "IVA", "valor": D("2.04")},
					{"codigo": cod, "descripcion": "Tributo de prueba", "valor": D("1.00")},
				],
				"resumen.montoTotalOperacion": monto_total,
				"resumen.totalPagar": monto_total,
			}
		)

	def test_tributos_informativos_no_se_suman_en_v4(self):
		for cod in CAT_015_SECCION_3:
			with self.subTest(cod):
				r = parsear_ccf_v4(self._con_tributo(cod, D("17.72")))
				self.assertEqual([t["codigo"] for t in r["tributos"]], ["20", cod])
				self.assertEqual(r["advertencias"], [])
				self.rechaza(self._con_tributo(cod, D("18.72")), "montoTotalOperacion")

	def test_tributos_de_la_seccion_1_se_suman_y_los_desconocidos_advierten(self):
		for cod in [c for c in CAT_015_SECCION_1 if c != "20"]:
			with self.subTest(cod):
				self.assertEqual(parsear_ccf_v4(self._con_tributo(cod, D("18.72")))["advertencias"], [])
				self.rechaza(self._con_tributo(cod, D("17.72")), "montoTotalOperacion")
		for cod in (*CAT_015_SECCION_2, "ZZ"):
			with self.subTest(cod):
				self.assertEqual(len(parsear_ccf_v4(self._con_tributo(cod, D("18.72")))["advertencias"]), 1)

	def test_campos_obligatorios_ausentes(self):
		for ruta in (
			"identificacion.codigoGeneracion",
			"identificacion.numeroControl",
			"emisor.nombre",
			"receptor.nit",
			"resumen.totalPagar",
			"resumen.montoTotalOperacion",
			"cuerpoDocumento.0.precioUni",
		):
			with self.subTest(ruta):
				with self.assertRaises(DTEInvalido):
					parsear_ccf_v4(v4(**{ruta: ELIMINAR}))

	def test_limite_de_2000_items(self):
		item = json.loads(v4())["cuerpoDocumento"][0]
		datos = json.loads(v4())
		datos["cuerpoDocumento"] = [{**item, "numItem": n} for n in range(1, 2002)]
		self.rechaza(json.dumps(datos), "2000 ítems")

	# --- una sola fuente de verdad para los catálogos
	def test_los_catalogos_son_los_mismos_para_todas_las_versiones(self):
		self.assertIs(dte_compra.TRIBUTOS_INFORMATIVOS, catalogos.TRIBUTOS_INFORMATIVOS)
		self.assertIs(dte_compra.TRIBUTOS_RESUMEN, catalogos.TRIBUTOS_RESUMEN)
		self.assertEqual(catalogos.TRIBUTOS_INFORMATIVOS, frozenset(CAT_015_SECCION_3))
		self.assertEqual(catalogos.TRIBUTOS_RESUMEN, frozenset(CAT_015_SECCION_1))


class TestSelectorDeVersion(UnitTestCase):
	def test_elige_el_parser_segun_la_version(self):
		self.assertEqual(parsear_dte_compra(construir_ccf()), parsear_ccf_v3(construir_ccf()))
		self.assertEqual(parsear_dte_compra(v4()), parsear_ccf_v4(v4()))
		self.assertEqual(parsear_dte_compra(construir_ccf())["identificacion"]["version"], 3)
		self.assertEqual(parsear_dte_compra(v4())["identificacion"]["version"], 4)

	def test_los_mismos_datos_en_dos_versiones_dan_el_mismo_resumen_de_negocio(self):
		a, b = parsear_dte_compra(construir_ccf()), parsear_dte_compra(v4())
		self.assertEqual(a["resumen"], b["resumen"])
		self.assertEqual(a["items"], b["items"])
		self.assertEqual(a["tributos"], b["tributos"])
		self.assertEqual(a["emisor"], b["emisor"])

	def test_rechaza_versiones_no_soportadas_con_mensaje_claro(self):
		for version in (1, 2, 5, 0, -3, 99, "3", "4", D("3.0"), D("4.5"), True, False, None, [4]):
			with self.subTest(version=version):
				with self.assertRaises(DTEInvalido) as cm:
					parsear_dte_compra(construir_ccf(**{"identificacion.version": version}))
				self.assertIn("no está soportada (se admiten: 3, 4)", str(cm.exception))

	def test_la_version_ausente_se_rechaza(self):
		with self.assertRaises(DTEInvalido) as cm:
			parsear_dte_compra(construir_ccf(**{"identificacion.version": ELIMINAR}))
		self.assertIn("no está soportada", str(cm.exception))

	def test_el_tipo_se_comprueba_antes_que_la_version(self):
		with self.assertRaises(DTEInvalido) as cm:
			parsear_dte_compra(construir_ccf(**{"identificacion.tipoDte": "05", "identificacion.version": 9}))
		self.assertIn("tipo de DTE 03", str(cm.exception))

	def test_entradas_que_no_son_un_dte(self):
		for texto, fragmento in (
			("{no json", "JSON inválido"),
			("[1]", "debe ser un objeto"),
			("{}", "identificacion"),
			(json.dumps({"dteJson": json.loads(v4())}), "identificacion"),
		):
			with self.subTest(texto=texto[:20]):
				with self.assertRaises(DTEInvalido) as cm:
					parsear_dte_compra(texto)
				self.assertIn(fragmento, str(cm.exception))

	def test_decodifica_el_json_una_sola_vez(self):
		with mock.patch.object(dte_compra, "leer_json", wraps=dte_compra.leer_json) as leer:
			parsear_dte_compra(v4())
		self.assertEqual(leer.call_count, 1)

	def test_la_version_declarada_decide_el_perfil(self):
		"""El mismo documento se valida con los límites de la versión que declara, no con otros."""
		nombre = {"emisor.nombre": "E" * 250}  # límite de v4; v3 admite 200
		r = parsear_dte_compra(v4(**nombre))  # CCF v4 válido, declara versión 4
		self.assertEqual((r["identificacion"]["version"], len(r["emisor"]["nombre"])), (4, 250))
		datos = json.loads(v4(**nombre), parse_float=D)
		datos["identificacion"]["version"] = 3  # mismo documento, declara versión 3
		with self.assertRaises(DTEInvalido) as cm:
			parsear_dte_compra(a_json(datos))
		self.assertIn("supera 200", str(cm.exception))
