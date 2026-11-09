"""Pruebas de integración de la ingesta de un DTE de compra (CCF v3). Datos ficticios."""

import hashlib
import json
from decimal import Decimal
from unittest import mock

import frappe
from frappe.tests import IntegrationTestCase

from kontaflow_sv import api
from kontaflow_sv.ingesta import servicio
from kontaflow_sv.tests.fixtures import FixturesDePrueba
from kontaflow_sv.tests.limpieza import borrar_dte
from kontaflow_sv.tests.utilidades import (
	NIT_EMPRESA_A,
	NIT_EMPRESA_B,
	a_json,
	codigo,
	construir_ccf,
)

DOCTYPE = "KontaFlow DTE Compra"
D = Decimal

# Documentos que la ingesta nunca debe generar en esta etapa
DOCTYPES_CONTABLES = ("GL Entry", "Journal Entry", "Purchase Invoice", "Payment Entry")


class TestIngestaDTECompra(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Empresas y usuarios con nombre propio de esta ejecución: no se reutiliza ni se modifica nada
		# preexistente y al terminar se elimina solo lo que se creó aquí (ver fixtures.py).
		cls.fx = FixturesDePrueba()
		cls.addClassCleanup(cls.fx.limpiar)
		cls.fx.preparar()
		a = cls.fx.empresa("A", NIT_EMPRESA_A)
		b = cls.fx.empresa("B", NIT_EMPRESA_B)
		cls.empresa_a, cls.abbr_a = a.name, a.abbr
		cls.empresa_b, cls.abbr_b = b.name, b.abbr
		cls.usuario_a = cls.fx.usuario("a", cls.empresa_a, "Accounts Manager")
		cls.usuario_b = cls.fx.usuario("b", cls.empresa_b, "Accounts Manager")
		cls.usuario_consulta = cls.fx.usuario("consulta", cls.empresa_a, "System Manager")
		cls.usuario_contador = cls.fx.usuario("contador", cls.empresa_a, "Accounts User")

	def setUp(self):
		frappe.set_user("Administrator")
		# Solo los DTE de las empresas creadas por esta ejecución, con sus filas hijas
		borrar_dte(self.fx.nombres_de_empresas())

	def _contar(self, doctype: str) -> int:
		"""Los DTE se cuentan solo en las empresas de esta ejecución: el sitio puede tener otros."""
		if doctype == DOCTYPE:
			return frappe.db.count(doctype, {"company": ["in", self.fx.nombres_de_empresas()]})
		return frappe.db.count(doctype)  # los doctypes contables se comparan antes y después, no en absoluto

	def tearDown(self):
		frappe.set_user("Administrator")

	# --- borrador y conservación
	def test_crea_borrador_sin_asientos(self):
		antes = {d: self._contar(d) for d in DOCTYPES_CONTABLES}
		r = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		self.assertEqual(r["resultado"], "creado")
		self.assertEqual(r["name"], f"{self.abbr_a}-{codigo(1)}")
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual(doc.estado, "Borrador")
		self.assertEqual(doc.docstatus, 0)
		self.assertEqual(doc.company, self.empresa_a)
		self.assertEqual(len(doc.items), 2)
		self.assertEqual(len(doc.tributos), 1)
		self.assertEqual({d: self._contar(d) for d in DOCTYPES_CONTABLES}, antes)

	def test_conserva_el_dte_recibido(self):
		texto = construir_ccf(1)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual(doc.dte_original, texto)
		self.assertEqual(doc.dte_sha256, hashlib.sha256(texto.encode("utf-8")).hexdigest())

	def test_importes_almacenados_exactos(self):
		r = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		doc = frappe.get_doc(DOCTYPE, r["name"])

		def exacto(v):
			return D(str(v))

		self.assertEqual(exacto(doc.total_gravada), D("15.68"))
		self.assertEqual(exacto(doc.iva), D("2.04"))
		self.assertEqual(exacto(doc.monto_total_operacion), D("17.72"))
		self.assertEqual(exacto(doc.total_pagar), D("17.72"))
		self.assertEqual(exacto(doc.items[0].precio_uni), D("0.1"))
		self.assertEqual(exacto(doc.items[1].venta_gravada), D("15.375"))
		self.assertEqual(exacto(doc.tributos[0].valor), D("2.04"))
		# Lo guardado en la base de datos, sin pasar por el objeto
		fila = frappe.db.get_value(DOCTYPE, r["name"], "monto_total_operacion")
		self.assertEqual(exacto(fila), D("17.72"))

	def test_sello_y_datos_de_identificacion(self):
		r = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertTrue(doc.sello_recibido.startswith("2026ABCDEF"))
		self.assertEqual(doc.tipo_dte, "03")
		self.assertEqual(doc.version, 3)
		self.assertEqual(str(doc.fecha_emision), "2026-09-04")
		self.assertEqual(doc.emisor_nit, "00000000000001")

	def test_advertencia_de_iva_queda_registrada(self):
		texto = construir_ccf(
			1,
			**{
				"resumen.tributos": [{"codigo": "20", "descripcion": "IVA", "valor": D("3.00")}],
				"resumen.montoTotalOperacion": D("18.68"),
				"resumen.totalPagar": D("18.68"),
			},
		)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		self.assertIn("IVA", frappe.db.get_value(DOCTYPE, r["name"], "advertencias"))

	# --- entradas inválidas
	def test_rechazo_no_deja_registros(self):
		for texto in (
			"{no json",
			construir_ccf(1, **{"identificacion.tipoDte": "05"}),
			construir_ccf(1, **{"resumen.totalGravada": D("99")}),
		):
			with self.subTest(texto=texto[:30]):
				with self.assertRaises(frappe.ValidationError):
					servicio.ingestar_dte_compra(self.empresa_a, texto)
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_rechaza_receptor_de_otra_empresa(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1, receptor_nit=NIT_EMPRESA_B))
		self.assertIn("no corresponde a la empresa", str(cm.exception))
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_rechaza_empresa_sin_nit(self):
		sin_nit = self.fx.empresa("N", None).name
		with self.assertRaises(frappe.ValidationError):
			servicio.ingestar_dte_compra(sin_nit, construir_ccf(1))
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_rechaza_empresa_inexistente_o_vacia(self):
		with self.assertRaises(frappe.PermissionError):
			servicio.ingestar_dte_compra("No existe", construir_ccf(1))
		for vacia in ("", None):
			with self.subTest(empresa=vacia):
				with self.assertRaises(frappe.ValidationError) as cm:
					servicio.ingestar_dte_compra(vacia, construir_ccf(1))
				self.assertIn("Indique la empresa", str(cm.exception))
		self.assertEqual(self._contar(DOCTYPE), 0)

	# --- el contenido recibido se conserva tal cual y su hash se reproduce desde lo guardado
	def _hash_reproducible(self, crudo, n):
		r = servicio.ingestar_dte_compra(self.empresa_a, crudo)
		doc = frappe.get_doc(DOCTYPE, r["name"])
		esperado = crudo if isinstance(crudo, str) else crudo.decode("utf-8")
		self.assertEqual(doc.dte_original, esperado)
		self.assertEqual(hashlib.sha256(doc.dte_original.encode("utf-8")).hexdigest(), doc.dte_sha256)
		return r

	def test_hash_reproducible_con_bom_utf8(self):
		crudo = b"\xef\xbb\xbf" + construir_ccf(1).encode("utf-8")
		r = self._hash_reproducible(crudo, 1)
		self.assertTrue(frappe.db.get_value(DOCTYPE, r["name"], "dte_original").startswith("\ufeff"))

	def test_hash_reproducible_con_otras_variantes_de_contenido(self):
		base = construir_ccf(1)
		variantes = {
			"saltos de línea CRLF": base.replace("},{", "},\r\n{").replace('],"', '],\r\n"'),
			"salto final": base + "\n",
			"espacios al inicio y al final": "  " + base + "  \n\n",
			"texto con tildes": base.replace("Artículo de prueba uno", "Artículo con tildes: ñ é ü"),
			"BOM como texto": "\ufeff" + base,
		}
		for n, (nombre, texto) in enumerate(variantes.items(), start=1):
			with self.subTest(nombre):
				# un codigoGeneracion distinto por variante para que sean registros independientes
				contenido = texto.replace(codigo(1), codigo(100 + n))
				self._hash_reproducible(contenido, 100 + n)

	def test_reintento_con_los_mismos_bytes_y_bom_es_idempotente(self):
		crudo = b"\xef\xbb\xbf" + construir_ccf(1).encode("utf-8")
		primero = servicio.ingestar_dte_compra(self.empresa_a, crudo)
		segundo = servicio.ingestar_dte_compra(self.empresa_a, crudo)
		self.assertEqual((primero["resultado"], segundo["resultado"]), ("creado", "existente"))
		self.assertEqual(self._contar(DOCTYPE), 1)

	def test_el_mismo_documento_con_y_sin_bom_es_contenido_distinto(self):
		"""Lo guardado es lo recibido: otra codificación del mismo JSON es otro contenido y no se sobrescribe."""
		sin_bom = construir_ccf(1)
		servicio.ingestar_dte_compra(self.empresa_a, sin_bom)
		with self.assertRaises(frappe.DuplicateEntryError):
			servicio.ingestar_dte_compra(self.empresa_a, "\ufeff" + sin_bom)
		self.assertEqual(self._contar(DOCTYPE), 1)
		self.assertEqual(frappe.db.get_value(DOCTYPE, f"{self.abbr_a}-{codigo(1)}", "dte_original"), sin_bom)

	# --- abonos, tributos informativos y límites a través del servicio
	def test_ingesta_con_abono_no_gravado_negativo(self):
		texto = construir_ccf(
			1, **{"cuerpoDocumento.0.noGravado": D("-5.25"), "resumen.totalNoGravado": D("-5.25")}
		)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual(D(str(doc.total_no_gravado)), D("-5.25"))
		self.assertEqual(D(str(doc.items[0].no_gravado)), D("-5.25"))

	def test_ingesta_con_tributo_informativo_conserva_la_fila(self):
		texto = construir_ccf(
			1,
			**{
				"resumen.tributos": [
					{"codigo": "20", "descripcion": "IVA", "valor": D("2.04")},
					{"codigo": "C5", "descripcion": "Informativo", "valor": D("1.00")},
				],
			},
		)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual(sorted(t.codigo for t in doc.tributos), ["20", "C5"])
		self.assertEqual(D(str(doc.monto_total_operacion)), D("17.72"))

	def test_largos_maximos_del_esquema_se_guardan_completos(self):
		"""El esquema de CCF v3 admite nombres de hasta 200 (emisor) y 250 (receptor) y descripciones de tributo
		de hasta 150; el campo de la base de datos no debe truncarlos ni rechazarlos."""
		texto = construir_ccf(
			1,
			**{
				"emisor.nombre": "E" * 200,
				"receptor.nombre": "R" * 250,
				"resumen.tributos": [
					{"codigo": "20", "descripcion": "T" * 150, "valor": D("2.04")},
				],
			},
		)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual(doc.emisor_nombre, "E" * 200)
		self.assertEqual(doc.receptor_nombre, "R" * 250)
		self.assertEqual(doc.tributos[0].descripcion, "T" * 150)
		# Lo guardado en la base de datos, no solo lo que devuelve el objeto
		self.assertEqual(frappe.db.get_value(DOCTYPE, r["name"], "receptor_nombre"), "R" * 250)

	def test_ingesta_con_tributo_informativo_19_no_suma_al_total(self):
		"""Caso de KF-02-R: el 19 es informativo (CAT-015, sección 3)."""
		texto = construir_ccf(
			1,
			**{
				"resumen.tributos": [
					{"codigo": "20", "descripcion": "IVA", "valor": D("2.04")},
					{"codigo": "19", "descripcion": "Fabricante de bebidas", "valor": D("1.00")},
				],
			},
		)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual(sorted(t.codigo for t in doc.tributos), ["19", "20"])
		self.assertEqual(D(str(doc.monto_total_operacion)), D("17.72"))
		self.assertFalse(doc.advertencias)

	def test_documento_demasiado_grande_se_rechaza_con_mensaje_claro(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1) + " " * 2_000_001)
		self.assertIn("tamaño máximo", str(cm.exception))
		self.assertEqual(self._contar(DOCTYPE), 0)

	# --- reintento e idempotencia
	def test_reintento_idempotente(self):
		texto = construir_ccf(1)
		primero = servicio.ingestar_dte_compra(self.empresa_a, texto)
		modificado = frappe.db.get_value(DOCTYPE, primero["name"], "modified")
		segundo = servicio.ingestar_dte_compra(self.empresa_a, texto)
		self.assertEqual(primero["resultado"], "creado")
		self.assertEqual(segundo["resultado"], "existente")
		self.assertEqual(primero["name"], segundo["name"])
		self.assertEqual(self._contar(DOCTYPE), 1)
		self.assertEqual(frappe.db.get_value(DOCTYPE, primero["name"], "modified"), modificado)
		self.assertEqual(frappe.db.count("KontaFlow DTE Compra Item", {"parent": primero["name"]}), 2)

	def test_codigo_en_minusculas_es_el_mismo_documento_y_no_un_segundo_registro(self):
		"""El codigoGeneracion se normaliza (Oculus hace lo mismo): otra capitalización no crea otro registro."""
		n = 0xABCDEF  # UUID con letras, para que mayúsculas y minúsculas sean distintas
		self.assertNotEqual(codigo(n), codigo(n).lower())
		servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(n))
		minusculas = construir_ccf(n, **{"identificacion.codigoGeneracion": codigo(n).lower()})
		with self.assertRaises(frappe.DuplicateEntryError):  # mismo documento, contenido distinto
			servicio.ingestar_dte_compra(self.empresa_a, minusculas)
		self.assertEqual(self._contar(DOCTYPE), 1)
		self.assertEqual(
			frappe.db.get_value(DOCTYPE, f"{self.abbr_a}-{codigo(n)}", "codigo_generacion"), codigo(n)
		)

	def test_mismo_codigo_con_contenido_distinto_se_rechaza_sin_tocar_el_original(self):
		original = construir_ccf(1)
		r = servicio.ingestar_dte_compra(self.empresa_a, original)
		distinto = construir_ccf(1, **{"cuerpoDocumento.0.descripcion": "Otra descripción"})
		with self.assertRaises(frappe.DuplicateEntryError):
			servicio.ingestar_dte_compra(self.empresa_a, distinto)
		self.assertEqual(self._contar(DOCTYPE), 1)
		self.assertEqual(frappe.db.get_value(DOCTYPE, r["name"], "dte_original"), original)

	def _con_carrera(self):
		"""Hace que la primera comprobación de existencia no vea el documento, como en una carrera real."""
		real = servicio._existente
		llamadas = []

		def falso(nombre, huella, **kw):
			llamadas.append(nombre)
			return None if len(llamadas) == 1 else real(nombre, huella, **kw)

		return mock.patch.object(servicio, "_existente", side_effect=falso), llamadas

	def test_concurrencia_simulada_mismo_contenido(self):
		"""Otra petición inserta el mismo documento entre la comprobación y la inserción."""
		texto = construir_ccf(1)
		servicio.ingestar_dte_compra(self.empresa_a, texto)
		parche, llamadas = self._con_carrera()
		with parche:
			r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		self.assertEqual(len(llamadas), 2)  # confirma que se recorrió la ruta de DuplicateEntryError
		self.assertEqual(r["resultado"], "existente")
		self.assertEqual(self._contar(DOCTYPE), 1)

	def test_concurrencia_simulada_contenido_distinto(self):
		original = construir_ccf(1)
		servicio.ingestar_dte_compra(self.empresa_a, original)
		parche, llamadas = self._con_carrera()
		with parche, self.assertRaises(frappe.DuplicateEntryError):
			servicio.ingestar_dte_compra(
				self.empresa_a, construir_ccf(1, **{"cuerpoDocumento.0.descripcion": "Otra"})
			)
		self.assertEqual(len(llamadas), 2)
		self.assertEqual(self._contar(DOCTYPE), 1)
		self.assertEqual(frappe.db.get_value(DOCTYPE, f"{self.abbr_a}-{codigo(1)}", "dte_original"), original)

	# --- aislamiento entre empresas
	def test_mismo_codigo_en_dos_empresas_son_registros_independientes(self):
		a = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1, receptor_nit=NIT_EMPRESA_A))
		b = servicio.ingestar_dte_compra(self.empresa_b, construir_ccf(1, receptor_nit=NIT_EMPRESA_B))
		self.assertNotEqual(a["name"], b["name"])
		self.assertEqual(frappe.db.get_value(DOCTYPE, a["name"], "company"), self.empresa_a)
		self.assertEqual(frappe.db.get_value(DOCTYPE, b["name"], "company"), self.empresa_b)
		self.assertEqual(self._contar(DOCTYPE), 2)

	def test_usuario_no_puede_ingestar_en_empresa_ajena(self):
		frappe.set_user(self.usuario_a)
		with self.assertRaises(frappe.PermissionError):
			servicio.ingestar_dte_compra(self.empresa_b, construir_ccf(1, receptor_nit=NIT_EMPRESA_B))
		frappe.set_user("Administrator")
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_sin_acceso_no_revela_si_la_empresa_existe_ni_valida_el_contenido(self):
		"""Quien no tiene acceso recibe el mismo error para una empresa ajena y para una inexistente,
		y antes de que se lea el documento (un JSON inválido no cambia la respuesta)."""
		frappe.set_user(self.usuario_a)
		mensajes = set()
		for empresa, texto in (
			(self.empresa_b, "{no json"),
			(self.empresa_b, construir_ccf(1, receptor_nit=NIT_EMPRESA_B)),
			("Empresa que no existe", "{no json"),
		):
			with self.assertRaises(frappe.PermissionError) as cm:
				servicio.ingestar_dte_compra(empresa, texto)
			mensajes.add(str(cm.exception))
		self.assertEqual(len(mensajes), 1)

	def test_usuario_ingesta_en_su_empresa_y_no_ve_las_de_otra(self):
		ajeno = servicio.ingestar_dte_compra(self.empresa_b, construir_ccf(2, receptor_nit=NIT_EMPRESA_B))
		frappe.set_user(self.usuario_a)
		propio = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		visibles = [d.name for d in frappe.get_list(DOCTYPE, fields=["name"])]
		self.assertIn(propio["name"], visibles)
		self.assertNotIn(ajeno["name"], visibles)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(DOCTYPE, ajeno["name"]).check_permission("read")

	# --- el DTE recibido no se manipula
	def test_no_se_crea_a_mano(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": DOCTYPE,
					"company": self.empresa_a,
					"codigo_generacion": codigo(7),
					"estado": "Borrador",
				}
			).insert()
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_no_se_modifica_despues_de_ingestado(self):
		r = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		doc = frappe.get_doc(DOCTYPE, r["name"])
		doc.total_pagar = 1
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		doc = frappe.get_doc(DOCTYPE, r["name"])
		doc.items[0].venta_gravada = 999
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		self.assertEqual(D(str(frappe.db.get_value(DOCTYPE, r["name"], "total_pagar"))), D("17.72"))

	def test_el_estado_solo_puede_ser_borrador(self):
		meta = frappe.get_meta(DOCTYPE)
		self.assertEqual(meta.get_field("estado").options, "Borrador")

	# --- permisos: importar y consultar, solo en las empresas autorizadas; sin editar ni borrar
	def test_contador_puede_importar_y_consultar_en_su_empresa(self):
		frappe.set_user(self.usuario_contador)
		r = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		self.assertEqual(frappe.get_doc(DOCTYPE, r["name"]).company, self.empresa_a)

	def test_nadie_salvo_administrator_puede_editar_ni_borrar(self):
		r = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		for usuario in (self.usuario_a, self.usuario_contador, self.usuario_consulta):
			with self.subTest(usuario=usuario):
				frappe.set_user(usuario)
				self.assertFalse(frappe.has_permission(DOCTYPE, "write", r["name"]))
				self.assertFalse(frappe.has_permission(DOCTYPE, "delete", r["name"]))
				with self.assertRaises(frappe.PermissionError):
					frappe.delete_doc(DOCTYPE, r["name"])
				with self.assertRaises(frappe.PermissionError):
					doc = frappe.get_doc(DOCTYPE, r["name"])
					doc.total_pagar = 1
					doc.save()
		frappe.set_user("Administrator")
		self.assertEqual(self._contar(DOCTYPE), 1)

	def test_system_manager_consulta_solo_dentro_de_su_alcance(self):
		propio = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		ajeno = servicio.ingestar_dte_compra(self.empresa_b, construir_ccf(2, receptor_nit=NIT_EMPRESA_B))
		frappe.set_user(self.usuario_consulta)
		self.assertTrue(frappe.has_permission(DOCTYPE, "read", propio["name"]))
		self.assertFalse(frappe.has_permission(DOCTYPE, "read", ajeno["name"]))
		visibles = [d.name for d in frappe.get_list(DOCTYPE, fields=["name"])]
		self.assertEqual(visibles, [propio["name"]])

	def test_system_manager_no_puede_importar(self):
		frappe.set_user(self.usuario_consulta)
		with self.assertRaises(frappe.PermissionError):
			servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		frappe.set_user("Administrator")
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_el_doctype_no_concede_compartir_ni_enviar_por_correo(self):
		meta = frappe.get_meta(DOCTYPE)
		for permiso in meta.permissions:
			self.assertFalse(permiso.share, permiso.role)
			self.assertFalse(permiso.email, permiso.role)
			self.assertFalse(permiso.write, permiso.role)
			self.assertFalse(permiso.delete, permiso.role)

	# --- CCF v4 y selector de versión
	def test_ingesta_de_ccf_v4_como_borrador(self):
		antes = {d: self._contar(d) for d in DOCTYPES_CONTABLES}
		texto = construir_ccf(
			1, version_dte=4, **{"resumen.ivaRete": D("0.75"), "resumen.ivaPerci": D("1.25")}
		)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		self.assertEqual(r["resultado"], "creado")
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual((doc.estado, doc.docstatus, doc.company), ("Borrador", 0, self.empresa_a))
		self.assertEqual((doc.tipo_dte, doc.version), ("03", 4))
		self.assertEqual(len(doc.items), 2)
		self.assertEqual(D(str(doc.monto_total_operacion)), D("17.72"))
		self.assertEqual(D(str(doc.iva_retenido)), D("0.75"))
		self.assertEqual(D(str(doc.iva_percibido)), D("1.25"))
		self.assertEqual(D(str(doc.retencion_renta)), D("0"))  # v4 ya no trae reteRenta
		self.assertEqual(doc.dte_original, texto)
		self.assertEqual(hashlib.sha256(doc.dte_original.encode("utf-8")).hexdigest(), doc.dte_sha256)
		self.assertEqual({d: self._contar(d) for d in DOCTYPES_CONTABLES}, antes)

	def test_v4_con_ceros_decimales_finales_conserva_el_json_original(self):
		"""KF-03-R: ``0.7500`` es el valor 0.75; se guarda el número y el texto recibido queda tal cual."""
		texto = construir_ccf(
			1,
			version_dte=4,
			**{"resumen.ivaRete": D("0.7500"), "cuerpoDocumento.0.precioUni": D("0.100000000")},
		)
		self.assertIn("0.7500", texto)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual(D(str(doc.iva_retenido)), D("0.75"))
		self.assertEqual(D(str(doc.items[0].precio_uni)), D("0.1"))
		self.assertEqual(doc.dte_original, texto)  # los ceros finales siguen en el original
		self.assertIn("0.7500", doc.dte_original)
		self.assertEqual(hashlib.sha256(doc.dte_original.encode("utf-8")).hexdigest(), doc.dte_sha256)

	def test_v4_sin_los_importes_obligatorios_no_deja_registros(self):
		datos = json.loads(construir_ccf(1, version_dte=4), parse_float=D)
		resumen = datos["resumen"]
		del resumen["ivaPerci"], resumen["ivaRete"]
		resumen["ivaPerci1"], resumen["ivaRete1"] = D("1.25"), D("0.75")
		with self.assertRaises(frappe.ValidationError) as cm:
			servicio.ingestar_dte_compra(self.empresa_a, a_json(datos))
		self.assertIn("Falta resumen.ivaPerci", str(cm.exception))
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_v3_y_v4_conviven_en_la_misma_empresa(self):
		a = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		b = servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(2, version_dte=4))
		self.assertEqual((a["resultado"], b["resultado"]), ("creado", "creado"))
		self.assertEqual(frappe.db.get_value(DOCTYPE, a["name"], "version"), 3)
		self.assertEqual(frappe.db.get_value(DOCTYPE, b["name"], "version"), 4)
		self.assertEqual(self._contar(DOCTYPE), 2)

	def test_reintento_identico_de_v4_es_idempotente(self):
		texto = construir_ccf(1, version_dte=4)
		primero = servicio.ingestar_dte_compra(self.empresa_a, texto)
		segundo = servicio.ingestar_dte_compra(self.empresa_a, texto)
		self.assertEqual((primero["resultado"], segundo["resultado"]), ("creado", "existente"))
		self.assertEqual(primero["name"], segundo["name"])
		self.assertEqual(self._contar(DOCTYPE), 1)

	def _conflicto_entre_versiones(self, primera, segunda):
		original = construir_ccf(1, version_dte=primera)
		r = servicio.ingestar_dte_compra(self.empresa_a, original)
		with self.assertRaises(frappe.DuplicateEntryError) as cm:
			servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1, version_dte=segunda))
		mensaje = str(cm.exception)
		self.assertIn(f"versión {primera}", mensaje)
		self.assertIn(f"versión {segunda}", mensaje)
		self.assertIn("no puede tener dos versiones", mensaje)
		# El original queda intacto: no se sobrescribe ni se duplica
		self.assertEqual(self._contar(DOCTYPE), 1)
		self.assertEqual(frappe.db.get_value(DOCTYPE, r["name"], "dte_original"), original)
		self.assertEqual(frappe.db.get_value(DOCTYPE, r["name"], "version"), primera)

	def test_mismo_codigo_en_otra_version_es_conflicto_v3_luego_v4(self):
		self._conflicto_entre_versiones(3, 4)

	def test_mismo_codigo_en_otra_version_es_conflicto_v4_luego_v3(self):
		self._conflicto_entre_versiones(4, 3)

	def test_mismo_codigo_en_otra_version_en_otra_empresa_no_choca(self):
		servicio.ingestar_dte_compra(self.empresa_a, construir_ccf(1, version_dte=3))
		b = servicio.ingestar_dte_compra(
			self.empresa_b, construir_ccf(1, receptor_nit=NIT_EMPRESA_B, version_dte=4)
		)
		self.assertEqual(b["resultado"], "creado")

	def test_versiones_no_soportadas_se_rechazan_sin_dejar_registros(self):
		for version in (1, 2, 5, "4", None):
			with self.subTest(version=version):
				with self.assertRaises(frappe.ValidationError) as cm:
					servicio.ingestar_dte_compra(
						self.empresa_a, construir_ccf(1, **{"identificacion.version": version})
					)
				self.assertIn("no está soportada", str(cm.exception))
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_v4_rechaza_receptor_de_otra_empresa(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			servicio.ingestar_dte_compra(
				self.empresa_a, construir_ccf(1, receptor_nit=NIT_EMPRESA_B, version_dte=4)
			)
		self.assertIn("no corresponde a la empresa", str(cm.exception))
		self.assertEqual(self._contar(DOCTYPE), 0)

	def test_largos_maximos_de_v4_se_guardan_completos(self):
		"""v4 admite nombres de emisor de hasta 250 y descripciones de tributo de hasta 300."""
		texto = construir_ccf(
			1,
			version_dte=4,
			**{
				"emisor.nombre": "E" * 250,
				"receptor.nombre": "R" * 250,
				"resumen.tributos": [{"codigo": "20", "descripcion": "T" * 300, "valor": D("2.04")}],
			},
		)
		r = servicio.ingestar_dte_compra(self.empresa_a, texto)
		doc = frappe.get_doc(DOCTYPE, r["name"])
		self.assertEqual(doc.emisor_nombre, "E" * 250)
		self.assertEqual(doc.receptor_nombre, "R" * 250)
		self.assertEqual(doc.tributos[0].descripcion, "T" * 300)
		self.assertEqual(frappe.db.get_value(DOCTYPE, r["name"], "emisor_nombre"), "E" * 250)

	def test_v4_con_tributo_informativo_19_no_suma_al_total(self):
		texto = construir_ccf(
			1,
			version_dte=4,
			**{
				"resumen.tributos": [
					{"codigo": "20", "descripcion": "IVA", "valor": D("2.04")},
					{"codigo": "19", "descripcion": "Fabricante de bebidas", "valor": D("1.00")},
				],
			},
		)
		doc = frappe.get_doc(DOCTYPE, servicio.ingestar_dte_compra(self.empresa_a, texto)["name"])
		self.assertEqual(sorted(t.codigo for t in doc.tributos), ["19", "20"])
		self.assertEqual(D(str(doc.monto_total_operacion)), D("17.72"))

	# --- API
	def test_api_whitelisted_solo_post(self):
		self.assertIn(api.ingestar_dte_compra, frappe.whitelisted)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[api.ingestar_dte_compra], ("POST",))

	def test_api_ingesta(self):
		r = api.ingestar_dte_compra(self.empresa_a, construir_ccf(1))
		self.assertEqual(r["resultado"], "creado")

	def test_api_ingesta_v4(self):
		r = api.ingestar_dte_compra(self.empresa_a, construir_ccf(2, version_dte=4))
		self.assertEqual(r["resultado"], "creado")
		self.assertEqual(frappe.db.get_value(DOCTYPE, r["name"], "version"), 4)
