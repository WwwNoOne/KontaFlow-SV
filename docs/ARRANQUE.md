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
| KF-02 | Claude Code | Hecha | Primera ingesta manual de un DTE de compra en JSON de un solo tipo y versión verificados. Con datos ficticios, verificar importes exactos, rechazo de entradas inválidas, aislamiento entre empresas y reintento idempotente. El flujo conserva el registro como borrador sin generar asientos. |
| KF-02-R | Codex | Hecha | Revisar el esquema, la aritmética decimal, el manejo de documentos repetidos y el alcance por empresa. Verificar que el flujo conserve el DTE recibido y deje el registro en borrador. |
| KF-03 | Claude Code | Lista para iniciar | Ingesta manual de un CCF v4 en JSON como borrador, sin asientos. El parser se elige por `identificacion.version` (3 o 4; cualquier otra se rechaza con mensaje claro) y v3 se conserva intacto para documentos históricos. Contrastar con el esquema oficial `fe-ccf-v4.json` del ZIP de Hacienda con la misma prueba diferencial que v3. Compartir las constantes de CAT-015 entre parsers. Definir y probar qué pasa si el mismo `codigoGeneracion` llega en otra versión (la identidad sigue siendo por (empresa, `codigoGeneracion`)). Verificar con datos ficticios importes exactos, rechazo de entradas inválidas, aislamiento entre empresas y reintento idempotente. |
| KF-03-R | Codex | Pendiente de KF-03 | Revisar el selector de versión, la regresión de v3, la aritmética decimal, el cotejo con el esquema v4 y el manejo de un documento repetido entre versiones. |

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

## KF-02 · Decisiones tomadas (9 de noviembre de 2026)

- **Tipo y versión:** DTE `03` (Comprobante de Crédito Fiscal) versión `3`. Es el tipo de 71 de los 82 documentos de la muestra local (70 directos y 1 envuelto en `dteJson`) `../muestra/` (fuera del repo, datos reales: no se commitean ni se citan). Las notas `05`/`06` y el tipo `14` quedan para otra tarea.
- **Identidad del DTE:** única por `(empresa, codigoGeneracion)`. El sello de recepción se guarda como dato opcional y **no** forma parte de la clave. En la muestra `codigoGeneracion` está en los 82 documentos, y el sello falta en 2 y llega bajo 8 nombres distintos.
- **Empresa:** la persona usuaria elige la Company al cargar y el parser rechaza el documento si el NIT/NRC del receptor no coincide con el de esa empresa.
- **Alcance:** termina en borrador, sin asientos contables.

## Entrega KF-02 · En revisión

- **Base:** `3a44418`, rama `feature_claude`. Sin commits nuevos; los cambios están en el árbol de trabajo.
- **Modificados:** `docs/ARRANQUE.md`, `docs/DESARROLLO_LOCAL.md`.
- **Nuevos:**
  - `kontaflow_sv/api.py`
  - `kontaflow_sv/ingesta/__init__.py`, `ingesta/dte_compra.py` (parser, sin Frappe), `ingesta/servicio.py` (ingesta)
  - `kontaflow_sv/kontaflow_sv/doctype/__init__.py`
  - `doctype/kontaflow_dte_compra/` (`__init__.py`, `.json`, `.py`), `doctype/kontaflow_dte_compra_item/` (ídem), `doctype/kontaflow_dte_compra_tributo/` (ídem)
  - `kontaflow_sv/tests/utilidades.py`, `tests/test_dte_compra_parser.py`, `tests/test_ingesta_dte_compra.py`
