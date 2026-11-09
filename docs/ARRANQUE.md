# Arranque de KontaFlow SV

## Estado inicial · 9 de noviembre de 2026

- KontaFlow-SV tiene un repositorio propio en `main`, con base `207c3ba`. Todavía queda por crear la app Frappe `kontaflow_sv`.
- El checkout vecino de ERPNext está en `develop` (`0d2bc1a939`). Su `pyproject.toml` declara Python `>=3.14` y Frappe `>=17.0.0-dev,<18.0.0`. La versión que se usará para KontaFlow queda por fijar como parte de KF-01.
- En el entorno inspeccionado, Python 3.14.9 y Node v26.13.0 estaban disponibles. `bench`, `docker`, `redis-server`, `mariadb` y `psql` no aparecían en el `PATH`. Falta verificar la ruta de instalación y levantar un sitio local.
- Oculus está en `main` (`bc5b3b7`). Para revisar la ingesta de compras, empieza en `../Oculus/src/backend/services/` por `email_service.py`, `dte_service.py` y `ocr_service.py`. El contexto reporta extracciones PDF vacías o inexactas y compras físicas que pueden faltar en el correo.

## Tablero

| ID | Responsable | Estado | Entrega y criterio de cierre |
| --- | --- | --- | --- |
| KF-01 | Claude Code | Hecha | Guía reproducible del entorno local y app base `kontaflow_sv`. Registrar versiones exactas, comandos y resultados. Verificar en un sitio desechable que ERPNext y la app aparecen instalados y que la prueba mínima de la app pasa. |
| KF-01-R | Codex | Hecha | Revisar el cambio completo, los archivos nuevos y la evidencia de instalación. Repetir las verificaciones posibles y registrar los hallazgos. |
| KF-02 | Claude Code | Lista para iniciar | Primera ingesta manual de un DTE de compra en JSON de un solo tipo y versión verificados. Con datos ficticios, verificar importes exactos, rechazo de entradas inválidas, aislamiento entre empresas y reintento idempotente. El flujo conserva el registro como borrador sin generar asientos. |
| KF-02-R | Codex | Pendiente de KF-02 | Revisar el esquema, la aritmética decimal, el manejo de documentos repetidos y el alcance por empresa. Verificar que el flujo conserve el DTE recibido y deje el registro en borrador. |

Usa los estados **Lista para iniciar**, **En curso**, **En revisión**, **Bloqueada** y **Hecha**. Las filas pendientes de otra tarea pasan a **Lista para iniciar** cuando se cumple la dependencia.

## KF-01 · Primer encargo

- [ ] Inventariar las herramientas disponibles y consultar los requisitos de las versiones candidatas en la documentación oficial. Comparar Bench local y contenedores según lo que pueda ejecutarse en el equipo. Registrar la ruta elegida y las versiones compatibles de Frappe, ERPNext, Python, Node y base de datos.
- [ ] Documentar la instalación en `docs/DESARROLLO_LOCAL.md`, incluidos los prerrequisitos, los comandos y la ubicación del sitio desechable. Mantener el entorno Bench, la base de datos y los archivos de sitio fuera del repositorio del producto.
- [ ] Crear la app base dentro de KontaFlow-SV, utilizando los mecanismos estándar de Frappe y preservando la documentación y el historial existentes. Mantener ERPNext como dependencia. Antes de usar un generador, comprobar dónde escribirá y qué archivos tocará.
- [ ] Instalar ambas apps en el sitio de prueba. Verificar la lista de apps y ejecutar una prueba mínima de la app. Registrar los comandos, resultados y pasos pendientes si el entorno impide completar la ejecución.
- [ ] Actualizar el estado y entregar el cambio a Codex con la referencia base y las rutas exactas. Los DocTypes de negocio y el parser corresponden a KF-02.

## Entrega KF-01 · En revisión

- **Base:** `10032fe`, rama `feature_claude`. Sin commits nuevos; los cambios están en el árbol de trabajo.
- **Modificado:** `docs/ARRANQUE.md`.
- **Nuevos:** `.gitignore`, `.editorconfig`, `.eslintrc`, `.pre-commit-config.yaml`, `license.txt`, `pyproject.toml`, `docs/DESARROLLO_LOCAL.md`, y la app `kontaflow_sv/` (`__init__.py`, `hooks.py`, `modules.txt`, `patches.txt`, `config/`, `patches/`, `public/`, `templates/`, `kontaflow_sv/` módulo, `tests/test_instalacion.py`).
- **Verificado** (detalle y versiones en `docs/DESARROLLO_LOCAL.md`): `bench list-apps` muestra frappe, erpnext y kontaflow_sv en `kf.localhost`; `bench run-tests --app kontaflow_sv` pasa 2 de 2.
- **Fuera del repo:** bench, MariaDB y Valkey en `~/frappe-kf/`. `apps/kontaflow_sv` del bench es un enlace simbólico a este repositorio.
- **Riesgos y decisiones pendientes:** MariaDB 13.0.2 frente al 11.8 documentado; Arch sin soporte oficial; falta `cronie`; licencia de la app sin decidir; no se probó `bench start` ni la interfaz web.

