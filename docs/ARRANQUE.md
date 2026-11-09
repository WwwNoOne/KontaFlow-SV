# Arranque de KontaFlow SV

## Estado inicial · 9 de noviembre de 2026

- KontaFlow-SV tiene un repositorio propio en `main`, con base `207c3ba`. Todavía queda por crear la app Frappe `kontaflow_sv`.
- El checkout vecino de ERPNext está en `develop` (`0d2bc1a939`). Su `pyproject.toml` declara Python `>=3.14` y Frappe `>=17.0.0-dev,<18.0.0`. La versión que se usará para KontaFlow queda por fijar como parte de KF-01.
- En el entorno inspeccionado, Python 3.14.9 y Node v26.13.0 estaban disponibles. `bench`, `docker`, `redis-server`, `mariadb` y `psql` no aparecían en el `PATH`. Falta verificar la ruta de instalación y levantar un sitio local.
- Oculus está en `main` (`bc5b3b7`). Para revisar la ingesta de compras, empieza en `../Oculus/src/backend/services/` por `email_service.py`, `dte_service.py` y `ocr_service.py`. El contexto reporta extracciones PDF vacías o inexactas y compras físicas que pueden faltar en el correo.

## Tablero

| ID | Responsable | Estado | Entrega y criterio de cierre |
| --- | --- | --- | --- |
| KF-01 | Claude Code | Lista para iniciar | Guía reproducible del entorno local y app base `kontaflow_sv`. Registrar versiones exactas, comandos y resultados. Verificar en un sitio desechable que ERPNext y la app aparecen instalados y que la prueba mínima de la app pasa. |
| KF-01-R | Codex | Pendiente de KF-01 | Revisar el cambio completo, los archivos nuevos y la evidencia de instalación. Repetir las verificaciones posibles y registrar los hallazgos. |
| KF-02 | Claude Code | Pendiente de KF-01 y su revisión | Primera ingesta manual de un DTE de compra en JSON de un solo tipo y versión verificados. Con datos ficticios, verificar importes exactos, rechazo de entradas inválidas, aislamiento entre empresas y reintento idempotente. El flujo conserva el registro como borrador sin generar asientos. |
| KF-02-R | Codex | Pendiente de KF-02 | Revisar el esquema, la aritmética decimal, el manejo de documentos repetidos y el alcance por empresa. Verificar que el flujo conserve el DTE recibido y deje el registro en borrador. |

Usa los estados **Lista para iniciar**, **En curso**, **En revisión**, **Bloqueada** y **Hecha**. Las filas pendientes de otra tarea pasan a **Lista para iniciar** cuando se cumple la dependencia.

## KF-01 · Primer encargo

- [ ] Inventariar las herramientas disponibles y consultar los requisitos de las versiones candidatas en la documentación oficial. Comparar Bench local y contenedores según lo que pueda ejecutarse en el equipo. Registrar la ruta elegida y las versiones compatibles de Frappe, ERPNext, Python, Node y base de datos.
- [ ] Documentar la instalación en `docs/DESARROLLO_LOCAL.md`, incluidos los prerrequisitos, los comandos y la ubicación del sitio desechable. Mantener el entorno Bench, la base de datos y los archivos de sitio fuera del repositorio del producto.
- [ ] Crear la app base dentro de KontaFlow-SV, utilizando los mecanismos estándar de Frappe y preservando la documentación y el historial existentes. Mantener ERPNext como dependencia. Antes de usar un generador, comprobar dónde escribirá y qué archivos tocará.
- [ ] Instalar ambas apps en el sitio de prueba. Verificar la lista de apps y ejecutar una prueba mínima de la app. Registrar los comandos, resultados y pasos pendientes si el entorno impide completar la ejecución.
- [ ] Actualizar el estado y entregar el cambio a Codex con la referencia base y las rutas exactas. Los DocTypes de negocio y el parser corresponden a KF-02.

## Decisiones pendientes antes de KF-02

- Confirmar el tipo y la versión del DTE inicial con el esquema oficial. El [contexto técnico](../Project_Context.md) contiene etiquetas de notas de ajuste que deben cotejarse antes de llevarlas al parser.
- Definir el alcance de la identidad del DTE para un sistema multiempresa. El contexto propone tanto unicidad por `codigoGeneracion` como una clave con `sello_recibido`. Validar la clave de negocio y la restricción de base de datos con casos de reingesta y concurrencia antes de crear el DocType.
- Validar importes con aritmética decimal y conservar la fuente. Los porcentajes, los modelos de IA, los costos y las estimaciones del contexto quedan como referencias por verificar en sus fases respectivas.
- El alcance inicial termina en borrador. La política de aprobación y contabilización automática se define aparte, porque el contexto describe tanto registro automático como aprobación del contador. Correo, PDF, OCR, IA y libros fiscales se programarán después del flujo JSON inicial.

## Mensajes para las sesiones

**Para Claude Code, al abrir KontaFlow-SV**

> Lee CLAUDE.md y docs/ARRANQUE.md. Toma KF-01, registra las rutas que vas a tocar y prepara el entorno local y la app base según sus criterios de cierre. Deja el cambio estable para Codex con el estado, el HEAD base, la lista de archivos y las verificaciones realizadas.

**Para Codex, cuando KF-01 figure En revisión**

> Lee AGENTS.md y docs/ARRANQUE.md. Haz la revisión KF-01-R de la entrega de Claude, incluidos los archivos nuevos. Contrasta el resultado con los criterios de KF-01 y reporta hallazgos por severidad, pruebas ejecutadas y bloqueos. Mantén esta primera revisión en modo lectura.