- **Qué hace:** `kontaflow_sv.api.ingestar_dte_compra(company, dte_json)` (POST) valida un CCF v3 y lo registra como `KontaFlow DTE Compra` en estado Borrador, con ítems y tributos. No crea asientos, facturas ni pagos (hay una prueba que compara los conteos de `GL Entry`, `Journal Entry`, `Purchase Invoice` y `Payment Entry`).
- **Identidad:** el nombre del registro es `<abreviatura de la empresa>-<codigoGeneracion>`. La abreviatura de `Company` es única, así que la unicidad por (empresa, codigoGeneracion) queda en la clave primaria de la base de datos. Un reintento idéntico devuelve el registro existente; el mismo código con contenido distinto se rechaza (`DuplicateEntryError`) sin tocar el original.
- **DTE recibido:** se guarda el JSON tal como llegó (`dte_original`) y su SHA-256. El controlador impide crear a mano y modificar un registro ingestado.
- **Importes:** se leen como `Decimal` (`parse_float=Decimal`), nunca pasan por `float` en el parser. Se rechaza lo que tenga más de 2 decimales (resumen) o 8 (ítems) y lo que no sobreviva exactamente a la ida y vuelta por `float`, porque Frappe guarda a través de `float`.
- **Reglas:** se rechazan los cuadres que se cumplen en los 71 CCF reales (totales gravada, exenta y no sujeta frente a ítems; monto total frente a subtotal más tributos, con tolerancia 0.01). El IVA al 13 % fuera de tolerancia es **advertencia**, porque 1 de los 71 reales no lo cumple. Las fórmulas de `totalPagar` y `subTotal` no se imponen (64/71 y 56/71 las cumplen).
- **Empresa:** el NIT del receptor (solo dígitos) debe coincidir con el `tax_id` de la empresa elegida. Quien no puede leer la empresa recibe el mismo error que si no existiera, y antes de que se lea el contenido.
- **Verificación:** `bench --site kf.localhost migrate` y `run-tests --app kontaflow_sv`: 23 unitarias y 25 de integración OK. `ruff check`: OK. Contra la muestra real, solo en memoria y sin guardar nada: 70 de 71 CCF aceptados; el rechazado es el envuelto en `dteJson`.
- **Pruebas de las pruebas:** se rompió a propósito cada regla clave (cuadres, tipo, versión, NIT, clave sin empresa, permiso, hash, decimales, `parse_float`) y se confirmó que alguna prueba falla. Así se detectaron y corrigieron 3 pruebas que no comprobaban nada y una filtración real: una empresa inexistente producía un mensaje distinto al de una empresa sin acceso.

**Límites y decisiones pendientes (para Codex y para la persona responsable):**
- **No se consultó el esquema oficial del DTE de Hacienda.** Las reglas de campos y formatos se contrastaron con 71 documentos reales, no con el JSON Schema oficial. La decisión pendiente «confirmar tipo y versión con el esquema oficial» sigue abierta.
- La concurrencia está **simulada** (se fuerza que la comprobación previa no vea el registro y se prueba la ruta de `DuplicateEntryError`). No hay prueba con hilos o procesos reales; la garantía descansa en la clave primaria.
- No se valida el NRC del receptor: `Company` de ERPNext no trae NRC estándar.
- No se normalizan envoltorios (`dteJson`, respuestas de Hacienda en el nivel superior) ni las variantes del sello: solo se acepta el sello como texto bajo `selloRecibido`, `selloRecepcion` o `SelloRecepcion`. En la muestra, 60 de 70 documentos aceptados traen sello.
- Notas `05`/`06` (comprobar cuál es crédito y cuál débito) y tipo `14`: fuera de alcance.
- No hay interfaz de carga de archivo: solo la API y el servicio.
- Permisos del DocType: Accounts Manager (crear, escribir, borrar), Accounts User (crear, escribir) y System Manager (leer). Conviene revisarlos.
- Límites de tamaño: 2 MB por DTE y 2000 ítems.
- Los datos reales de `../muestra/` no se copiaron al repositorio ni se guardaron en la base de datos.

### Correcciones tras KF-02-R · En revisión

Base sin cambios: `3a44418`, rama `feature_claude`, sin commits nuevos.

