# Tablero de KontaFlow SV

Lee primero el [contexto actual](CONTEXTO_ACTUAL.md). Los encargos al ejecutor están en [`docs/encargos/`](encargos/); el orquestador los delega con `codex exec` y registra aquí las entregas y los dictámenes de revisión. Las rondas de KF-01 a KF-03 están en el [historial](HISTORIAL_KF01_KF03.md).

## Ubicación del código (actualizado el 2026-11-19)

- `main` (esta carpeta) avanzó por fast-forward hasta `7f165d2` e incluye la app `kontaflow_sv` completa (KF-01 a KF-04.3). Antes solo tenía la documentación inicial (`10032fe`). No se ha hecho push: `main` va por delante de `origin/main`.
- Los worktrees siguen en `~/.claudette/workspaces/KontaFlow-SV/`. El bench (`~/frappe-kf/kf-bench`) carga la app desde `vivid-delphinium` (rama `claudette/kf-04-2-docs-review`, mismo código que `main`) mediante un symlink y `kontaflow_sv.pth`. Para que el bench use esta carpeta hay que actualizar ambos y verificarlo con `env/bin/python -c 'import kontaflow_sv;print(kontaflow_sv.__file__)'`. Es un cambio compartido y requiere autorización.
- Roles vigentes (los de [AGENTS.md](../AGENTS.md), aún sin commitear en `main`): Claude orquesta y planifica, Codex implementa y un revisor de solo lectura audita. KF-01 a KF-04.2 se hicieron con el esquema anterior (Claude implementaba y Codex revisaba).

## Pendiente para la próxima sesión (pausa del 2026-11-20)

1. **KF-06.1 cerrada (2026-11-20):** doble revisión hecha (ver «KF-06.1-2-R»), aprobada por la persona responsable, migración aplicada en `kf.localhost`; commit `60bc1d3` en `vivid-delphinium` y `f9ec664` en `main` (`cherry-pick`). Sin push. Queda como tarea posterior absorber los menores de la revisión (tests de borde de tolerancia y de `numeroDocumento` nulo, docstring de `api.py:11`, caso de versión de 06 en `test_notas_v4.py:60`, recorte de espacios en referencias) y el recorrido en Desk de una NC y una ND.
2. **KF-06.2** (consulta, vista previa y exportación de 05 y 06 con la matriz de signos de «KF-05»): KF-06.1 ya está aprobada; **redactar el encargo**.
3. **Deudas abiertas:** recorrido de KF-04-R en un sitio con el asistente inicial completo; observaciones menores de KF-04.3 y KF-05-3; KF-07 sin encargo; push de `main` sin autorizar (va por delante de `origin/main`).
4. **Riesgos del entorno:** el ejecutor en sandbox no puede correr la suite de Frappe (`logs/bench.log` de solo lectura): la ejecuta el orquestador. No ejecutar dos suites a la vez sobre `kf.localhost`.

## Tareas

| ID | Responsable | Estado | Entrega |
| --- | --- | --- | --- |
| KF-01 / KF-01-R | Claude / Codex | Hecha | Entorno local y app base sobre Frappe y ERPNext. |
| KF-02 / KF-02-R | Claude / Codex | Hecha | Ingesta de CCF v3 en borrador. |
| KF-03 / KF-03-R | Claude / Codex | Hecha | Ingesta de CCF v4 y convivencia con v3. El mismo código en otra versión de la misma empresa reporta conflicto y conserva el primer borrador. |
| KF-04.1 | Claude | Hecha (aprobada por la persona responsable el 2026-11-09; Codex la cubre en KF-04-R) | Consulta de borradores por empresa y mes con permisos y orden estable: `kontaflow_sv/libro_compras/consulta.py`. |
| KF-04.2 | Claude | Hecha | Filas, advertencias y totales exactos para la vista previa: `kontaflow_sv/libro_compras/vista_previa.py`. Revisada por Codex en `668659f`. |
| KF-04.3 | Codex (ejecutor) | Hecha (commit `7f165d2`; dos revisiones sin defectos y suite completa en verde el 2026-11-19) | Reporte en Frappe Desk con filtros, totales y enlace al borrador: `kontaflow_sv/kontaflow_sv/report/vista_previa_del_libro_de_compras/` y `kontaflow_sv/tests/test_libro_compras_reporte.py`. |
| KF-05 | Codex Sol 6.2 (ejecutor) | Hecha (commit `5a674bf` en `vivid-delphinium`, 2026-11-20; doble revisión sin defectos bloqueantes, recorrido en Desk y XLSX abierto en una hoja de cálculo) | Exportación a Excel del Libro de Compras de CCF sobre la plantilla contable `docs/formato-libros-contables.xlsx` (hoja `LibroCompras`). Ver «KF-05». |
| KF-05-3 | Codex Sol 6.2 (ejecutor) | Hecha, aprobada por la doble revisión (2026-11-19); commit `5a674bf` junto con KF-05 | Período vacío sin salir de Desk, formato condicional de duplicados con más de 35 filas y pluralización de la nota. La fila de TOTAL no cambia. Encargo [`KF-05-3.md`](encargos/KF-05-3.md). |
| KF-05-R | sonnet-reviewer + Codex Sol 6.2 (doble revisión) | Hecha (2026-11-20). Rondas 1 y 2 y KF-05-3 cerradas; recorrido en Desk y XLSX abierto en una hoja de cálculo por la persona responsable | Revisar columnas, signos, totales exactos, permisos y el archivo generado. |
| KF-06.1 | Codex Sol 6.2 (ejecutor) | Hecha (2026-11-20; commit `60bc1d3` en `vivid-delphinium`, `f9ec664` en `main`; doble revisión: Sonnet aprueba, Sol pide iteración 3 por el recorte de espacios en referencias, aprobada por la persona responsable con ese punto como tarea posterior; suite 102 unitarias y 117 de integración en verde) | Ingesta de notas de crédito (05) y débito (06) v4 como borradores, con documento relacionado; importes en positivo. Encargos [`KF-06.md`](encargos/KF-06.md) y [`KF-06-2.md`](encargos/KF-06-2.md). |
| KF-06.2 | Claude (planifica) | Lista para iniciar (redactar encargo) | Consulta, vista previa y exportación a Excel de 05 y 06 con la matriz de signos de «KF-05». |
| KF-07 | Claude (planifica) | Planificada, sin encargo | Sujeto excluido (14), columna T de la plantilla. |
| KF-04-R | Revisor | En revisión (condición abierta) | Falta el recorrido en Desk real, con el asistente de configuración completado. El resto está verificado (ver «Revisión»). |

