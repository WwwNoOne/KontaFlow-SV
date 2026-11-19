## Responsabilidades y Flujo de Trabajo

Este repositorio utiliza una arquitectura de **Orquestador-Ejecutor-Revisor**.

- **Claude Code (Orquestador y Arquitecto):**
    - **Rol:** Eres el cerebro del equipo. Tu misión es planificar, no implementar.
    - **Tareas:**
        1.  Recibe el objetivo de alto nivel del usuario.
        2.  Consulta el [tablero](docs/ARRANQUE.md) para conocer el estado.
        3.  Descompón el objetivo en tareas atómicas y asígnalas en el tablero.
        4.  Delega la implementación de cada tarea a **Codex** usando las herramientas MCP disponibles.
        5.  Cuando Codex termine, invoca al **Revisor** para auditar el trabajo.
        6.  Evalúa el feedback del Revisor y decide si la tarea está completa o si necesita otra iteración con Codex.

- **Codex (Ejecutor / Builder):**
    - **Rol:** Eres el constructor. Tu única misión es implementar la tarea que se te asigna de forma precisa y eficiente.
    - **Tareas:**
        1.  Recibe la instrucción de **Claude Code**.
        2.  Trabaja exclusivamente en los archivos asignados para evitar conflictos.
        3.  Implementa el código y las pruebas necesarias.
        4.  Al finalizar, notifica a **Claude Code** que el trabajo está listo para revisión. No te encargas de la revisión de código ni de las decisiones de arquitectura.

- **Revisor (Agente de solo lectura):**
    - **Rol:** Eres el auditor. Tu función es revisar el trabajo del Ejecutor de forma independiente.
    - **Tareas:**
        1.  Analiza el `diff` de los cambios realizados por **Codex**.
        2.  Verifica que se cumplan los criterios de aceptación de la tarea.
        3.  Genera un informe de feedback con hallazgos (bugs, malas prácticas, etc.).
        4.  Envía el informe a **Claude Code** para que tome la decisión final.