**Hallazgos de Codex**
1. **Abonos no gravados:** `noGravado` (ítem) y `totalNoGravado` (resumen) admiten signo negativo; el resto de importes sigue rechazándolo. Pruebas: abono aceptado, negativos rechazados en 8 campos más, y el abono respeta límite y decimales.
2. **Tributos informativos:** `C5`, `C6` y `C7` se conservan en el registro y se excluyen del cuadre del monto total; los demás tributos (`D1`, `C8`, `59`…) sí se suman. **No pude contrastar el Anexo II por mi cuenta**: implementé lo que Codex reprodujo, y la lista `TRIBUTOS_INFORMATIVOS` queda marcada como pendiente de confirmar con el catálogo oficial.
3. **BOM y hash:** `dte_original` guarda el contenido exactamente como llegó (BOM incluido) y el SHA-256 se calcula sobre ese texto: `sha256(dte_original.encode("utf-8")) == dte_sha256`. Probado con BOM, CRLF, salto final, espacios y tildes tras ir y volver de la base de datos. Consecuencia, a propósito: el mismo JSON con y sin BOM es contenido distinto y se rechaza como conflicto, no se sobrescribe.

**Permisos y límites (propuesta de Codex, adoptada)**
- Accounts Manager y Accounts User: crear y consultar. System Manager: solo consultar. Todos limitados a las empresas autorizadas (User Permission). Sin edición ni borrado. Además se quitaron `email` y `share`: compartir un DTE abriría el acceso fuera de la empresa autorizada. Probado con usuarios de cada rol, incluida una mutación que devuelve `write`, `delete` y `share`.
- Límites provisionales de la API: 2 MB y 2000 ítems, con mensaje claro; son de KontaFlow, no del esquema fiscal. Probados.

**Dos solicitudes simultáneas reales: defecto encontrado y corregido.** Con procesos independientes, 5 de 6 solicitudes idénticas fallaban con `QueryDeadlockError` (error 1020 de MariaDB, aislamiento por instantánea) en lugar de devolver el borrador existente; la prueba simulada lo ocultaba. Ahora el servicio captura ese error y el duplicado 1062, y relee: en el modo con instantánea el motor reinicia la transacción y la relectura ve la fila; en el modo anterior hace falta una conexión nueva. Ambos modos se probaron cambiando `innodb_snapshot_isolation` y con mutaciones que fallan en cada uno. Resultado: exactamente un `creado` y el resto `existente`, un solo registro con sus ítems; con contenido distinto, un solo ganador intacto y el resto `conflicto`; repetido 3 veces sin fallos.
- **Regla derivada:** el error 1020 revierte la transacción completa. `ingestar_dte_compra` debe ir en su propia transacción (un DTE por solicitud); un proceso por lotes debe confirmar tras cada DTE. Está en el docstring.

**Archivos**
- Modificados: `kontaflow_sv/ingesta/dte_compra.py`, `kontaflow_sv/ingesta/servicio.py`, `kontaflow_sv/kontaflow_sv/doctype/kontaflow_dte_compra/kontaflow_dte_compra.json` (permisos), `kontaflow_sv/tests/test_dte_compra_parser.py`, `kontaflow_sv/tests/test_ingesta_dte_compra.py`, `docs/DESARROLLO_LOCAL.md`, `docs/ARRANQUE.md`.
- Nuevos: `kontaflow_sv/tests/test_ingesta_concurrente.py`, `kontaflow_sv/tests/trabajador_concurrente.py`.

**Verificación:** `bench --site kf.localhost migrate` (permisos) y `run-tests --app kontaflow_sv`: 29 unitarias y 39 de integración OK; `ruff check` OK; sitio limpio al terminar (0 empresas, 0 DTE, 0 asientos). Contra la muestra real, en memoria: 70 de 71 CCF aceptados, igual que antes.

**Sigue abierto**
- **Cotejo con el JSON Schema de CCF v3:** desbloqueado, ver «Cotejo con el esquema y el catálogo» más abajo.
- Notas `05`/`06`, tipo `14`, NRC del receptor, envoltorios y variantes del sello: sin cambios respecto a la entrega anterior.

### Cotejo con el esquema y el catálogo de Hacienda · En revisión

Archivos recibidos, guardados **fuera del repositorio** en `KF_Workspace/esquemas/` (no se modificaron): `JSON-Schemas-Hacienda.zip` (sha256 `8587a7d6…`), `fe-ccf-v3-copia-publica.json` (`b8c8e277…`) y `Catalogos-Facturacion-Electronica-Hacienda.xlsx` (`e86d7edc…`). El ZIP se extrajo en un directorio temporal, ya borrado.