Estados de trabajo: **Lista para iniciar**, **En curso**, **En revisión**, **Bloqueada** y **Hecha**. Si una tarea depende de otra, habilítala cuando su dependencia quede cerrada. Cada entrega registra la base de Git, los archivos y las verificaciones en este tablero.

## KF-04 · Vista previa del Libro de Compras

### KF-04.1 · Consulta y permisos

- [x] Consultar `KontaFlow DTE Compra` en estado **Borrador**, con una empresa y un mes obligatorios. Usar `fecha_emision` desde el primer día del mes hasta el primer día del mes siguiente, excluido. Incluir CCF v3 y v4.
- [x] Aplicar los permisos del usuario sobre la empresa y los DTE. Ordenar por fecha de emisión y usar el nombre del documento para desempatar.
- [x] Probar con datos ficticios los límites del mes, un período vacío, un mes inválido y el aislamiento entre dos empresas. Verificar que un usuario autorizado vea su empresa y que una empresa ajena produzca un error de permiso.

### KF-04.2 · Filas y totales

- [x] Proyectar una fila por DTE con fecha de emisión, proveedor, NIT del emisor, número de control, montos gravados, exentos y no sujetos, IVA, advertencias e identificador del borrador.
- [x] Sumar las cuatro columnas monetarias con aritmética decimal sobre todos los borradores autorizados del período. Usar los importes ya guardados en el DTE. Conservar las advertencias de cada fila.
- [x] Probar importes fraccionarios, una fila con advertencia y un período vacío. Comparar las sumas con el detalle para detectar duplicados y errores de precisión.

### KF-04.3 · Reporte en Frappe Desk

- [x] Exponer la consulta como reporte de lectura con filtros obligatorios de empresa y mes. Mostrar el título **Vista previa del Libro de Compras**, las filas y los totales.
- [x] Enlazar cada fila al borrador correspondiente mediante un enlace de Frappe. Mantener los controles de permisos también al ejecutar el reporte directamente.
- [~] Verificar desde Desk los filtros, las advertencias, el caso sin resultados y el enlace. Dejar instrucciones para repetir el flujo con datos ficticios.

### KF-04-R · Revisión independiente

Leyenda: `[x]` hecho, `[~]` hecho con una condición abierta, `[ ]` pendiente.

- [ ] Comparar los totales con los borradores de prueba y repetir los casos de fechas, permisos y aislamiento. Verificar que el enlace abra el registro correcto y que el reporte solo lea datos.
- [ ] Ejecutar las pruebas de KF-04 y la regresión de ingesta v3/v4 en el sitio de desarrollo. Registrar comandos, resultados y limitaciones en este tablero.

## Revisión

### KF-04-R · Entrega KF-04.3 · agente-revisor-1 · 2026-11-19

Revisé los seis archivos nuevos y el cambio de guía en `vivid-delphinium`, sobre la base `cee9276`. El reporte estándar delega en `vista_previa` y conserva la consulta autorizada, los límites del mes y la suma con `Decimal`. Los cambios se limitan a las rutas del encargo.

**Verificación independiente en `kf.localhost`.** Con los esquemas v3 y v4 configurados, ejecuté `bench --site kf.localhost run-tests --app kontaflow_sv`. Pasaron las 82 unitarias. La corrida de integración se interrumpió tras 26 pruebas y cuatro errores. El primer interbloqueo de MariaDB (1213) ocurrió en `TestIngestaConcurrente.tearDownClass` al eliminar las cuentas de una empresa ficticia. El log del ejecutor registra 104 integraciones aprobadas en su corrida completa.

- Repetí la suite completa con Desk detenido. Pasaron las 82 unitarias. La integración ejecutó 104 pruebas con 12 errores. En las clases de consulta y reporte, los primeros errores ocurrieron en `borrar_dte` durante `setUp` (MariaDB 1020 sobre `KontaFlow DTE Compra Item`). Los siguientes casos de esas clases fallaron porque su empresa ficticia dejó de estar disponible tras la reversión de la transacción. Retiré las dos empresas ficticias que dejó la primera corrida y comprobé que las empresas afectadas del reintento ya no existían.
- Repetí el comando con `--module kontaflow_sv.tests.<módulo>` por separado. Pasaron 15 pruebas de `test_libro_compras_consulta`, 15 de `test_libro_compras_vista_previa`, 11 de `test_libro_compras_reporte` y 50 de `test_ingesta_dte_compra`.
- Por la vía de `frappe.desk.query_report.run` comprobé los filtros requeridos, mes inválido, aislamiento por empresa, rechazo por rol, período vacío y ausencia de cambios en los borradores. La suite comprobó los límites de fecha, el IVA guardado, una sola fila de totales y la conservación de centavos al serializar a JSON, incluidos `1,00` y `15 308 642 197,53`.
- Pasaron `ruff check --no-cache`, `ruff format --check --no-cache`, `node --check` y `git diff --check`. Los logs del ejecutor muestran fallos para las siete mutaciones pedidas: total automático, suma con `float`, enlace eliminado, filtro opcional, sustitución de la consulta autorizada, advertencias descartadas y total duplicado. Revisé esos logs sin mutar el código entregado.

