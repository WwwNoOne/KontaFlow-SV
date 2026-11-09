"""Proceso de apoyo de ``test_ingesta_concurrente``: ingesta un DTE con su propia conexión y transacción.

Uso: ``python -m kontaflow_sv.tests.trabajador_concurrente <sitio> <sites_path> <empresa> <archivo> <inicio>``.
Espera hasta la hora ``inicio`` (epoch) para que todos los procesos arranquen a la vez, e imprime una
línea ``RESULTADO {json}``. No es una prueba: lo invoca la prueba mediante ``subprocess``.
"""

import json
import sys
import time

import frappe


def main():
	sitio, sites_path, empresa, archivo, inicio = sys.argv[1:6]
	with open(archivo, encoding="utf-8", newline="") as f:
		texto = f.read()

	frappe.init(site=sitio, sites_path=sites_path)
	frappe.connect()
	frappe.set_user("Administrator")

	from kontaflow_sv.ingesta import servicio

	llamadas = []
	real = servicio._existente

	def contado(nombre, huella, **kw):
		llamadas.append(nombre)
		return real(nombre, huella, **kw)

	servicio._existente = contado

	# Cada lectura del registro: (con conexión propia, encontró algo)
	lecturas = []
	leer_real = servicio._leer_registro

	def leer_contado(nombre, conexion_propia):
		registro = leer_real(nombre, conexion_propia)
		lecturas.append([conexion_propia, bool(registro)])
		return registro

	servicio._leer_registro = leer_contado

	while time.time() < float(inicio):
		time.sleep(0.0005)

	try:
		r = servicio.ingestar_dte_compra(empresa, texto)
		frappe.db.commit()
		salida = {"estado": r["resultado"]}
	except frappe.DuplicateEntryError:
		frappe.db.rollback()
		salida = {"estado": "conflicto"}
	except Exception as e:
		frappe.db.rollback()
		salida = {"estado": "error", "tipo": type(e).__name__, "mensaje": str(e)[:300]}
	finally:
		frappe.destroy()

	# 2 o más llamadas a _existente = la comprobación previa no vio el registro y la inserción chocó
	salida["llamadas_existente"] = len(llamadas)
	salida["lecturas"] = lecturas
	print("RESULTADO " + json.dumps(salida))


if __name__ == "__main__":
	main()
