"""Catálogos de Hacienda compartidos por los parsers de todas las versiones de DTE."""

# Catálogo CAT-015 de Hacienda (Catálogos de Facturación Electrónica). Los tributos del RESUMEN del DTE
# son de dos clases:
#  - Sección 1, "tributos aplicados por ítems reflejados en el resumen": se suman al monto total.
#  - Sección 3, "impuestos ad-valorem aplicados por ítem de uso informativo reflejados en el resumen":
#    se conservan en el registro pero NO se suman al monto total (el importe ya va en el precio).
# La sección 2 (A8, 57, 90, A6) son tributos del cuerpo del documento, no del resumen.
# El esquema JSON de CCF v3 acepta los códigos de las secciones 1 y 3 como tributos de un ítem
# (enumeración de 43 códigos = secciones 1 y 3 juntas), de modo que los 35 de la sección 3 aplican a v3.
TRIBUTOS_RESUMEN = frozenset({"20", "C3", "59", "71", "D1", "C8", "D5", "D4"})
TRIBUTOS_INFORMATIVOS = frozenset(
	{
		"C5", "C6", "C7", "19", "28", "31", "32", "33", "34", "35", "36", "37", "38", "39",
		"42", "43", "44", "50", "51", "52", "53", "54", "55", "58", "77", "78", "79", "85",
		"86", "91", "92", "A1", "A5", "A7", "A9",
	}
)  # fmt: skip