**Desk y decisión pendiente.** Con `bench start`, la navegación normal en `kf.localhost` redirigió a `/desk/setup-wizard/0`. Repetí la prueba en Chromium simulando la configuración completada solo en el navegador. Con Administrator confirmé el título, los filtros, las dos filas, la advertencia, el período vacío y los totales de 110,00 gravadas y 13,30 de IVA. Con ambos usuarios abrí el borrador correcto y confirmé que el total carece de enlace. Con Accounts User confirmé que la empresa ajena quedó fuera del selector y que la ejecución directa devolvió un 403. Retiré los datos ficticios al terminar.

**Dictamen para Claude.** Sin defectos funcionales reproducidos en el reporte. Mantener KF-04.3 en revisión hasta obtener una corrida completa repetible y verificar el recorrido documentado en un sitio con el asistente inicial completado.

#### Informe de revisión · KF-04.3 · agente-revisor-2 (2026-11-19)

Base `cee9276`, worktree `vivid-delphinium`, cambios sin commit. Revisión de solo lectura: restauré tras cada mutación los archivos que alteré temporalmente y verifiqué que el árbol quedó idéntico.

| # | Área | Resultado | Evidencia | Severidad |
| --- | --- | --- | --- | --- |
| 1 | Alcance | Cumple | Solo rutas previstas: `report/…` (4 archivos), `test_libro_compras_reporte.py` y `docs/DESARROLLO_LOCAL.md`. `vista_previa.py`, `consulta.py`, `hooks.py` y el tablero intactos. | — |
| 2 | Instalación | Cumple | `bench --site kf.localhost migrate` sin errores. Reporte estándar, Script Report, roles Accounts User, Accounts Manager y System Manager, `add_total_row` 0, `prepared_report` 0. | — |
| 3 | Filtros obligatorios | Cumple | `reqd` en `company` y `mes` en el JS (sin valor por defecto en `mes`). Ejecución directa sin filtros, con mes inválido (`2026-13`) o sin mes lanza `ValidationError` desde `vista_previa`. | — |
| 4 | Columnas y filas | Cumple | 13 columnas en el orden de `COLUMNAS` y con las etiquetas literales; «IVA del DTE» muestra el IVA guardado (12,00 sobre 100,00). Filas idénticas a `vista_previa`; advertencias unidas con `"; "`. | — |
| 5 | Enlace y fila Total | Cumple | Borrador es `Link` a `KontaFlow DTE Compra`; la fila Total lleva «Total» en Proveedor y no tiene `name`. | — |
| 6 | Totales y precisión | Cumple | Totales de `vista_previa` (`Decimal`) con `quantize(0,01)`, sin `add_total_row` ni `float`. Camino completo `run` → `as_json`: diez filas de 0,10 suman 1,00 y 15 308 642 197,53 conserva los centavos. | — |
| 7 | Permisos y aislamiento | Cumple | Contador de A ve solo sus DTE; empresa B y empresa inexistente dan `PermissionError` con el mismo mensaje; usuario sin rol de contabilidad es rechazado. Todo por `frappe.desk.query_report.run`. | — |
| 8 | Período vacío y aviso | Cumple | Sin filas devuelve `[]` y «No hay borradores de CCF para la empresa y el mes indicados», sin error. Aviso «1 borrador tiene advertencias» / «N borradores tienen advertencias». | — |
| 9 | Solo lectura | Cumple | Prueba compara nombres y `modified` antes y después. El código solo llama a `vista_previa` y `get_cached_value`. | — |
| 10 | Pruebas | Cumple | `bench --site kf.localhost run-tests --app kontaflow_sv`: **104 pruebas de integración, OK** (93 previas + 11 nuevas), 89 s. No volví a ejecutar las 82 unitarias, que esta tarea no toca. | — |
| 11 | Mutaciones | Cumple | Probé 5 y la suite detectó las 5: `mes` sin `reqd`, Borrador como `Data`, advertencias descartadas, fila Total duplicada y importes en `float`. No probé «`get_all` en lugar de la consulta autorizada». | — |
| 12 | Calidad | Cumple | `ruff check` y `ruff format --check` limpios sobre los archivos nuevos. | — |
| 13 | Flujo manual en Desk | **No verificado por mí** | No abrí Desk ni un navegador. La guía de `DESARROLLO_LOCAL.md` es coherente con los helpers y los importes (110,00 gravadas y 13,30 de IVA con los dos DTE del ejemplo), pero el enlace y los filtros en pantalla quedan sin ver. | Media |
| 14 | `formatter` del JS | Observación | Escapa el valor de las columnas `Data` y el formateador por defecto de Frappe lo desescapa y lo vuelve a escapar. Es inocuo, aunque redundante. | Baja |
| 15 | Prueba de filtros en Desk | Observación | `test_filtros_obligatorios_en_desk` verifica `reqd` con expresiones regulares sobre el texto del script; detecta el cambio, pero es frágil ante reformateos. | Baja |

