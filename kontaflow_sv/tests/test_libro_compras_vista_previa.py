"""Pruebas de las filas y los totales de la vista previa del Libro de Compras (KF-04.2). Datos ficticios."""

from decimal import Decimal

import frappe
from frappe.tests import IntegrationTestCase

from kontaflow_sv.ingesta import servicio
from kontaflow_sv.libro_compras import vista_previa as vp
from kontaflow_sv.tests.fixtures import FixturesDePrueba
from kontaflow_sv.tests.limpieza import borrar_dte
from kontaflow_sv.tests.utilidades import ELIMINAR, NIT_EMPRESA_A, NIT_EMPRESA_B, codigo, construir_ccf

D = Decimal
CERO = dict.fromkeys(vp.COLUMNAS_MONETARIAS, D(0))


def ccf_con_importes(
	n, fecha, gravada="0", exenta="0", no_suj="0", iva=None, receptor_nit=NIT_EMPRESA_A, **kw
):
	"""CCF coherente de un solo ítem con los importes indicados. Sin ``iva`` se usa el 13 % redondeado,
	que no produce advertencia; un ``iva`` distinto la produce."""
	g, e, ns = D(gravada), D(exenta), D(no_suj)
	iva = (g * D("0.13")).quantize(D("0.01")) if iva is None else D(iva)
	sub_total = g + e + ns
	cambios = {
		"identificacion.fecEmi": fecha,
		"cuerpoDocumento.1": ELIMINAR,
		"cuerpoDocumento.0.cantidad": D("1"),
		"cuerpoDocumento.0.precioUni": sub_total,
		"cuerpoDocumento.0.ventaGravada": g,
		"cuerpoDocumento.0.ventaExenta": e,
		"cuerpoDocumento.0.ventaNoSuj": ns,
		"resumen.totalGravada": g,
		"resumen.totalExenta": e,
		"resumen.totalNoSuj": ns,
		"resumen.subTotalVentas": sub_total,
		"resumen.subTotal": sub_total,
		"resumen.tributos": [{"codigo": "20", "descripcion": "IVA 13%", "valor": iva}],
		"resumen.montoTotalOperacion": sub_total + iva,
		"resumen.totalPagar": sub_total + iva,
	}
	return construir_ccf(n, receptor_nit=receptor_nit, **{**cambios, **kw})


