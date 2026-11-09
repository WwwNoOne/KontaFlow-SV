# Tablero de KontaFlow SV

Lee primero el [contexto actual](CONTEXTO_ACTUAL.md). Usa [Cordinacion.md](Cordinacion.md) para entregas, preguntas y resultados de revisión. Las rondas de KF-01 a KF-03 están en el [historial](HISTORIAL_KF01_KF03.md).

## Tareas

| ID | Responsable | Estado | Entrega |
| --- | --- | --- | --- |
| KF-01 / KF-01-R | Claude / Codex | Hecha | Entorno local y app base sobre Frappe y ERPNext. |
| KF-02 / KF-02-R | Claude / Codex | Hecha | Ingesta de CCF v3 en borrador. |
| KF-03 / KF-03-R | Claude / Codex | Hecha | Ingesta de CCF v4 y convivencia con v3. El mismo código en otra versión de la misma empresa reporta conflicto y conserva el primer borrador. |
| KF-04.1 | Claude | Lista para iniciar | Consulta de borradores por empresa y mes con permisos y orden estable. |
| KF-04.2 | Claude | Pendiente de KF-04.1 | Filas, advertencias y totales exactos para la vista previa. |
| KF-04.3 | Claude | Pendiente de KF-04.2 | Reporte en Frappe Desk con filtros, totales y enlace al borrador. |
| KF-04-R | Codex | Pendiente de KF-04.3 | Revisar permisos, fechas, montos y el flujo completo en Desk. |

Estados de trabajo: **Lista para iniciar**, **En curso**, **En revisión**, **Bloqueada** y **Hecha**. Si una tarea depende de otra, habilítala cuando su dependencia quede cerrada. Cada entrega registra la base de Git, los archivos y las verificaciones en [Cordinacion.md](Cordinacion.md).

## KF-04 · Vista previa del Libro de Compras

### KF-04.1 · Consulta y permisos

- [ ] Consultar `KontaFlow DTE Compra` en estado **Borrador**, con una empresa y un mes obligatorios. Usar `fecha_emision` desde el primer día del mes hasta el primer día del mes siguiente, excluido. Incluir CCF v3 y v4.
- [ ] Aplicar los permisos del usuario sobre la empresa y los DTE. Ordenar por fecha de emisión y usar el nombre del documento para desempatar.
- [ ] Probar con datos ficticios los límites del mes, un período vacío, un mes inválido y el aislamiento entre dos empresas. Verificar que un usuario autorizado vea su empresa y que una empresa ajena produzca un error de permiso.

### KF-04.2 · Filas y totales

- [ ] Proyectar una fila por DTE con fecha de emisión, proveedor, NIT del emisor, número de control, montos gravados, exentos y no sujetos, IVA, advertencias e identificador del borrador.
- [ ] Sumar las cuatro columnas monetarias con aritmética decimal sobre todos los borradores autorizados del período. Usar los importes ya guardados en el DTE. Conservar las advertencias de cada fila.
- [ ] Probar importes fraccionarios, una fila con advertencia y un período vacío. Comparar las sumas con el detalle para detectar duplicados y errores de precisión.

### KF-04.3 · Reporte en Frappe Desk

- [ ] Exponer la consulta como reporte de lectura con filtros obligatorios de empresa y mes. Mostrar el título **Vista previa del Libro de Compras**, las filas y los totales.
- [ ] Enlazar cada fila al borrador correspondiente mediante un enlace de Frappe. Mantener los controles de permisos también al ejecutar el reporte directamente.
- [ ] Verificar desde Desk los filtros, las advertencias, el caso sin resultados y el enlace. Dejar instrucciones para repetir el flujo con datos ficticios.

### KF-04-R · Revisión independiente

- [ ] Comparar los totales con los borradores de prueba y repetir los casos de fechas, permisos y aislamiento. Verificar que el enlace abra el registro correcto y que el reporte solo lea datos.
- [ ] Ejecutar las pruebas de KF-04 y la regresión de ingesta v3/v4 en el sitio de desarrollo. Registrar comandos, resultados y limitaciones en [Cordinacion.md](Cordinacion.md).

## Después de la vista previa

La exportación a Excel será una entrega separada. La incorporación de notas de crédito, notas de débito y documentos de sujeto excluido se planificará por tipo, con su esquema y pruebas. La salida de KF-04 es una herramienta de revisión de borradores.

## Mensaje para el nuevo chat de Claude

> Lee AGENTS.md, docs/CONTEXTO_ACTUAL.md, docs/ARRANQUE.md y la sección «Para Claude» de docs/Cordinacion.md. Verifica la rama y el árbol de trabajo antes de editar. Toma solo KF-04.1, registra las rutas previstas y deja pruebas y comandos para Codex. KF-03 ya está commiteada en `feature_claude` (sin push), así que el árbol debería estar limpio al empezar: si no lo está, averigua de quién es el cambio antes de tocarlo. Mantén las demás subtareas pendientes.