**Procedencia y límites del cotejo**
- El ZIP oficial trae `fe-ccf-v4`, `fe-nc-v4`, `fe-nd-v4`, `fe-nr-v4`, `fe-fex-v3`, v2 y v1, **pero no `fe-ccf-v3`**. El cotejo usa la **copia pública** de v3, que declara tipo `03` y versión `3` como constantes. **Falta confirmar esa copia contra un ZIP histórico de Hacienda.**
- Los 71 CCF reales traen todos `version: 3` (fechas de septiembre de 2026), mientras que el ZIP vigente solo publica v4. No sé cuándo se retira v3; conviene decidir cuándo se añade v4. En el esquema v4 se ven, entre otros cambios, la ausencia de `extension`, ninguna regla condicional y descripciones de tributo de hasta 300 caracteres.
- El Manual Funcional de Hacienda (sección 3) se recibió después y está leído: ver «Limpieza de las pruebas y manual» más abajo.

**Tributos informativos (hallazgo 2 de KF-02-R, resuelto)**
- CAT-015 tiene tres secciones: (1) tributos de ítems reflejados en el **resumen** (20, C3, 59, 71, D1, C8, D5, D4), que se suman; (2) tributos del **cuerpo** (A8, 57, 90, D4, D5, A6); (3) impuestos ad-valorem **de uso informativo reflejados en el resumen**: **35 códigos**, no solo C5, C6 y C7.
- **Todos los 35 aplican a v3:** la enumeración de códigos válidos de `tributos` por ítem en el esquema v3 es exactamente la sección 1 más la sección 3 (43 códigos, sin sobrantes ni faltantes, comprobado con conjuntos).
- El parser usa ahora los 35 (`TRIBUTOS_INFORMATIVOS`) y los 8 de la sección 1 (`TRIBUTOS_RESUMEN`). Un código fuera de ambas secciones (por ejemplo los de la sección 2, o uno inexistente) se suma al total y deja una **advertencia**. Probado: los 35 no se suman, los 7 de la sección 1 distintos del 20 sí, el 19 (caso reproducido por Codex) no. Las pruebas llevan una copia independiente del catálogo para detectar cambios accidentales.
- **La regla aritmética (no sumar la sección 3 al monto total) se apoya en el rótulo «de uso informativo» del catálogo y en la reproducción de Codex.** Ningún CCF real de la muestra lleva códigos de la sección 3 (solo 20, C8 y D1), así que no hay un documento real que la confirme.

**Cotejo de los 71 CCF reales contra el esquema v3**
- Solo **3 de 71 son válidos** al pie de la letra. Los incumplimientos, por documento: `municipio` fuera de los patrones por departamento en 65 a 67 (los códigos reales no los admite la versión del catálogo de municipios que usa el esquema), `tipoContingencia` en 2, `apendice[].valor` demasiado largo en 2 y `receptor.correo` nulo en 1. El parser no valida esos campos.
- Al principio aparecían decenas de fallos de `multipleOf`. Eran un **artefacto de la coma flotante**: con `Decimal` en datos y esquema desaparecen todos.

**Qué corrigió el cotejo en el parser**
- Los nombres se limitaban a 140 caracteres y el esquema admite **200 (emisor) y 250 (receptor)**: se rechazaban documentos legítimos. Corregido, con las columnas de la base de datos ampliadas a 200 y 250 (`length` del DocType) y una prueba que guarda y relee 200 y 250 caracteres completos.
- La descripción de un tributo admite 150 caracteres y el campo era de 140. Corregido (parser y columna).
- `montoTotalOperacion` debe ser mayor que cero (`exclusiveMinimum 0`); ninguno de los 71 reales lo incumple.
- El **límite de 2000 ítems es del esquema** (`maxItems`), no solo de KontaFlow; el de 2 MB sigue siendo provisional de KontaFlow. Se probaron ambos lados del límite: 2000 se acepta y 2001 se rechaza.
- Confirmado por el esquema: `noGravado` y `totalNoGravado` admiten negativos (`exclusiveMinimum -1e11`) y el resto de importes tiene `minimum 0`.