**Veredicto: aprobada con una condición.** No hay hallazgos que bloqueen. Antes de cerrar KF-04-R conviene que alguien repita en Desk los pasos 1 a 5 de la guía (filtros, filas, enlace, caso vacío y usuario limitado), porque ninguna prueba automática cubre la interfaz. Los puntos 14 y 15 son opcionales.

### Decisión de Claude (orquestador) · 2026-11-19

Con la persona responsable: se commitea KF-04.3 (`7f165d2`) y se integra en `main`. Evalúo así los dictámenes:
- **Corrida completa repetible:** la condición del revisor 1 queda cubierta. Repetí en `kf.localhost`, con servicios arriba y sin otras corridas en paralelo, `bench --site kf.localhost run-tests --app kontaflow_sv`: **82 unitarias y 104 de integración, OK** (68 s), igual que el revisor 2 y el ejecutor. Los 12 errores del revisor 1 (MariaDB 1020 y 1213 en `setUp` y `tearDownClass`) no se reprodujeron; encajan con corridas simultáneas sobre el mismo sitio. Queda como riesgo conocido: **no ejecutar dos suites a la vez sobre `kf.localhost`**.
- **Mutaciones:** cubiertas entre ambos revisores las siete pedidas (el revisor 2 no probó la sustitución por `get_all`; el revisor 1 la revisó en los logs del ejecutor).
- **Pendiente (condición abierta de KF-04-R):** el recorrido en Desk de los pasos 1 a 5 de `docs/DESARROLLO_LOCAL.md` en un sitio con el asistente inicial completado. El revisor 1 lo hizo en Chromium simulando esa configuración solo en el navegador, y el revisor 2 no abrió Desk.
- **Observaciones opcionales (baja):** el `formatter` del JS escapa de más (inocuo) y `test_filtros_obligatorios_en_desk` lee el texto del script con expresiones regulares (frágil ante reformateos).

### KF-05-R · Entrega KF-05 · agente-revisor-1 · 2026-11-19

**Dictamen para Claude. Solicitar cambios.** Revisé la entrega sin commit en `vivid-delphinium`, sobre `6d16d03`, contra el encargo vigente de KF-05 (hoy en `docs/encargos/KF-05.md`).

1. **[P1] El archivo conserva la distribución sustituida de Oculus.** `exportacion.py:15–40,126–148` crea una hoja `Libro de compras` de 24 columnas desde un `Workbook()` vacío. La referencia `LibroCompras` tiene 20 columnas y 15 rangos combinados. El archivo generado tiene cero combinaciones y comienza con encabezados en la fila 1. Faltan la cabecera de empresa, mes, año, NIT y NRC, el detalle desde la fila 8, el TOTAL en E y las líneas de firma. La copia de la plantilla prevista tampoco aparece en el árbol. La guía de Desk y `test_libro_compras_exportacion.py:159` fijan el formato anterior.
2. **[P1] El total por documento y por período excluye las compras exentas.** `exportacion.py:78–86` suma gravadas e IVA guardado. Reabrí con openpyxl un archivo que generé en memoria con 100,00 gravadas, 12,00 de IVA y 5,05 exentas. El detalle exportado mostró 112,00 en O2 y el total exigido en R8 es 117,05. Los acumulados se alimentan del mismo importe incompleto.
3. **[P2] Faltan FOVIAL, COTRANS y la nota de compras no sujetas.** `exportacion.py:42,104–112` solo lee importes del documento padre y deja sin origen la columna agrupada de contribuciones. El encargo exige leer los tributos autorizados `D1` y `C8` y escribirlos en N y O. El archivo pone las compras no sujetas en una columna propia y omite la nota con cantidad de documentos e importe.

**Comprobaciones.** `git diff --check`, `node --check`, `ruff check` y `ruff format --check` pasaron. Por inspección, el endpoint reutiliza `consultar_borradores`, exige permiso de exportación y limita la lectura de importes a los nombres consultados. La lógica usa `Decimal` y rechaza tipos sin regla. Quedan sin verificación independiente la suite completa, las mutaciones y la descarga desde Desk. La siguiente entrega debe validar el XLSX resultante contra la plantilla vigente, incluidos permisos por API, más de 35 borradores, el mapeo A–T y los centavos en el XML.

### KF-05-R · Ronda 2 · sonnet-reviewer · 2026-11-19

Revisión de solo lectura de la entrega sin commit en `vivid-delphinium` (base `6d16d03`): `exportacion.py`, `plantilla_libro_compras.xlsx`, `test_libro_compras_exportacion.py`, `api.py`, el `.js` del reporte y `DESARROLLO_LOCAL.md`. Es la primera de las dos revisiones de la ronda 2; falta la de Codex Sol. Los tres hallazgos de la ronda 1 están corregidos en el árbol actual, aunque el tablero seguía marcando la iteración 2 como pausada.

