# Contexto actual de KontaFlow SV

Actualizado el 9 de noviembre de 2026. Punto de entrada para una sesión nueva o para retomar después de una compactación.

## Dónde continuar

- Trabaja en el worktree activo de `feature_claude`, identificado por `git worktree list`. Su historial contiene KF-01 a KF-03 ya commiteadas (`3a44418`, `1125551` y `1d798c7`) y, encima, el commit de esta documentación; **no se ha hecho push a `origin`**. Una rama o un worktree creado desde `main` todavía parte de `10032fe` y no tiene esos commits: si tu sesión parte de ahí, ejecuta `git merge --ff-only feature_claude` (es un avance rápido, porque `10032fe` es ancestro) antes de empezar. El árbol de trabajo debe estar limpio al comenzar.
- La siguiente tarea disponible es **KF-04.1**, consulta de borradores por empresa y mes. Los pasos y criterios están en el [tablero](ARRANQUE.md). Claude implementa cada entrega y Codex revisa la entrega estable.
- Abre [Cordinacion.md](Cordinacion.md) para mensajes y decisiones. La [visión original](Project_Context.md) y el [historial de entregas](HISTORIAL_KF01_KF03.md) quedan como referencia. El tablero refleja el estado actual.

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