**Cómo se verifica.** `test_esquema_ccf_v3.py` compara esquema y parser caso por caso: 11 documentos válidos que ambos aceptan, 19 inválidos que ambos rechazan, el límite de ítems y las diferencias intencionales. El fixture base de las pruebas es ahora un CCF v3 válido según el esquema.

**Diferencias que se mantienen a propósito** (el parser es más tolerante que el esquema y está probado): `codigoGeneracion` en minúsculas (se normaliza a mayúsculas) y NIT con guiones (se normaliza a dígitos).

**Reglas del esquema que el parser todavía no impone:** con `ventaGravada` en 0 el ítem debe tener `tributos` nulo; con `tipoItem` 4 la unidad de medida es 99 y el único tributo válido es `"20"`; las listas de campos obligatorios completas; `tipoItem` en 1 a 4 y `uniMedida` de 1 a 99; el patrón del NRC (`^[0-9]{1,8}$`) y el formato de los demás datos de emisor y receptor. El parser guarda lo recibido y no repite toda la validación de Hacienda.

**Verificación:** 39 pruebas unitarias y 41 de integración OK, con y sin el esquema (sin él se omiten 5); `ruff check` OK; muestra real en memoria: 70 de 71 CCF aceptados, igual que antes. Se rompió a propósito cada regla nueva y alguna prueba falla en cada caso; así se detectó una prueba que no cubría el límite de 2000 ítems y se rehízo.

**Archivos:** modificados `kontaflow_sv/ingesta/dte_compra.py`, `kontaflow_sv/kontaflow_sv/doctype/kontaflow_dte_compra/kontaflow_dte_compra.json` y `.../kontaflow_dte_compra_tributo/kontaflow_dte_compra_tributo.json` (largos), `kontaflow_sv/tests/test_dte_compra_parser.py`, `test_ingesta_dte_compra.py`, `utilidades.py` (fixture válido según el esquema), `docs/DESARROLLO_LOCAL.md`, `docs/ARRANQUE.md`. Nuevo: `kontaflow_sv/tests/test_esquema_ccf_v3.py`.

**Sigue abierto**
- Confirmar la copia pública de v3 contra un ZIP histórico de Hacienda.
- Decidir cuándo se añade CCF v4 (propuesta de Codex: tarea propia, parser elegido por `identificacion.version`).

### Limpieza de las pruebas y manual · En revisión

Base sin cambios: `3a44418`, sin commits nuevos. Coordinación entre sesiones en [Cordinacion.md](../Cordinacion.md).

- **Manual Funcional (sección 3), verificado de forma independiente:** los tributos informativos no tienen efecto en los valores del documento (ejemplo: $6.40 de C5 conservados, $226.00 a pagar). Comparé por código su lista con `TRIBUTOS_INFORMATIVOS`: **35 códigos idénticos**. La regla aritmética ya no depende solo del rótulo del catálogo.
- **Bloqueo de KF-02-R (las pruebas borraban datos ajenos), reproducido y corregido.** Con un DTE señuelo confirmado en otra empresa, la prueba de concurrencia lo destruía junto con sus ítems y tributos; además `test_ingesta_dte_compra.py` también borraba todos los DTE en su `setUp`. Ahora `kontaflow_sv/tests/limpieza.py` (`borrar_dte(empresas, nombres=None)`) exige alcance y solo toca los DTE de las empresas de prueba, y en concurrencia solo los nombres `KFC-<codigoGeneracion>` de los códigos 1 a 3. Los conteos de las pruebas también se acotaron a sus empresas: asumían un sitio vacío y fallaban 19 con un solo DTE ajeno presente.
- **Regresión:** `test_la_limpieza_no_toca_registros_ajenos` y `test_limpieza.py`. Con el señuelo real en el sitio, la suite completa lo deja intacto. Mutaciones (sin filtro de empresa, sin filtro de nombres): ambas se detectan. La primera versión de la prueba no detectaba la ausencia del filtro de empresa y se amplió.
- **Verificación:** 40 pruebas unitarias y 42 de integración OK con el esquema v3 indicado (sin él se omiten 5); `ruff check` OK; sitio limpio al terminar (0 empresas, 0 DTE, 0 ítems, 0 tributos).
- **Archivos nuevos:** `Cordinacion.md` (raíz), `kontaflow_sv/tests/limpieza.py`, `kontaflow_sv/tests/test_limpieza.py`. **Modificados:** `kontaflow_sv/tests/test_ingesta_concurrente.py`, `kontaflow_sv/tests/test_ingesta_dte_compra.py`, `AGENTS.md`, `docs/DESARROLLO_LOCAL.md`, `docs/ARRANQUE.md`.