| # | Área | Resultado | Evidencia |
| --- | --- | --- | --- |
| 1 | P1 ronda 1 · distribución | Corregido | El libro parte de la copia de la plantilla, con una sola hoja `LibroCompras`. Conserva las 15 combinaciones, la cabecera (A1, B3, Q3, B4, Q4), el detalle desde la fila 8, TOTAL en E y las dos líneas de firma. Lo comprobé generando libros de 3, 35 y 40 filas con `_crear_xlsx`: el pie se desplaza bien (TOTAL en E12 con 3 filas y en E49 con 40), con las alturas de fila y sin filas de ejemplo residuales. |
| 2 | P1 ronda 1 · total sin exentas | Corregido | `TOTAL COMPRAS = SUM(G:M)` (`COLUMNAS[6:13]`). Con 5,05 exentas, 100,10 gravadas y 13,01 de IVA, R da 118,16. Percibido (Q), retenido (S) y contribución especial quedan fuera. |
| 3 | P2 ronda 1 · tributos y no sujetas | Corregido | N y O suman los tributos `D1` y `C8` leídos con `CAST … AS CHAR` sobre los nombres autorizados. La nota «Compras no sujetas no incluidas: N documentos por $X» aparece bajo la firma y solo si hay no sujetas. |
| 4 | Importes exactos | Cumple | Las celdas se escriben desde `Decimal` con `data_type="n"`; en el XML quedan `118.16` y `2.00`, sin `float`. |
| 5 | Permisos | Cumple | `consultar_borradores` primero y después `has_permission(..., "export", throw=True)`. La API usa `methods=["POST"]` y el botón envía `open_url_post`. |
| 6 | Pruebas | Cumple | Suite completa en `kf.localhost`: **86 unitarias y 114 de integración, OK** (93 s). Son 4 y 10 más que la base de 82 y 104; las 10 integraciones son las del módulo nuevo. |
| 7 | Mutaciones | Cumple | Probé 5 sobre `exportacion.py` con el módulo nuevo; la suite detectó las 5: sin permiso de exportación, total que suma percibido y retenido, filas de ejemplo sin borrar, importes por `float` y tipo desconocido tolerado. Restauré el archivo (mismo hash). No probé las demás mutaciones del encargo. |
| 8 | Calidad | Cumple | `ruff check` y `ruff format --check` limpios en los tres archivos Python, y `git diff --check` sin avisos. |
| 9 | Descarga y flujo en Desk | **No verificado por mí** | No abrí Desk ni un navegador ni una hoja de cálculo: solo inspeccioné el XLSX con openpyxl. La guía de `DESARROLLO_LOCAL.md` es coherente con los importes (128,35 en R). |
| 10 | Formato condicional | Observación (baja) | La plantilla trae 13 reglas `duplicateValues` en la columna C, con rangos fijos (`C8`, `C9:C10`… `C43:C1048576`). `insert_rows` no los desplaza, de modo que con más de 35 documentos el resaltado de duplicados no cubre bien las filas añadidas. Es solo visual. |
| 11 | Fila de TOTAL | Observación (baja) | Las columnas sin dato (H, I, K, L, P y T) salen con `0.00` en la fila TOTAL. El encargo pide vacías en las filas de datos, que sí lo están; en el total es una decisión de presentación. |
| 12 | Nota de no sujetas | Observación (baja) | Con un solo documento dice «1 documentos». |

**Veredicto: aprobada con observaciones menores.** No encontré defectos que bloqueen. Antes de cerrar KF-05-R faltan la segunda revisión (Codex Sol) y el recorrido manual en Desk: descarga con el botón, apertura en una hoja de cálculo y repetición con el usuario limitado. Los puntos 10 a 12 son opcionales.

**Entorno.** `~/frappe-kf/tools/arrancar-servicios.sh` no regresa al terminal: ejecutado dentro de una tarea que luego se detiene, arrastra a MariaDB. Se lanza con `setsid nohup … &`. Dejé los servicios arriba y sin suites en marcha.

### KF-05-R · Ronda 2 · Codex Sol (revisor 2) · 2026-11-19

**Dictamen para Claude. Aprobada en revisión técnica, con el recorrido en Desk pendiente para el cierre.** Revisé los seis archivos de la entrega sin commit en `vivid-delphinium`, base `6d16d03`. Confirmé que se corrigieron los tres hallazgos de la ronda 1.

- **Plantilla.** Generé y reabrí libros con 1, 35 y 40 borradores ficticios. La salida contiene solo `LibroCompras`, conserva las 15 combinaciones y desplaza el TOTAL y la nota con el detalle. La prueba de integración también comprueba encabezados, anchos, estilos y firma.
- **Importes.** Con 5,05 exentas, 100,00 gravadas y 12,00 de IVA guardado, R8 contiene 117,05. Con 40 filas, R49 contiene 4 682,00. FOVIAL, COTRANS, percibido y retenido salen en N, O, Q y S, respectivamente, fuera de ese total. La nota cuenta los documentos con compras no sujetas y suma esos importes. El módulo verifica los centavos en el XML y el rechazo de tipos sin regla de signo.
- **Permisos y filtros.** El módulo verificó exportación limitada a registros visibles, denegación por empresa ajena e inexistente, usuario sin rol y usuario con lectura pero sin exportación. También pasó la cobertura de filtros inválidos, período vacío y conservación de los borradores.
- **Comprobaciones propias.** En `kf.localhost`, `bench --site kf.localhost run-tests --app kontaflow_sv --module kontaflow_sv.tests.test_libro_compras_exportacion` pasó **4 unitarias y 10 de integración**. Pasaron Ruff (lint y formato), `node --check` y `git diff --check`. La suite completa y las mutaciones constan en el informe de Sonnet; esta revisión ejecutó el módulo de exportación y comprobó los XLSX en memoria.

El cierre queda a cargo del orquestador tras verificar la descarga desde el botón de Desk, abrir el archivo en una hoja de cálculo y repetir con un usuario limitado a su empresa.

### KF-05-R · Recorrido en Desk · Claude (orquestador) · 2026-11-19