### Correcciones tras KF-01-R (ronda 2) · En revisión

Base sin cambios: `10032fe`, rama `feature_claude`, sin commits nuevos. Solo cambió `docs/DESARROLLO_LOCAL.md` (nuevo) y esta nota.

1. **Arranque diario:** carga `bench` en el `PATH`, borra `mysqld.pid` y `mysqld.sock` residuales, espera a que respondan MariaDB y Valkey. Verificado en terminal limpia (`env -i`) con los servicios apagados: `bench --version` → 5.31.1.
2. **Instalación reproducible:** `frappe-bench==5.31.1`; Frappe `09f83e0730b29f6e35218f97328eeabdf71a1a4a` y ERPNext `0d2bc1a9398eccf8003a851c01e2f2d99e594a01` fijados con `git checkout --detach` + `bench setup requirements` + `bench build`. El remoto de las apps es `upstream`, no `origin`. Ejecutado con exit 0.
3. **Enlace de la app:** la guía aparta el directorio existente (o enlace anterior) antes de `ln -s` y comprueba que `readlink -f` apunta al repo y que no hay enlace anidado. Reproducido con un directorio real preexistente: quedó apartado y el enlace correcto.
- **Repetido desde terminal limpia:** `list-apps` (frappe `09f83e0`, erpnext `0d2bc1a`, kontaflow_sv 0.0.1) y las 2 pruebas de instalación, OK.
- **No verificado:** `bench init`/`new-site` desde cero en un directorio nuevo; `bench start`.

### Correcciones tras KF-01-R (ronda 3) · En revisión

Base sin cambios: `10032fe`, rama `feature_claude`, sin commits nuevos. Solo cambió `docs/DESARROLLO_LOCAL.md` y esta nota.

1. **Revisiones fijadas antes de instalar:** `bench init --frappe-path` y `bench get-app` clonan desde repos locales con una rama `kf-pin` en cada SHA, así que nada se instala desde `develop`. `--no-backups` evita el error de `crontab`. Los bloques usan `set -euo pipefail`.
2. **Arranque diario seguro:** script `arrancar-servicios.sh` (fuera del repo) que reutiliza servicios activos, solo borra PID y socket si el PID no es un `mariadbd` vivo, y espera máximo 60 s. Probado: todo activo (mismos PID), PID obsoleto (arranca), fallo (errores y exit 1 a los 3 s).
3. **Enlace inválido detiene la instalación:** el bloque valida el repo antes de tocar el bench y el enlace antes de `install-app`; ambos con exit 1. Probado con repo inexistente, repo de otro proyecto y repo correcto.
- **Defecto propio hallado y corregido:** `ln -s` + `pip install -e` no registra la app en `sites/apps.txt`, y en un bench nuevo `install-app` fallaba con `App kontaflow_sv not in apps.txt`. Ahora se usa `bench get-app --soft-link`. Solo se detectó al probar en un bench nuevo.
- **Verificación en bench nuevo desde cero (revisiones fijadas):** frappe `09f83e0`, erpnext `0d2bc1a939`, kontaflow_sv 0.0.1; 2 de 2 pruebas OK. En el bench original, bloque 5 repetido y 2 de 2 OK.
- **No verificado:** `bench start` y la interfaz web.

## Cierre de KF-01-R

Codex aprobó la tercera ronda en `feature_claude`, base `10032fe`. Revisó el fijado de las revisiones antes de instalar, el arranque de servicios y la validación y el registro de la app antes de instalarla en el sitio.

En `kf.localhost`, `bench --site kf.localhost list-apps` confirmó Frappe `09f83e0`, ERPNext `0d2bc1a` y `kontaflow_sv` `0.0.1`. `bench --site kf.localhost run-tests --app kontaflow_sv` aprobó las dos pruebas de integración. La verificación del servidor web queda fuera de KF-01.

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