### Fixtures con nombre propio por ejecución · En revisión

Base sin cambios: `3a44418`, sin commits nuevos. Detalle y cómo repetirlo en [Cordinacion.md](../Cordinacion.md).

- **Hallazgo de Codex (KF-02-R):** las pruebas reutilizaban una `Company` preexistente por nombre fijo, le cambiaban el NIT y la borraban con `force`. Corregido con `kontaflow_sv/tests/fixtures.py`: nombre y abreviatura con token propio de cada ejecución, aborto (`FixtureYaExiste`) si algo ya existe y limpieza de **solo lo que el fixture creó**.
- **Regresión:** `test_fixtures_seguros.py` (6 pruebas): una compañía preexistente con su DTE y el mismo nombre queda intacta; también por abreviatura, por usuario y con nombre distinto. Verificado además extremo a extremo con cinco empresas preexistentes con los nombres fijos antiguos: las cinco intactas tras la suite completa.
- **Defecto propio corregido:** si el fixture creaba el `Warehouse Type` «Transit», la limpieza fallaba (ERPNext no deja borrarlo) **antes del `commit`** y dejaba empresas y un DTE confirmados. Ahora no se intenta borrar y se confirma en un `finally`.
- **Verificación:** 40 pruebas unitarias y 49 de integración OK con el esquema v3 indicado; `ruff check` OK; sitio limpio al terminar. Mutaciones sobre la fábrica y la limpieza: todas detectadas.
- **Límite:** «Transit» queda en el sitio si faltaba (dato obligatorio de ERPNext).
- **Archivos nuevos:** `kontaflow_sv/tests/fixtures.py`, `kontaflow_sv/tests/test_fixtures_seguros.py`. **Modificados:** `kontaflow_sv/tests/test_ingesta_dte_compra.py`, `kontaflow_sv/tests/test_ingesta_concurrente.py`, `Cordinacion.md`, `docs/DESARROLLO_LOCAL.md`, `docs/ARRANQUE.md`.

## Cierre de KF-02-R

Codex aprobó la ronda 6 sobre `feature_claude`, base `3a44418`. Los fixtures usan identificadores por ejecución y se detienen ante una colisión con registros preexistentes. La limpieza se limita a los datos de la ejecución.

En `kf.localhost`, `bench --site kf.localhost run-tests --app kontaflow_sv` con `KF_ESQUEMA_CCF_V3` apuntando a la copia pública pasó **40 pruebas unitarias y 49 de integración**, incluidas concurrencia real y conservación de una empresa preexistente con su DTE. Ruff pasó. Los conteos de empresas, DTE, ítems, tributos y asientos quedaron en cero antes y después.

El cotejo de v3 usó la copia pública identificada en la entrega. La corroboración contra un ZIP histórico oficial sigue pendiente. KF-03 queda habilitada después del commit de KF-02 ya autorizado para Claude.

## Mensajes para las sesiones

**Para Claude Code, al abrir KontaFlow-SV**

> Lee CLAUDE.md y docs/ARRANQUE.md. Toma KF-01, registra las rutas que vas a tocar y prepara el entorno local y la app base según sus criterios de cierre. Deja el cambio estable para Codex con el estado, el HEAD base, la lista de archivos y las verificaciones realizadas.

**Para Codex, cuando KF-01 figure En revisión**

> Lee AGENTS.md y docs/ARRANQUE.md. Haz la revisión KF-01-R de la entrega de Claude, incluidos los archivos nuevos. Contrasta el resultado con los criterios de KF-01 y reporta hallazgos por severidad, pruebas ejecutadas y bloqueos. Mantén esta primera revisión en modo lectura.