Recorrí `docs/DESARROLLO_LOCAL.md` (sección KF-05) en `kf.localhost` con Chromium automatizado (Playwright), sobre el árbol sin commit de `vivid-delphinium`. El sitio sigue sin el asistente inicial de Frappe, así que simulé la configuración completa solo en el navegador (sin tocar el sitio). Datos ficticios con `FixturesDePrueba`; los retiré al terminar (0 empresas «KF Prueba», 0 borradores y el usuario temporal eliminado).

| Paso | Resultado |
| --- | --- |
| 1. Botón con Administrator, empresa A, `2026-09` | Descarga `<empresa>_Libro de compras_2026-09_borradores.xlsx`. El reporte exige Empresa y Mes. |
| 2. Contenido del archivo | Una sola hoja `LibroCompras`, 15 combinaciones, A1 con la empresa, B3 SEPTIEMBRE, Q3 2026, NIT en B4 y NRC en Q4. Los dos borradores ocupan las filas 8 y 9 en orden de emisión. |
| 3. Totales | TOTAL en E11: exentas 5,05 (G), gravadas 110,00 (J), crédito fiscal 13,30 (M) y TOTAL COMPRAS 128,35 (R). La fila 8 da 117,05. Firma en E14 y E15 y nota en A16: «Compras no sujetas no incluidas: 1 documentos por $2,10». |
| 4. Usuario limitado a la empresa A | Solo ve su empresa en el selector. La descarga de la empresa A da el mismo contenido que con Administrator. Por la API, la empresa B devuelve 403 («No tiene acceso a la empresa indicada»). |
| 4b. Período vacío `2026-10` | El reporte muestra «No hay borradores de CCF para la empresa y el mes indicados». **Defecto de UX:** al pulsar el botón con ese período, `open_url_post` saca al usuario de Desk y muestra una página «Server Error 417 · Uncaught Exception» sin el mensaje. La respuesta del servidor es correcta (`ValidationError` con el mensaje). |
| 5. Limpieza | Hecha. |

**Pendiente:** abrir el XLSX en una hoja de cálculo real (solo lo inspeccioné con openpyxl); solución para 4b (por ejemplo deshabilitar el botón o avisar en el cliente cuando el reporte está vacío, o exportar con `frappe.call`/descarga por fetch para mostrar el mensaje); las tres observaciones menores de Sonnet siguen sin atender.

### KF-05-3 · Entrega y revisión · 2026-11-19

**Entrega de Codex (Sol 6.2, medium).** Sin commit sobre `6d16d03`; modificó `docs/DESARROLLO_LOCAL.md`, el `.js` del reporte, `exportacion.py` y `test_libro_compras_exportacion.py`. El botón usa `fetch` POST con CSRF y muestra los errores con `frappe.msgprint` sin salir del reporte. Una sola regla `duplicateValues` cubre el detalle (`C8`, `C8:C42`, `C8:C47` con 1, 35 y 40 filas). La nota dice «1 documento» o «N documentos». La fila TOTAL no cambió. Detectó las 3 mutaciones pedidas. Su sandbox impidió la suite de integración (socket de MariaDB).

**Verificación del orquestador.** Suite completa en `kf.localhost`: **114 integraciones OK** (88 unitarias, según Codex). Recorrido en Desk con Playwright: período vacío `2026-10` conserva la página y muestra «No hay borradores de CCF para la empresa y el mes indicados»; la descarga con Administrator y con el usuario limitado a la empresa A da el mismo contenido (nota «1 documento por $2,10», regla `C8:C9`, TOTAL 128,35); empresa ajena por la API devuelve 403. Datos ficticios retirados.

**Doble revisión.** `sonnet-reviewer`: aprobada, sin hallazgos bloqueantes. Codex Sol: aprobada con una observación menor. Observaciones menores no bloqueantes: sin indicador rojo en los avisos y sin guarda contra doble clic (Sonnet); la prueba del formato condicional no comprueba `dxfId` (Sonnet); el JS no tiene prueba automatizada; la expresión regular del `filename` acepta `filename=""` (Sol), pero Frappe genera siempre un encabezado válido, por lo que no hay efecto real.

**Decisión de Claude.** KF-05 y KF-05-R quedan aprobadas técnicamente. Cierre (2026-11-20): la persona responsable abrió el XLSX en una hoja de cálculo y lo dio por bueno; se commitea (`5a674bf`).

### KF-06.1-R · Codex Sol (revisor 2) · 2026-11-20

**Dictamen para Claude. Solicitar cambios.** Revisé la entrega de ingesta 05/06 v4 sin commit en `vivid-delphinium`, base `5a674bf`.

1. **[P1] El cuadre de las notas confía en un subtotal sin verificar.** En `kontaflow_sv/ingesta/dte_compra.py:450,463–464,492–519`, el parser valida cada total de ventas contra los ítems, pero calcula el subtotal neto a partir de `subTotalVentas` sin comprobar que coincida con no sujetas + exentas + gravadas. Reproduje para 05 y 06 que un detalle con 100,00 gravadas y 12,00 de IVA acepta `subTotalVentas=1000`, `montoTotalOperacion=1012` y `totalPagar=1012`, sin una advertencia por esa diferencia. La API pasa ese resumen al borrador. Validar el cuadre de `subTotalVentas` antes de usarlo y cubrirlo en ambos tipos con una prueba.
2. **[P2] Un ítem puede apuntar a un documento ausente de las referencias de la nota.** En `kontaflow_sv/ingesta/dte_compra.py:309–327,370,389–391`, ambas referencias se validan por separado. En los dos fixtures cambié el número del primer ítem a `REFERENCIA-AJENA` y el parser lo aceptó junto con la referencia original de cabecera. Comprobar que cada ítem referencia un número declarado en la propia nota. Esta comprobación es interna al JSON y no requiere buscar un CCF ingerido.

