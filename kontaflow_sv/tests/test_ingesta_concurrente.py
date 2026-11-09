"""Solicitudes simultáneas reales: varios procesos, cada uno con su propia conexión y transacción.

A diferencia de las pruebas simuladas de ``test_ingesta_dte_compra``, aquí la base de datos arbitra de
verdad. Como los procesos son independientes, los datos de la empresa de prueba se confirman (commit).
La empresa lleva un nombre propio de la ejecución (ver ``fixtures.py``): se aborta si ya existe y al
terminar se elimina únicamente lo que esta ejecución creó.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter

import frappe
from frappe.tests import IntegrationTestCase

from kontaflow_sv.ingesta import servicio
from kontaflow_sv.tests.fixtures import FixturesDePrueba
from kontaflow_sv.tests.limpieza import borrar_dte
from kontaflow_sv.tests.utilidades import codigo, construir_ccf

DOCTYPE = "KontaFlow DTE Compra"
NIT_EMPRESA_C = "00000000000004"
PROCESOS = 6
ESPERA_ARRANQUE = 8  # segundos para que todos los procesos conecten antes de la salida común


class TestIngestaConcurrente(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.fx = FixturesDePrueba()
		# addClassCleanup se ejecuta incluso si setUpClass falla a mitad: nunca quedan datos confirmados
		cls.addClassCleanup(cls._retirar_fixtures)
		cls.fx.preparar()
		cls.empresa = cls.fx.empresa("C", NIT_EMPRESA_C)
		# Registros que crean estas pruebas: los de la empresa propia y con estos nombres, nada más.
		cls.nombres = [f"{cls.empresa.abbr}-{codigo(n)}" for n in range(1, 4)]
		frappe.db.commit()

	@classmethod
	def _retirar_fixtures(cls):
		frappe.set_user("Administrator")
		try:
			cls.fx.limpiar()
		finally:
			frappe.db.commit()  # aunque algo falle, lo ya retirado se confirma: no queda nada a medias

	def _limpiar(self):
		borrar_dte([self.empresa.name], self.nombres)

	def setUp(self):
		frappe.set_user("Administrator")
		self._limpiar()
		frappe.db.commit()

	def test_la_limpieza_no_toca_registros_ajenos(self):
		"""Regresión de KF-02-R: la limpieza borraba todos los DTE del sitio y confirmaba el borrado.

		Se crean y confirman dos registros que NO son de la ejecución: uno de otra empresa y otro de la
		empresa de prueba con un nombre que no figura entre los de las pruebas. Ambos deben sobrevivir.
		"""
		nit_otra = "00000000000005"
		otra = self.fx.empresa("Z", nit_otra).name
		ajeno_otra_empresa = servicio.ingestar_dte_compra(otra, construir_ccf(70, receptor_nit=nit_otra))
		ajeno_nombre_distinto = servicio.ingestar_dte_compra(
			self.empresa.name, construir_ccf(9, receptor_nit=NIT_EMPRESA_C)
		)
		propio = servicio.ingestar_dte_compra(self.empresa.name, construir_ccf(1, receptor_nit=NIT_EMPRESA_C))
		frappe.db.commit()
		try:
			for r in (ajeno_otra_empresa, ajeno_nombre_distinto, propio):
				self.assertTrue(frappe.db.exists(DOCTYPE, r["name"]))  # los tres existen antes de limpiar
			self._limpiar()
			frappe.db.commit()
			self.assertFalse(frappe.db.exists(DOCTYPE, propio["name"]), "debía borrar el de la prueba")
			for r in (ajeno_otra_empresa, ajeno_nombre_distinto):
				self.assertTrue(frappe.db.exists(DOCTYPE, r["name"]), f"borró un registro ajeno: {r['name']}")
				self.assertEqual(frappe.db.count("KontaFlow DTE Compra Item", {"parent": r["name"]}), 2)
				self.assertEqual(frappe.db.count("KontaFlow DTE Compra Tributo", {"parent": r["name"]}), 1)
			# Ni las filas hijas del registro que sí se borró deben quedar huérfanas
			self.assertEqual(frappe.db.count("KontaFlow DTE Compra Item", {"parent": propio["name"]}), 0)

			# Sin indicar nombres, la limpieza borra todo lo de la empresa de prueba, pero solo de ella
			borrar_dte([self.empresa.name])
			frappe.db.commit()
			self.assertFalse(frappe.db.exists(DOCTYPE, ajeno_nombre_distinto["name"]))
			self.assertTrue(
				frappe.db.exists(DOCTYPE, ajeno_otra_empresa["name"]), "borró un registro de otra empresa"
			)
			self.assertEqual(
				frappe.db.count("KontaFlow DTE Compra Item", {"parent": ajeno_otra_empresa["name"]}), 2
			)
		finally:
			# Nombres explícitos: ni siquiera esta limpieza final puede llevarse nada ajeno.
			# Las empresas las retira la limpieza de clase, porque las creó este fixture.
			borrar_dte([otra], [ajeno_otra_empresa["name"]])
			borrar_dte([self.empresa.name], [ajeno_nombre_distinto["name"]])
			frappe.db.commit()

	def _lanzar(self, textos: list[str]) -> list[dict]:
		"""Lanza un proceso por texto, los sincroniza y devuelve el resultado de cada uno."""
		sites_path = os.path.abspath(frappe.local.sites_path)
		inicio = time.time() + ESPERA_ARRANQUE
		with tempfile.TemporaryDirectory() as carpeta:
			procesos = []
			for i, texto in enumerate(textos):
				archivo = os.path.join(carpeta, f"dte_{i}.json")
				with open(archivo, "w", encoding="utf-8", newline="") as f:
					f.write(texto)
				procesos.append(
					subprocess.Popen(
						[
							sys.executable,
							"-m",
							"kontaflow_sv.tests.trabajador_concurrente",
							frappe.local.site,
							sites_path,
							self.empresa.name,
							archivo,
							str(inicio),
						],
						cwd=sites_path,
						stdout=subprocess.PIPE,
						stderr=subprocess.PIPE,
						text=True,
					)
				)
			resultados = []
			for proceso in procesos:
				salida, errores = proceso.communicate(timeout=180)
				lineas = [x for x in salida.splitlines() if x.startswith("RESULTADO ")]
				self.assertTrue(
					lineas,
					f"El proceso no devolvió resultado.\nstdout: {salida[-500:]}\nstderr: {errores[-1500:]}",
				)
				resultados.append(json.loads(lineas[-1][len("RESULTADO ") :]))
		# Los procesos confirmaron en otras conexiones: se abre una instantánea nueva para verlo
		frappe.db.rollback()
		return resultados

	def test_reimportacion_identica_simultanea_devuelve_el_mismo_borrador(self):
		"""Varias solicitudes idénticas a la vez: un solo registro y todas reciben el mismo borrador."""
		colisiones = 0
		for ronda in range(1, 4):
			self._limpiar()
			frappe.db.commit()
			texto = construir_ccf(ronda, receptor_nit=NIT_EMPRESA_C)
			resultados = self._lanzar([texto] * PROCESOS)

			self.assertEqual(
				Counter(r["estado"] for r in resultados),
				Counter({"creado": 1, "existente": PROCESOS - 1}),
				resultados,
			)
			nombre = f"{self.empresa.abbr}-{codigo(ronda)}"
			self.assertEqual(frappe.db.count(DOCTYPE, {"company": self.empresa.name}), 1)
			self.assertEqual(frappe.db.count(DOCTYPE, {"name": nombre}), 1)
			self.assertEqual(frappe.db.count("KontaFlow DTE Compra Item", {"parent": nombre}), 2)
			self.assertEqual(frappe.db.count("KontaFlow DTE Compra Tributo", {"parent": nombre}), 1)
			self.assertEqual(frappe.db.get_value(DOCTYPE, nombre, "dte_original"), texto)
			colisiones += sum(1 for r in resultados if r["llamadas_existente"] >= 2)
			if colisiones:
				break

		if not colisiones:
			raise unittest.SkipTest(
				"Las invariantes se cumplieron, pero en 3 rondas ninguna solicitud llegó a chocar con la clave primaria."
			)

	def test_mismo_codigo_con_contenido_distinto_simultaneo_deja_un_solo_ganador(self):
		x = construir_ccf(1, receptor_nit=NIT_EMPRESA_C)
		y = construir_ccf(
			1, receptor_nit=NIT_EMPRESA_C, **{"cuerpoDocumento.0.descripcion": "Otra descripción"}
		)
		self.assertNotEqual(x, y)
		resultados = self._lanzar([x, x, x, y, y, y])

		self.assertEqual(frappe.db.count(DOCTYPE, {"company": self.empresa.name}), 1)
		guardado = frappe.db.get_value(DOCTYPE, f"{self.empresa.abbr}-{codigo(1)}", "dte_original")
		self.assertIn(guardado, (x, y))  # el original ganador queda intacto, nunca mezclado
		contenidos = [x, x, x, y, y, y]
		for texto, r in zip(contenidos, resultados, strict=True):
			if texto == guardado:
				self.assertIn(r["estado"], ("creado", "existente"), r)
			else:
				self.assertEqual(r["estado"], "conflicto", r)
		self.assertEqual(
			Counter(r["estado"] for r in resultados),
			Counter({"creado": 1, "existente": 2, "conflicto": 3}),
			resultados,
		)

	def test_mismo_codigo_en_distintas_versiones_simultaneo_deja_un_solo_ganador(self):
		"""Un mismo documento no puede existir en v3 y en v4: gana uno, el resto es conflicto o existente."""
		v3 = construir_ccf(1, receptor_nit=NIT_EMPRESA_C)
		v4 = construir_ccf(1, receptor_nit=NIT_EMPRESA_C, version_dte=4)
		self.assertNotEqual(v3, v4)
		contenidos = [v3, v3, v3, v4, v4, v4]
		resultados = self._lanzar(contenidos)

		nombre = f"{self.empresa.abbr}-{codigo(1)}"
		self.assertEqual(frappe.db.count(DOCTYPE, {"company": self.empresa.name}), 1)
		guardado = frappe.db.get_value(DOCTYPE, nombre, "dte_original")
		self.assertIn(guardado, (v3, v4))  # el ganador queda intacto, nunca mezclado
		self.assertEqual(frappe.db.get_value(DOCTYPE, nombre, "version"), 3 if guardado == v3 else 4)
		for texto, r in zip(contenidos, resultados, strict=True):
			if texto == guardado:
				self.assertIn(r["estado"], ("creado", "existente"), r)
			else:
				self.assertEqual(r["estado"], "conflicto", r)
		self.assertEqual(
			Counter(r["estado"] for r in resultados),
			Counter({"creado": 1, "existente": 2, "conflicto": 3}),
			resultados,
		)
