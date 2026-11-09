"""Pruebas del parser de CCF v3. No usan base de datos."""

import json
from decimal import Decimal

from frappe.tests import UnitTestCase

from kontaflow_sv.ingesta.dte_compra import DTEInvalido, parsear_ccf_v3
from kontaflow_sv.tests.utilidades import ELIMINAR, codigo, construir_ccf

D = Decimal


class TestParserCCFv3(UnitTestCase):
	def rechaza(self, texto, fragmento):
		with self.assertRaises(DTEInvalido) as cm:
			parsear_ccf_v3(texto)
		self.assertIn(fragmento, str(cm.exception))

	# --- aceptación e importes exactos
	def test_acepta_ccf_valido(self):
		r = parsear_ccf_v3(construir_ccf())
		self.assertEqual(r["identificacion"]["codigo_generacion"], codigo(1))
		self.assertEqual(r["identificacion"]["tipo_dte"], "03")
		self.assertEqual(r["identificacion"]["version"], 3)
		self.assertEqual(len(r["items"]), 2)
		self.assertEqual(r["advertencias"], [])

	def test_importes_son_decimal_exactos(self):
		r = parsear_ccf_v3(construir_ccf())
		self.assertIs(type(r["items"][0]["precio_uni"]), Decimal)
		self.assertEqual(r["items"][0]["precio_uni"], D("0.1"))  # con float sería 0.1000000000000000055...
		self.assertEqual(r["items"][1]["venta_gravada"], D("15.375"))
		self.assertEqual(r["resumen"]["total_gravada"], D("15.68"))
		self.assertEqual(r["resumen"]["monto_total_operacion"], D("17.72"))
		self.assertEqual(r["resumen"]["iva"], D("2.04"))

	def test_acepta_importe_grande_que_si_cabe_exacto(self):
		texto = construir_ccf(
			**{
				"cuerpoDocumento.0.ventaGravada": D("5000000.12345678"),
				"resumen.totalGravada": D("5000015.50"),
				"resumen.subTotalVentas": D("5000015.50"),
				"resumen.subTotal": D("5000015.50"),
				"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("650002.02")}],
				"resumen.montoTotalOperacion": D("5650017.52"),
				"resumen.totalPagar": D("5650017.52"),
			}
		)
		self.assertEqual(parsear_ccf_v3(texto)["items"][0]["venta_gravada"], D("5000000.12345678"))

	def _ccf_con_item_de_muchos_digitos(self):
		"""Documento coherente en todo (totales, IVA, monto): solo el exceso de dígitos puede rechazarlo."""
		return construir_ccf(
			**{
				"cuerpoDocumento.0.ventaGravada": D("1234567890.12345678"),
				"resumen.totalGravada": D("1234567905.50"),
				"resumen.subTotalVentas": D("1234567905.50"),
				"resumen.subTotal": D("1234567905.50"),
				"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("160493827.72")}],
				"resumen.montoTotalOperacion": D("1395061733.22"),
				"resumen.totalPagar": D("1395061733.22"),
			}
		)

	def test_rechaza_item_con_demasiados_digitos_para_guardarse_exacto(self):
		self.rechaza(self._ccf_con_item_de_muchos_digitos(), "demasiados dígitos")

	# --- abonos no gravados (el signo negativo se admite solo en estos dos campos)
	def test_acepta_abono_no_gravado_negativo(self):
		texto = construir_ccf(
			**{"cuerpoDocumento.0.noGravado": D("-5.25"), "resumen.totalNoGravado": D("-5.25")}
		)
		r = parsear_ccf_v3(texto)
		self.assertEqual(r["items"][0]["no_gravado"], D("-5.25"))
		self.assertEqual(r["resumen"]["total_no_gravado"], D("-5.25"))

	def test_el_signo_negativo_sigue_rechazado_en_los_demas_campos(self):
		casos = {
			"ventaGravada": {"cuerpoDocumento.0.ventaGravada": D("-0.3")},
			"ventaExenta": {"cuerpoDocumento.0.ventaExenta": D("-1")},
			"ventaNoSuj": {"cuerpoDocumento.0.ventaNoSuj": D("-1")},
			"montoDescu": {"cuerpoDocumento.0.montoDescu": D("-1")},
			"precioUni": {"cuerpoDocumento.0.precioUni": D("-0.1")},
			"totalExenta": {"resumen.totalExenta": D("-1")},
			"ivaRete1": {"resumen.ivaRete1": D("-1")},
			"valor de tributo": {
				"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("-2.04")}]
			},
		}
		for nombre, cambios in casos.items():
			with self.subTest(nombre):
				with self.assertRaises(DTEInvalido) as cm:
					parsear_ccf_v3(construir_ccf(**cambios))
				self.assertIn("negativo", str(cm.exception))

	def test_el_abono_negativo_tambien_respeta_limite_y_decimales(self):
		self.rechaza(construir_ccf(**{"resumen.totalNoGravado": D("-1e10")}), "excede")
		self.rechaza(construir_ccf(**{"resumen.totalNoGravado": D("-1.005")}), "decimales")
		self.rechaza(construir_ccf(**{"cuerpoDocumento.0.noGravado": D("-1.123456789")}), "decimales")

	# --- tributos informativos (C5, C6, C7): se conservan pero no se suman al total
	def _con_tributo(self, codigo_tributo, monto_total):
		return construir_ccf(
			**{
				"resumen.tributos": [
					{"codigo": "20", "descripcion": "IVA", "valor": D("2.04")},
					{"codigo": codigo_tributo, "descripcion": "Tributo de prueba", "valor": D("1.00")},
				],
				"resumen.montoTotalOperacion": monto_total,
				"resumen.totalPagar": monto_total,
			}
		)

	# Copia independiente de CAT-015 (Catálogos de Facturación Electrónica de Hacienda), para que un
	# cambio accidental en las constantes del parser no pase inadvertido.
	SECCION_1 = ("20", "C3", "59", "71", "D1", "C8", "D5", "D4")  # se suman
	SECCION_2 = ("A8", "57", "90", "A6")  # del cuerpo del documento, no del resumen
	SECCION_3 = (  # de uso informativo: no se suman
		"C5", "C6", "C7", "19", "28", "31", "32", "33", "34", "35", "36", "37", "38", "39", "42", "43",
		"44", "50", "51", "52", "53", "54", "55", "58", "77", "78", "79", "85", "86", "91", "92", "A1",
		"A5", "A7", "A9",
	)  # fmt: skip

	def test_las_constantes_coinciden_con_cat_015(self):
		from kontaflow_sv.ingesta.dte_compra import TRIBUTOS_INFORMATIVOS, TRIBUTOS_RESUMEN

		self.assertEqual(len(self.SECCION_3), 35)
		self.assertEqual(TRIBUTOS_INFORMATIVOS, frozenset(self.SECCION_3))
		self.assertEqual(TRIBUTOS_RESUMEN, frozenset(self.SECCION_1))
		self.assertFalse(TRIBUTOS_INFORMATIVOS & TRIBUTOS_RESUMEN)

	def test_tributos_informativos_no_se_suman_pero_se_conservan(self):
		for codigo_tributo in self.SECCION_3:
			with self.subTest(codigo_tributo):
				r = parsear_ccf_v3(self._con_tributo(codigo_tributo, D("17.72")))  # total sin el tributo
				self.assertEqual([t["codigo"] for t in r["tributos"]], ["20", codigo_tributo])
				self.assertEqual(r["tributos"][1]["valor"], D("1.00"))
				self.assertEqual(r["advertencias"], [])
				self.rechaza(self._con_tributo(codigo_tributo, D("18.72")), "montoTotalOperacion")

	def test_el_codigo_19_no_se_suma(self):
		"""Caso reproducido en KF-02-R: el 19 (fabricante de bebidas) es informativo."""
		parsear_ccf_v3(self._con_tributo("19", D("17.72")))
		self.rechaza(self._con_tributo("19", D("18.72")), "montoTotalOperacion")

	def test_los_tributos_de_la_seccion_1_si_se_suman(self):
		for codigo_tributo in [c for c in self.SECCION_1 if c != "20"]:
			with self.subTest(codigo_tributo):
				r = parsear_ccf_v3(self._con_tributo(codigo_tributo, D("18.72")))
				self.assertEqual(r["advertencias"], [])
				self.rechaza(self._con_tributo(codigo_tributo, D("17.72")), "montoTotalOperacion")

	def test_codigos_fuera_de_las_secciones_1_y_3_se_suman_y_advierten(self):
		# La sección 2 es del cuerpo del documento y un código inexistente tampoco está en el resumen
		for codigo_tributo in (*self.SECCION_2, "ZZ"):
			with self.subTest(codigo_tributo):
				r = parsear_ccf_v3(self._con_tributo(codigo_tributo, D("18.72")))
				self.assertEqual(len(r["advertencias"]), 1)
				self.assertIn(codigo_tributo, r["advertencias"][0])
				self.rechaza(self._con_tributo(codigo_tributo, D("17.72")), "montoTotalOperacion")

	# --- largos y mínimos del esquema de CCF v3
	def test_largos_maximos_de_nombre_y_descripcion_de_tributo(self):
		parsear_ccf_v3(construir_ccf(**{"emisor.nombre": "E" * 200}))
		parsear_ccf_v3(construir_ccf(**{"receptor.nombre": "R" * 250}))
		self.rechaza(construir_ccf(**{"emisor.nombre": "E" * 201}), "emisor.nombre supera 200")
		self.rechaza(construir_ccf(**{"receptor.nombre": "R" * 251}), "receptor.nombre supera 250")
		tributo = lambda n: [{"codigo": "20", "descripcion": "T" * n, "valor": D("2.04")}]  # noqa: E731
		parsear_ccf_v3(construir_ccf(**{"resumen.tributos": tributo(150)}))
		self.rechaza(construir_ccf(**{"resumen.tributos": tributo(151)}), "descripcion supera 150")

	def test_monto_total_debe_ser_mayor_que_cero(self):
		self.rechaza(construir_ccf(**{"resumen.montoTotalOperacion": D("0")}), "mayor que cero")

	# --- límites provisionales de KontaFlow
	def test_rechaza_mas_de_2000_items_con_mensaje_claro(self):
		item = json.loads(construir_ccf())["cuerpoDocumento"][0]
		items = [{**item, "numItem": n} for n in range(1, 2002)]
		self.rechaza(json.dumps({**json.loads(construir_ccf()), "cuerpoDocumento": items}), "2000 ítems")

	def test_acepta_bytes_con_bom(self):
		r = parsear_ccf_v3(b"\xef\xbb\xbf" + construir_ccf().encode("utf-8"))
		self.assertEqual(r["identificacion"]["codigo_generacion"], codigo(1))

	def test_normaliza_codigo_y_nit(self):
		texto = construir_ccf(
			**{"identificacion.codigoGeneracion": codigo(1).lower(), "receptor.nit": "0000-000000-000-2"}
		)
		r = parsear_ccf_v3(texto)
		self.assertEqual(r["identificacion"]["codigo_generacion"], codigo(1))
		self.assertEqual(r["receptor"]["nit"], "00000000000002")

	def test_sello_es_opcional(self):
		texto = json.dumps({k: v for k, v in json.loads(construir_ccf()).items() if k != "selloRecibido"})
		self.assertIsNone(parsear_ccf_v3(texto)["identificacion"]["sello_recibido"])
		self.assertTrue(parsear_ccf_v3(construir_ccf())["identificacion"]["sello_recibido"])

	# --- tipo y versión
	def test_rechaza_otro_tipo(self):
		self.rechaza(construir_ccf(**{"identificacion.tipoDte": "05"}), "tipo de DTE 03")

	def test_rechaza_otra_version(self):
		self.rechaza(construir_ccf(**{"identificacion.version": 1}), "versión 3")
		self.rechaza(construir_ccf(**{"identificacion.version": D("3.0")}), "versión 3")
		self.rechaza(construir_ccf(**{"identificacion.version": True}), "versión 3")

	# --- entradas inválidas
	def test_rechaza_json_invalido(self):
		self.rechaza("{no es json", "JSON inválido")
		self.rechaza("[1, 2]", "debe ser un objeto")
		self.rechaza("", "JSON inválido")

	def test_rechaza_valores_no_finitos(self):
		self.rechaza('{"identificacion": {"version": NaN}}', "no permitido")

	def test_rechaza_bytes_no_utf8(self):
		self.rechaza(b"\xff\xfe\x00{", "UTF-8")

	def test_rechaza_envoltorio(self):
		self.rechaza(json.dumps({"dteJson": json.loads(construir_ccf())}), "identificacion")

	def test_rechaza_tamano_excesivo(self):
		self.rechaza(" " * 2_000_001, "tamaño máximo")

	def test_rechaza_campos_obligatorios_ausentes(self):
		for ruta in (
			"identificacion.codigoGeneracion",
			"identificacion.numeroControl",
			"identificacion.fecEmi",
			"emisor.nombre",
			"receptor.nit",
			"resumen.totalPagar",
			"resumen.subTotal",
			"resumen.montoTotalOperacion",
			"resumen.totalGravada",
			"cuerpoDocumento.0.descripcion",
			"cuerpoDocumento.0.precioUni",
		):
			with self.subTest(ruta=ruta):
				with self.assertRaises(DTEInvalido):
					parsear_ccf_v3(construir_ccf(**{ruta: ELIMINAR}))

	def test_rechaza_sin_items(self):
		self.rechaza(construir_ccf(cuerpoDocumento=[]), "al menos un ítem")

	def test_rechaza_items_repetidos(self):
		self.rechaza(construir_ccf(**{"cuerpoDocumento.1.numItem": 1}), "repetidos")

	def test_rechaza_importes_invalidos(self):
		casos = {
			"negativo": {"resumen.totalPagar": D("-1")},
			"texto": {"resumen.totalPagar": "17.72"},
			"booleano": {"resumen.totalPagar": True},
			"nulo obligatorio": {"resumen.totalPagar": None},
			"demasiado grande": {"resumen.totalPagar": D("1e10")},
			"más de 2 decimales en el resumen": {"resumen.totalPagar": D("17.725")},
			"más de 8 decimales en un ítem": {"cuerpoDocumento.0.precioUni": D("0.123456789")},
			"cantidad cero": {"cuerpoDocumento.0.cantidad": D("0")},
			"cantidad negativa": {"cuerpoDocumento.0.cantidad": D("-3")},
			"exponente enorme": {"resumen.totalPagar": D("1e400")},
			"exponente diminuto": {"resumen.totalPagar": D("1e-400")},
		}
		for nombre, cambios in casos.items():
			with self.subTest(nombre):
				with self.assertRaises(DTEInvalido):
					parsear_ccf_v3(construir_ccf(**cambios))

	def test_rechaza_identificacion_mal_formada(self):
		casos = {
			"codigoGeneracion no UUID": {"identificacion.codigoGeneracion": "1234"},
			"numeroControl sin formato": {"identificacion.numeroControl": "DTE-01-M001P001-000000000000001"},
			"fecha inexistente": {"identificacion.fecEmi": "2026-02-30"},
			"fecha con otro formato": {"identificacion.fecEmi": "04/09/2026"},
			"fecha ISO básica (la acepta fromisoformat, el DTE no)": {"identificacion.fecEmi": "20260904"},
			"hora inválida": {"identificacion.horEmi": "25:00:00"},
			"moneda distinta": {"identificacion.tipoMoneda": "EUR"},
			"ambiente desconocido": {"identificacion.ambiente": "09"},
			"NIT corto": {"receptor.nit": "123"},
		}
		for nombre, cambios in casos.items():
			with self.subTest(nombre):
				with self.assertRaises(DTEInvalido):
					parsear_ccf_v3(construir_ccf(**cambios))

	# --- cuadres
	def test_rechaza_total_gravada_que_no_cuadra(self):
		self.rechaza(construir_ccf(**{"resumen.totalGravada": D("16.00")}), "totalGravada")

	def test_acepta_diferencia_de_redondeo(self):
		# 15.675 (suma exacta de ítems) frente a 15.68 en el resumen: lo normal en un DTE real
		parsear_ccf_v3(construir_ccf(**{"resumen.totalGravada": D("15.67")}))

	def test_rechaza_monto_total_que_no_cuadra(self):
		self.rechaza(construir_ccf(**{"resumen.montoTotalOperacion": D("20.00")}), "montoTotalOperacion")

	def test_iva_distinto_del_13_es_advertencia(self):
		texto = construir_ccf(
			**{
				"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("3.00")}],
				"resumen.montoTotalOperacion": D("18.68"),
				"resumen.totalPagar": D("18.68"),
			}
		)
		r = parsear_ccf_v3(texto)
		self.assertEqual(len(r["advertencias"]), 1)
		self.assertIn("IVA", r["advertencias"][0])