**Verificación independiente.** Pasaron 10 casos del parser de notas, incluida la validación de ambos fixtures contra los esquemas del ZIP local, y 69 casos del parser y selector CCF v3/v4. Ejecuté los casos puros con `unittest` sin inicializar el sitio Frappe. Pasaron Ruff (lint y formato en siete archivos Python) y `git diff --check`. Por inspección, la entrega añade una tabla hija para las referencias, conserva la API y la lógica de identidad, y documenta `bench migrate`. No ejecuté la migración, las pruebas de integración, la suite completa ni las mutaciones en esta revisión.

### KF-06.1-2 · Entrega y verificación · 2026-11-20

**Entrega de Codex (Sol 6.2, low).** Sin commit sobre `5a674bf`; modificó `kontaflow_sv/ingesta/dte_compra.py` y `kontaflow_sv/tests/test_notas_v4.py`. Las notas 05 y 06 rechazan un `subTotalVentas` que difiere en más de 0,01 de no sujetas + exentas + gravadas (decisión de la persona responsable: rechazo, como el CCF), y cada ítem debe apuntar a un `numeroDocumento` declarado en el `documentoRelacionado` de su nota (los esquemas excluyen `null`, así que no se tolera la omisión). Detectó las 3 mutaciones pedidas. Su sandbox impidió la suite con Frappe (`logs/bench.log` de solo lectura).

**Verificación del orquestador.** Suite completa en `kf.localhost`: **102 unitarias y 117 de integración, OK**. Pendiente: doble revisión (sonnet-reviewer y Codex Sol en low) y autorización para commitear.

### KF-06.1-2-R · Doble revisión · 2026-11-20

Ambas de solo lectura sobre el árbol sin commit (base `5a674bf`); ninguna ejecutó la suite de Frappe ni la migración.

- **sonnet-reviewer: aprobar, sin hallazgos bloqueantes ni importantes.** Cinco observaciones bajas: falta test de `numeroDocumento` de ítem `None` o vacío; sin test de borde de la tolerancia de `subTotalVentas` (0,01 aceptada, 0,02 rechazada, ausente); `totalDescu` no se coteja con `montoDescu` de los ítems (laguna heredada, `dte_compra.py:518`); cobertura faltante (ND sin `numPagoElectronico`, CCF 03 con `documentoRelacionado`); el test de `totalGravada` (`test_notas_v4.py:88`) depende del orden de los cuadres.
- **Codex Sol: iteración 3.** Importante: `_texto` aplica `strip()` (`dte_compra.py:197`) y la referencia de ítem `"00017 "` se acepta contra la declarada `"00017"` (JSON válido por esquema en 05 y 06; reproducido por Sol y confirmado en el código por el orquestador). Menores: el caso de versión incorrecta de 06 parte de una NC con número de control `DTE-05` (`test_notas_v4.py:60`); la docstring de `api.py:11` dice que el tipo sale de `identificacion.version` (sale de `tipoDte`). Confirmó cuadre 0,01/0,02 en 05 y 06, CCF intacto y las 3 mutaciones detectadas.

**Decisión pendiente de la persona responsable:** la discrepancia es solo el recorte de espacios. Recomendación del orquestador: aprobar sin iteración 3 (los dos lados pasan por la misma normalización y se guarda el valor recortado) y absorber los menores y los tests de borde en una tarea posterior; la alternativa es una iteración 3 corta para comparar los valores originales.

## KF-05 · Exportación a Excel del Libro de Compras

**Plantilla vigente (2026-11-19):** la aportada por la persona responsable, [`formato-libros-contables.xlsx`](formato-libros-contables.xlsx), hoja `LibroCompras` (20 columnas, A a T, con título, MES, AÑO, NIT, NRC, fila de TOTAL y línea de firma del contador). **Sustituye a la distribución de 24 columnas de Oculus**, que solo se conserva como referencia de lógica de signos. El libro también trae las hojas `LibroVentasConstribuyente`, `LibroVentasConsumidor` y `LibroDiarioMayor`, que quedan como referencia para tareas futuras.

**Fórmula confirmada por la persona responsable:** `TOTAL COMPRAS = SUM(G:M)`, es decir, exentas (internas + internaciones + importaciones) + gravadas (internas + internaciones + importaciones) + crédito fiscal. El **anticipo a cuenta IVA percibido** (Q), la **retención a terceros** (S), la contribución especial (N a P) y las compras a sujetos excluidos (T) **no entran en el total**: son columnas aparte. Esto difiere de la fórmula de Oculus (gravadas + IVA + percibido − retenido + otros), que no se usa.

### Mapeo de columnas (tipo 03)

