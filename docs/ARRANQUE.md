# Tablero de KontaFlow SV

Lee primero el [contexto actual](CONTEXTO_ACTUAL.md). Usa [Cordinacion.md](Cordinacion.md) para entregas, preguntas y resultados de revisión. Las rondas de KF-01 a KF-03 están en el [historial](HISTORIAL_KF01_KF03.md).

## Ubicación del código (actualizado el 2026-11-19)

- `main` (esta carpeta) avanzó por fast-forward hasta `7f165d2` e incluye la app `kontaflow_sv` completa (KF-01 a KF-04.3). Antes solo tenía la documentación inicial (`10032fe`). No se ha hecho push: `main` va por delante de `origin/main`.
- Los worktrees siguen en `~/.claudette/workspaces/KontaFlow-SV/`. El bench (`~/frappe-kf/kf-bench`) carga la app desde `vivid-delphinium` (rama `claudette/kf-04-2-docs-review`, mismo código que `main`) mediante un symlink y `kontaflow_sv.pth`. Para que el bench use esta carpeta hay que actualizar ambos y verificarlo con `env/bin/python -c 'import kontaflow_sv;print(kontaflow_sv.__file__)'`. Es un cambio compartido y requiere autorización.
- Roles vigentes (los de [AGENTS.md](../AGENTS.md), aún sin commitear en `main`): Claude orquesta y planifica, Codex implementa y un revisor de solo lectura audita. KF-01 a KF-04.2 se hicieron con el esquema anterior (Claude implementaba y Codex revisaba).

## Tareas

| ID | Responsable | Estado | Entrega |
| --- | --- | --- | --- |
| KF-01 / KF-01-R | Claude / Codex | Hecha | Entorno local y app base sobre Frappe y ERPNext. |
| KF-02 / KF-02-R | Claude / Codex | Hecha | Ingesta de CCF v3 en borrador. |
| KF-03 / KF-03-R | Claude / Codex | Hecha | Ingesta de CCF v4 y convivencia con v3. El mismo código en otra versión de la misma empresa reporta conflicto y conserva el primer borrador. |
| KF-04.1 | Claude | Hecha (aprobada por la persona responsable el 2026-11-09; Codex la cubre en KF-04-R) | Consulta de borradores por empresa y mes con permisos y orden estable: `kontaflow_sv/libro_compras/consulta.py`. |
| KF-04.2 | Claude | Hecha | Filas, advertencias y totales exactos para la vista previa: `kontaflow_sv/libro_compras/vista_previa.py`. Revisada por Codex en `668659f`. |
| KF-04.3 | Codex (ejecutor) | Hecha (commit `7f165d2`; dos revisiones sin defectos y suite completa en verde el 2026-11-19) | Reporte en Frappe Desk con filtros, totales y enlace al borrador: `kontaflow_sv/kontaflow_sv/report/vista_previa_del_libro_de_compras/` y `kontaflow_sv/tests/test_libro_compras_reporte.py`. |
| KF-05 | Codex (ejecutor) | Lista para iniciar | Exportación a Excel del Libro de Compras de CCF con la distribución de columnas de Oculus. Ver «KF-05». |
| KF-05-R | Revisor | Pendiente de KF-05 | Revisar columnas, signos, totales exactos, permisos y el archivo generado. |
| KF-06 / KF-07 | Claude (planifica) | Planificadas, sin encargo | KF-06: ingesta de notas de crédito (05) y débito (06), con los signos de abajo. KF-07: sujeto excluido (14). Cada una con su esquema y pruebas. |
| KF-04-R | Revisor | En revisión (condición abierta) | Falta el recorrido en Desk real, con el asistente de configuración completado. El resto está verificado (ver «Revisión»). |

Estados de trabajo: **Lista para iniciar**, **En curso**, **En revisión**, **Bloqueada** y **Hecha**. Si una tarea depende de otra, habilítala cuando su dependencia quede cerrada. Cada entrega registra la base de Git, los archivos y las verificaciones en [Cordinacion.md](Cordinacion.md).

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
- [ ] Ejecutar las pruebas de KF-04 y la regresión de ingesta v3/v4 en el sitio de desarrollo. Registrar comandos, resultados y limitaciones en [Cordinacion.md](Cordinacion.md).

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

