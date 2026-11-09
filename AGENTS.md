# Instrucciones compartidas de KontaFlow SV

Lee [README.md](README.md), [Project_Context.md](Project_Context.md) y [docs/ARRANQUE.md](docs/ARRANQUE.md). El contexto describe la visión del producto y el tablero indica el alcance de cada tarea y qué decisiones quedan abiertas.

## Responsabilidades

- **Claude Code** implementa la tarea asignada, añade las pruebas del comportamiento nuevo y deja el cambio listo para revisión.
- **Codex** revisa el cambio de forma independiente y ejecuta las verificaciones pertinentes. En la primera revisión trabaja en modo lectura. Aplica correcciones cuando se las encarguen.

## Cambios y seguridad

- Trabaja desde la raíz de este repositorio. Inspecciona `git status --short --branch --untracked-files=all`, los cambios existentes y los archivos de la tarea antes de editar. Preserva el trabajo del usuario y de la otra sesión.
- Mantén cambios pequeños y reversibles. Conserva la arquitectura y las interfaces públicas salvo autorización. Justifica cada dependencia nueva y respeta la versión de Python acordada para el entorno.
- Usa las herramientas de pruebas y lint configuradas. Si faltan, registra la limitación. Conserva las pruebas existentes y verifica los comandos que cites en la entrega.
- Usa datos ficticios. Protege secretos, credenciales, archivos `.env` y documentos reales de clientes. Evita migraciones destructivas. Los commits y pushes requieren autorización.
- Mantén ERPNext y Oculus como repositorios de referencia. Usa los mecanismos de extensión de Frappe para la app propia y verifica el comportamiento de Oculus antes de adaptar ideas de su ingesta.

## Coordinación

1. Antes de editar, registra en el [tablero](docs/ARRANQUE.md) el ID de la tarea, responsable, estado y rutas previstas. Una sola sesión escribe en una misma ruta a la vez. En la copia de trabajo compartida, Claude implementa y Codex revisa la entrega cuando quede estable.
2. Al entregar, indica el ID, referencia base (`git rev-parse --short HEAD`), archivos modificados y nuevos, comandos y resultados, decisiones y pendientes. Identifica los archivos nuevos explícitamente, porque un diff por sí solo los omite. Marca la tarea **En revisión**.
3. Codex revisa archivos y diff respecto de la base indicada, incluidos los archivos nuevos. Prioriza bugs, regresiones, seguridad, aislamiento entre empresas, casos límite, precisión de importes y pruebas faltantes. Reporta severidad, archivo y línea, impacto y verificaciones ejecutadas.
4. Tras la revisión, devuelve los hallazgos al responsable o registra la aprobación y la verificación. Marca **Hecha** cuando se cumplan los criterios de cierre. Si el entorno impide una verificación requerida, registra el bloqueo y deja la tarea abierta.