class TestVistaPrevia(IntegrationTestCase):
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

	def setUp(self):
		frappe.set_user("Administrator")
		borrar_dte(self.fx.nombres_de_empresas())

	def tearDown(self):
		frappe.set_user("Administrator")

	def _ingestar(self, n, fecha="2026-09-15", empresa=None, **importes) -> str:
		empresa = empresa or self.empresa_a
		nit = NIT_EMPRESA_A if empresa == self.empresa_a else NIT_EMPRESA_B
		texto = ccf_con_importes(n, fecha, receptor_nit=nit, **importes)
		return servicio.ingestar_dte_compra(empresa, texto)["name"]

	def _comprobar_cuadre(self, resultado):
		"""Los totales son la suma de las filas, sin filas repetidas."""
		nombres = [f["name"] for f in resultado["filas"]]
		self.assertEqual(len(nombres), len(set(nombres)))
		for columna in vp.COLUMNAS_MONETARIAS:
			self.assertEqual(
				resultado["totales"][columna], sum((f[columna] for f in resultado["filas"]), D(0))
			)

	# --- filas
	def test_fila_con_columnas_e_importes_exactos(self):
		nombre = self._ingestar(1, gravada="1234.56", exenta="7.89", no_suj="0.01")
		[fila] = vp.vista_previa(self.empresa_a, "2026-09")["filas"]
		self.assertEqual(
			tuple(fila),
			(
				"name",
				"fecha_emision",
				"codigo_generacion",
				"numero_control",
				"sello_recibido",
				"emisor_nombre",
				"emisor_nit",
				"emisor_nrc",
				"total_gravada",
				"total_exenta",
				"total_no_suj",
				"iva",
				"advertencias",
			),
		)
		self.assertEqual(fila["name"], nombre)
		self.assertEqual(str(fila["fecha_emision"]), "2026-09-15")
		self.assertEqual(fila["emisor_nombre"], "PROVEEDOR DE PRUEBA, S.A. DE C.V.")
		self.assertEqual(fila["emisor_nit"], "00000000000001")
		self.assertEqual(fila["numero_control"], "DTE-03-M001P001-000000000000001")
		self.assertEqual(fila["codigo_generacion"], codigo(1))
		self.assertEqual(fila["emisor_nrc"], "100001")
		self.assertEqual(fila["sello_recibido"], "2026ABCDEF0123456789ABCDEF0123456789ABCD")
		esperado = {
			"total_gravada": D("1234.56"),
			"total_exenta": D("7.89"),
			"total_no_suj": D("0.01"),
			"iva": D("160.49"),
		}
		for columna, valor in esperado.items():
			self.assertIsInstance(fila[columna], Decimal)
			self.assertEqual(fila[columna], valor, columna)
		self.assertEqual(fila["advertencias"], [])

	def test_ccf_enteramente_exento_no_se_trata_como_gravado(self):
		"""Con totalGravada 0 no se sustituye la base por el subtotal ni se calcula un 13 % (Oculus sí lo
		hace): exentas 100, gravadas 0 e IVA 0, tal como están en el DTE."""
		self._ingestar(1, exenta="100.00")
		resultado = vp.vista_previa(self.empresa_a, "2026-09")
		[fila] = resultado["filas"]
		self.assertEqual(
			{c: fila[c] for c in vp.COLUMNAS_MONETARIAS},
			{"total_gravada": D("0"), "total_exenta": D("100.00"), "total_no_suj": D("0"), "iva": D("0")},
		)
		self.assertEqual(fila["advertencias"], [])
		self.assertEqual(resultado["totales"]["iva"], D("0"))

	def test_control_del_iva_usa_la_base_gravada_neta_de_descuentos(self):
		"""El 13 % se calcula sobre gravadas menos el descuento gravado: 13 % de 90 = 11.70 no avisa; un IVA
		de 13.00 (13 % sin descontar) sí. En ambos casos la fila muestra el IVA del DTE."""
		for n, iva, avisa in ((1, "11.70", False), (2, "13.00", True)):
			with self.subTest(iva=iva):
				texto = ccf_con_importes(
					n,
					"2026-09-15",
					gravada="100.00",
					iva=iva,
					**{
						"resumen.descuGravada": D("10.00"),
						"resumen.totalDescu": D("10.00"),
						"resumen.subTotal": D("90.00"),
						"resumen.montoTotalOperacion": D("90.00") + D(iva),
						"resumen.totalPagar": D("90.00") + D(iva),
					},
				)
				nombre = servicio.ingestar_dte_compra(self.empresa_a, texto)["name"]
				filas = {f["name"]: f for f in vp.vista_previa(self.empresa_a, "2026-09")["filas"]}
				self.assertEqual(filas[nombre]["iva"], D(iva))
				self.assertEqual(filas[nombre]["total_gravada"], D("100.00"))
				self.assertEqual(bool(filas[nombre]["advertencias"]), avisa)

	def test_sello_ausente_queda_vacio(self):
		texto = ccf_con_importes(1, "2026-09-15", gravada="1.00", selloRecibido=ELIMINAR)
		servicio.ingestar_dte_compra(self.empresa_a, texto)
		[fila] = vp.vista_previa(self.empresa_a, "2026-09")["filas"]
		self.assertIn(fila["sello_recibido"], (None, ""))
		self.assertEqual(fila["codigo_generacion"], codigo(1))

	def test_importes_guardados_y_no_recalculados(self):
		"""El IVA es el del DTE aunque no sea el 13 % de la base: la vista previa no lo recalcula."""
		self._ingestar(1, gravada="100.00", iva="12.00")
		[fila] = vp.vista_previa(self.empresa_a, "2026-09")["filas"]
		self.assertEqual(fila["iva"], D("12.00"))

	def test_fila_con_advertencia(self):
		con_aviso = self._ingestar(1, gravada="100.00", iva="12.00", fecha="2026-09-01")
		sin_aviso = self._ingestar(2, gravada="10.00", fecha="2026-09-02")
		resultado = vp.vista_previa(self.empresa_a, "2026-09")
		filas = {f["name"]: f for f in resultado["filas"]}
		self.assertEqual(len(filas[con_aviso]["advertencias"]), 1)
		self.assertIn("IVA", filas[con_aviso]["advertencias"][0])
		self.assertEqual(filas[sin_aviso]["advertencias"], [])
		self.assertEqual(resultado["totales"]["iva"], D("13.30"))  # la fila con advertencia también suma
		self._comprobar_cuadre(resultado)

	def test_varias_advertencias_se_conservan_por_separado(self):
		texto = ccf_con_importes(
			1,
			"2026-09-15",
			gravada="100.00",
			iva="12.00",
			**{
				"resumen.tributos": [
					{"codigo": "20", "descripcion": "IVA 13%", "valor": D("12.00")},
					{"codigo": "ZZ", "descripcion": "Tributo ficticio", "valor": D("1.00")},
				],
				"resumen.montoTotalOperacion": D("113.00"),
				"resumen.totalPagar": D("113.00"),
			},
		)
		servicio.ingestar_dte_compra(self.empresa_a, texto)
		[fila] = vp.vista_previa(self.empresa_a, "2026-09")["filas"]
		self.assertEqual(len(fila["advertencias"]), 2)
		self.assertTrue(all(a.strip() for a in fila["advertencias"]))

	# --- totales
	def test_importes_fraccionarios_suman_sin_error_de_coma_flotante(self):
		# Diez veces 0.10 suma 0.9999999999999999 en float; en Decimal, exactamente 1.00
		for n in range(1, 11):
			self._ingestar(n, gravada="0.10", exenta="0.07", no_suj="0.03")
		resultado = vp.vista_previa(self.empresa_a, "2026-09")
		self.assertEqual(len(resultado["filas"]), 10)
		self.assertEqual(
			resultado["totales"],
			{
				"total_gravada": D("1.00"),
				"total_exenta": D("0.70"),
				"total_no_suj": D("0.30"),
				"iva": D("0.10"),
			},
		)
		self._comprobar_cuadre(resultado)

	def test_totales_con_importes_grandes(self):
		# El total de la operación debe quedar por debajo del límite del parser (1e10)
		self._ingestar(1, gravada="7654321098.76")  # IVA 995061742.84
		self._ingestar(2, gravada="7654321098.76")
		self._ingestar(3, gravada="0.01")  # IVA 0.00
		resultado = vp.vista_previa(self.empresa_a, "2026-09")
		self.assertEqual(resultado["totales"]["total_gravada"], D("15308642197.53"))
		self.assertEqual(resultado["totales"]["iva"], D("1990123485.68"))
		self._comprobar_cuadre(resultado)

	def test_periodo_vacio(self):
		self._ingestar(1, fecha="2026-08-31", gravada="5.00")
		self.assertEqual(vp.vista_previa(self.empresa_a, "2026-09"), {"filas": [], "totales": CERO})

	def test_solo_suma_el_mes_y_la_empresa(self):
		dentro = self._ingestar(1, fecha="2026-09-30", gravada="1.00")
		self._ingestar(2, fecha="2026-10-01", gravada="20.00")
		self._ingestar(3, fecha="2026-09-15", gravada="300.00", empresa=self.empresa_b)
		resultado = vp.vista_previa(self.empresa_a, "2026-09")
		self.assertEqual([f["name"] for f in resultado["filas"]], [dentro])
		self.assertEqual(resultado["totales"]["total_gravada"], D("1.00"))

	def test_v3_y_v4_suman_juntos(self):
		self._ingestar(1, gravada="1.10")
		texto = ccf_con_importes(2, "2026-09-16", gravada="2.20", version_dte=4)
		servicio.ingestar_dte_compra(self.empresa_a, texto)
		resultado = vp.vista_previa(self.empresa_a, "2026-09")
		self.assertEqual(resultado["totales"]["total_gravada"], D("3.30"))
		self._comprobar_cuadre(resultado)

	# --- permisos
	def test_usuario_autorizado_obtiene_los_mismos_totales(self):
		self._ingestar(1, gravada="1.10")
		self._ingestar(2, gravada="2.20", empresa=self.empresa_b)
		esperado = vp.vista_previa(self.empresa_a, "2026-09")
		frappe.set_user(self.gerente_a)
		self.assertEqual(vp.vista_previa(self.empresa_a, "2026-09"), esperado)

	def test_empresa_ajena_y_mes_invalido(self):
		self._ingestar(1, gravada="2.20", empresa=self.empresa_b)
		frappe.set_user(self.gerente_a)
		with self.assertRaises(frappe.PermissionError):
			vp.vista_previa(self.empresa_b, "2026-09")
		with self.assertRaises(frappe.ValidationError):
			vp.vista_previa(self.empresa_a, "2026-13")

	def test_la_vista_previa_no_modifica_registros(self):
		nombre = self._ingestar(1, gravada="1.10")
		antes = frappe.db.get_value(
			"KontaFlow DTE Compra", nombre, ["modified", "dte_sha256", "total_gravada"]
		)
		vp.vista_previa(self.empresa_a, "2026-09")
		self.assertEqual(
			frappe.db.get_value("KontaFlow DTE Compra", nombre, ["modified", "dte_sha256", "total_gravada"]),
			antes,
		)
