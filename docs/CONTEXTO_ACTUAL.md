# Contexto actual de KontaFlow SV

Actualizado el 9 de noviembre de 2026. Punto de entrada para una sesión nueva o para retomar después de una compactación.

## Dónde continuar

- Desde el 2026-11-19 `main` de esta carpeta contiene la app completa hasta `7f165d2` (KF-04.3, el reporte en Desk, sobre KF-04.2 aprobada en `668659f`). El bench sigue cargando la app desde el worktree `vivid-delphinium` (rama `claudette/kf-04-2-docs-review`, mismo código que `main`); consulta el [tablero](ARRANQUE.md) antes de ejecutar pruebas. No ejecutes dos suites a la vez sobre `kf.localhost`: provocan errores de MariaDB (1020 y 1213). Verifica `git status` antes de editar.
- KF-04.3 está **hecha** (commit `7f165d2`): reporte «Vista previa del Libro de Compras» en Desk sobre `vista_previa.py`. Queda una condición abierta de KF-04-R: recorrer en Desk los pasos 1 a 5 de la [guía local](DESARROLLO_LOCAL.md) en un sitio con el asistente inicial completado. KF-05 quedó **hecha** (commit `5a674bf`, 2026-11-20) y la tarea en curso es **KF-06.1** (ingesta de notas de crédito y débito, encargos [`KF-06.md`](encargos/KF-06.md) y [`KF-06-2.md`](encargos/KF-06-2.md)): entregada en su iteración 2 en `vivid-delphinium`, sin commit y con la doble revisión pendiente (ver «Pendiente para la próxima sesión» en el [tablero](ARRANQUE.md)). KF-05 fue la exportación a Excel del Libro de Compras de CCF sobre la plantilla contable `docs/formato-libros-contables.xlsx` (mapeo de columnas, fórmula de TOTAL COMPRAS y matriz de signos en el [tablero](ARRANQUE.md); encargo en [`docs/encargos/KF-05.md`](encargos/KF-05.md)). KF-06 (notas de crédito y débito) y KF-07 (sujeto excluido) quedan planificadas. Con los roles vigentes, Claude planifica y delega a Codex (Sol 6.2) con `codex exec`, y dos revisores de solo lectura (Sonnet y Sol) auditan.
- Los encargos vigentes están en [`docs/encargos/`](encargos/); el estado y los dictámenes, en el [tablero](ARRANQUE.md). La [visión original](Project_Context.md) y el [historial de entregas](HISTORIAL_KF01_KF03.md) quedan como referencia. El tablero refleja el estado actual.

## Qué existe

- App Frappe `kontaflow_sv` sobre ERPNext. El punto de entrada es el POST `kontaflow_sv.api.ingestar_dte_compra(company, dte_json)`. El selector en `kontaflow_sv/ingesta/dte_compra.py` admite CCF tipo `03` v3 y v4, y el servicio registra `KontaFlow DTE Compra` en **Borrador**, con ítems, tributos y advertencias.
- La ingesta verifica el receptor contra la empresa, conserva el JSON original y su SHA-256, y respeta la identidad `(empresa, codigoGeneracion)`. Un reintento idéntico devuelve el mismo borrador. Si cambia el contenido o la versión, reporta conflicto y conserva el primero. El UID de correo queda como dato de procedencia cuando se integre esa fuente.
- Las funciones de consulta deben respetar el acceso a la empresa y al DocType. Accounts User y Accounts Manager pueden importar y consultar en su ámbito. System Manager puede consultar en su ámbito.
- La última revisión de KF-03 pasó **82 pruebas unitarias y 63 de integración**. El cotejo de v4 usó el ZIP oficial y datos ficticios. Los 71 CCF v3 de la muestra local dieron los mismos resultados que en KF-02: 70 aceptados y uno envuelto en `dteJson` rechazado. La copia pública del esquema v3 sigue pendiente de corroboración con un ZIP histórico oficial.

## Entorno y límites

- Sitio de desarrollo: `kf.localhost` en `~/frappe-kf/kf-bench`. Sigue la [guía local](DESARROLLO_LOCAL.md) para arrancar servicios y ejecutar la suite con `KF_ESQUEMA_CCF_V3` y `KF_ESQUEMAS_ZIP`.
- `KF_Workspace/esquemas/` contiene las referencias de Hacienda y la copia pública de v3. `KF_Workspace/muestra/` contiene documentos reales para verificación local. Usa datos ficticios en las pruebas versionadas.
- KF-04 se definió como vista previa de compras sobre borradores. Para la primera entrega se propone un período mensual por fecha de emisión. La exportación y la ampliación a otros DTE tienen su propio turno.
- Revisa `git status --short --branch --untracked-files=all` al retomar. Conserva el trabajo local ya aprobado y mantén los cambios de KF-04 separados. Los commits y pushes se rigen por [AGENTS.md](../AGENTS.md).