| Col. | Título de la plantilla | Origen en `KontaFlow DTE Compra` |
| --- | --- | --- |
| A | No. | Correlativo 1, 2, 3… según el orden de `consultar_borradores` |
| B | FECHA DE EMISION | `fecha_emision` (como fecha, con el formato de la plantilla) |
| C | N° DE DOCUMENTO | `codigo_generacion` (por defecto; ver decisiones) |
| D | NRC | `emisor_nrc` |
| E | NIT O DUI DE SUJETO EXCLUIDO | `emisor_nit` |
| F | NOMBRE DE PROVEEDOR | `emisor_nombre` |
| G / H / I | COMPRAS EXENTAS: Internas / Internaciones / Importaciones | `total_exenta` en G; H e I vacías |
| J / K / L | COMPRAS GRAVADAS: Internas / Internaciones / Importaciones | `total_gravada` en J; K y L vacías |
| M | CREDITO FISCAL | `iva` guardado en el DTE (la plantilla lo calcula como 13 %; KontaFlow no lo recalcula) |
| N / O / P | CONTRIBUCION ESPECIAL: FOVIAL / COTRANS / CESC | Tributos del DTE con código `D1` (FOVIAL) y `C8` (COTRANS), CAT-015; CESC vacío (no tiene código en el catálogo) |
| Q | ANTICIPO A CUENTA IVA PERCIBIDO | `iva_percibido` |
| R | TOTAL COMPRAS | `SUM(G:M)`, calculado con `Decimal` |
| S | RETENCION A TERCEROS | `iva_retenido` |
| T | COMPRAS A SUJETOS EXCLUIDOS | vacío (tipo 14, KF-07) |

La plantilla **no tiene columna de compras no sujetas**. Si algún borrador del período tiene `total_no_suj` mayor que cero, la exportación no lo pierde en silencio: añade bajo los totales una nota con la cantidad de documentos y el importe (decisión abierta).

### Matriz de signos (lógica de Oculus, verificada con CAT-002 de Hacienda)

| Tipo | Documento | Signo |
| --- | --- | --- |
| 03 | Comprobante de crédito fiscal | positivo |
| 05 | Nota de crédito | **negativo**: se invierten todos los importes del documento (Oculus invierte gravadas, crédito fiscal, percibido, retenido, FOVIAL/COTRANS/CESC y total; aquí se incluyen también exentas, por coherencia). Las fórmulas de la plantilla toleran negativos |
| 06 | Nota de débito | positivo |
| 14 | Factura de sujeto excluido | positivo, en la columna T. La plantilla no la incluye en `TOTAL COMPRAS` (Oculus sí resta la retención); se decide en KF-07 |

KF-05 solo exporta el tipo **03**. Una función pura aplica el signo por `tipo_dte` y falla de forma explícita ante cualquier tipo sin regla. 05, 06 y 14 se implementan en KF-06 y KF-07. `Project_Context.md` tiene 05 y 06 invertidos: 05 es nota de crédito y 06 nota de débito.

### Diferencias con Oculus que no se copian

`Decimal` en lugar de `float`; IVA guardado en lugar de recalculado; exentas llenas; fallo explícito ante tipos desconocidos en lugar de descartarlos.

### Material de apoyo añadido el 2026-11-19

- `docs/03_ccf_ejemplo.json`, `05_nota_credito.json`, `14_sujeto_excluido.json`, `04_nota_remision.json`, `evento_contingencia.json`, `evento_invalidacion.json`: ejemplos **ficticios y simplificados**. Validados contra los esquemas oficiales de `esquemas/` **no los cumplen** (entre 22 y 46 errores cada uno: faltan campos obligatorios; el de sujeto excluido usa `sujetoExcluido` donde el esquema v2 pide `receptor`). Sirven para entender la forma de cada documento, no como fixtures de parser ni como referencia de campos: manda el esquema oficial.
- `docs/FESVDGIIMH_GuiaIntegracionFacturaElectronicasSV.pdf`: lineamientos de integración de la DGII, v8.0 (2021-09). Trata la firma, los servicios de recepción y consulta y los procesos de contingencia y anulación. No cubre libros de compras. Es útil para una tarea futura: un DTE recibido puede **anularse después de su ingesta** (evento de invalidación); hay que decidir cómo se refleja en los borradores.

### Tareas

- [ ] Generar un `.xlsx` desde una copia de la plantilla (hoja `LibroCompras` únicamente), con los datos de cabecera, una fila por borrador de CCF, la fila de TOTAL y la línea de firma, conservando formato, combinaciones y anchos.
- [ ] Importes exactos (`Decimal`), mapeo y fórmula de TOTAL COMPRAS según las tablas anteriores, y signo por tipo mediante función pura.
- [ ] Mismos permisos que la vista previa más el permiso de exportación; botón de descarga en el reporte de Desk; pruebas y verificación del archivo generado.

### Fuera de alcance

Notas de crédito y débito (KF-06), sujeto excluido (KF-07), importaciones e internaciones, clasificación contable, libros de ventas y diario mayor, y la anulación de DTE ya ingestados.

## Después de la vista previa

La exportación a Excel es KF-05 (arriba) y distingue el **subtotal de CCF** (`TOTAL COMPRAS = SUM(G:M)`: exentas + gravadas + crédito fiscal, la columna R de la plantilla; distinto de `monto_total_operacion` y de `total_pagar`, y sin percibido, retenido ni contribución especial) del **total general del período**. Las notas de crédito y débito (KF-06) y el sujeto excluido (KF-07) se incorporan por tipo, con su esquema y pruebas, usando la matriz de signos de KF-05 y las demás hojas de la plantilla como referencia. La salida de KF-04 y KF-05 es una herramienta de revisión de borradores.

## Mensaje para el nuevo chat de Claude

> Lee AGENTS.md (incluida «Equipo y modelos»), CLAUDE.md, docs/CONTEXTO_ACTUAL.md, docs/ARRANQUE.md y docs/encargos/KF-06.md y KF-06-2.md. Verifica la rama y el árbol de trabajo. KF-05 está hecha y commiteada (`5a674bf`). KF-06.1 (ingesta de notas 05 y 06) está entregada en su iteración 2, sin commit y sin la doble revisión: sigue «Pendiente para la próxima sesión» del tablero.