## KF-05 · Exportación a Excel del Libro de Compras

Plantilla de referencia: la de Oculus. **No hay un `.xlsx` de plantilla en el repositorio de Oculus**: la plantilla es la distribución de 24 columnas y la lógica de signos de `Oculus/src/backend/services/excel_service.py` (`ExcelService.columns` y `_fila_desde_data`), verificadas el 2026-11-19. Códigos de tipo según el catálogo CAT-002 de Hacienda (`esquemas/`): **05 = Nota de crédito, 06 = Nota de débito** (el orden de `Project_Context.md` está invertido).

### Matriz de signos (de Oculus)

| Tipo | Documento | Signo | Columnas que Oculus llena |
| --- | --- | --- | --- |
| 03 | Comprobante de crédito fiscal | positivo | Gravadas internas, Crédito fiscal, IVA percibido, Retenido, TOTAL Compras |
| 05 | Nota de crédito | **negativo**: Oculus invierte Gravadas, Crédito fiscal, IVA percibido, Retenido, FOVIAL/COTRANS/CESC y TOTAL Compras | Las mismas que el 03, con signo invertido |
| 06 | Nota de débito | positivo (igual que el 03) | Las mismas que el 03 |
| 14 | Factura de sujeto excluido | positivo | «Compras a Sujetos Excluidos»; Gravadas y Crédito fiscal en 0; TOTAL Compras = subtotal − retenido |

KF-05 solo exporta el tipo **03**, el único que se ingesta hoy. Los signos de 05, 06 y 14 quedan fijados aquí para KF-06 y KF-07, no se implementan todavía. La exportación debe fallar de forma explícita ante un tipo sin regla de signo, nunca omitirlo ni exportarlo con signo positivo.

### Diferencias con Oculus que no se copian

- Oculus usa `float`; KontaFlow usa `Decimal` y el importe guardado.
- Oculus recalcula el crédito fiscal como 13 % de la base; KontaFlow usa el **IVA guardado en el DTE** (la advertencia de ingesta ya controla el 13 %).
- Oculus deja vacías las columnas de compras exentas y no sujetas; KontaFlow las llena con `total_exenta` y `total_no_suj`.
- Oculus descarta en silencio lo que no es 03/05/06/14; KontaFlow ya consulta solo CCF y falla ante tipos sin regla.

### Tareas

- [ ] Exportar a `.xlsx` los borradores de CCF de una empresa y un mes, con las 24 columnas de Oculus, en su orden y con sus títulos literales, mapeadas como indica la nota «KF-05 · Exportación a Excel» de [Cordinacion.md](Cordinacion.md).
- [ ] Importes exactos (`Decimal`, sin `float`), signos según la matriz y, al final, una fila de totales por columna, el **Subtotal CCF** y el **Total general del período**, calculados por separado aunque hoy coincidan.
- [ ] Mismos permisos que la vista previa más el permiso de exportación; botón de descarga en el reporte de Desk; pruebas y verificación del archivo generado.

### Fuera de alcance

Notas de crédito y débito, sujeto excluido, importaciones, clasificación contable, correlativo fiscal oficial, PDF y carpeta de entrega como la de Oculus.

## Después de la vista previa

La exportación a Excel es KF-05 (arriba) y distingue el **subtotal de CCF** (compras gravadas + IVA, la columna «TOTAL Compras» de la plantilla, distinta de `monto_total_operacion` y de `total_pagar`) del **total general del período**. Las notas de crédito y débito (KF-06) y el sujeto excluido (KF-07) se incorporan por tipo, con su esquema y pruebas, usando la matriz de signos de KF-05. La salida de KF-04 y KF-05 es una herramienta de revisión de borradores.

## Mensaje para el nuevo chat de Claude

> Lee AGENTS.md, CLAUDE.md, docs/CONTEXTO_ACTUAL.md, docs/ARRANQUE.md y la sección «Para Codex» de docs/Cordinacion.md. Verifica la rama y el árbol de trabajo. KF-04.3 está hecha y queda la condición abierta de KF-04-R (recorrido en Desk con el asistente completado). Delega KF-05 a Codex con el encargo de «Para Codex» en docs/Cordinacion.md, y cuando termine pide la revisión KF-05-R al revisor.
