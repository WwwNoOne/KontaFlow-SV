# Especificación Técnica de Arquitectura: KontaFlow SV

**Sistema de Automatización Contable Multi-Empresa con IA y DTE (El Salvador)**  
**Versión:** 1.0.0  
**Plataforma Base:** ERPNext / Frappe Framework  
**Motor Contable:** Partida Doble Determinista + Aprendizaje Aumentado por IA  

---
#0.1 arquitectura del carpetas (INICIALES)
Carpetas
erpnext /Freppe Fremework
Oculus /lector de json y pdf genera los libros de compras pero tiene los siguientes detalles en la version actual con las api nesecita renovarse en la lectura de pdf a veces alusinan o las ia devuelven json vacio,si hay compras con dte fisico y no estan en el correo esas faltaran
KontaFlow-SV /carpeta principal del proyecto
KF_Workspace /carpeta general
#   arquitectura de carpeta KontaFlow_SV:
-Readme
-
# Oculus
esta es una aplicacion aparte creada por mi su funcion es descargar documentos adjuntos  PDF y json luego pasar !solo las compras!  para crear los libros de compra su codigo y arquitectura se puede usar de base para la injesta solo de compras 
# Entrada
Detalle de Entradas de Documentos al Sistema1. Ventas e Ingresos (Documentos Emitidos)Formatos: JSON DTE, CSV, XLSX, TXT.Costo de IA: $0.00 (Procesamiento por código).Documentos Específicos:JSON DTE Tipo 01 (Factura): Ventas directas a consumidor final.JSON DTE Tipo 03 (Comprobante de Crédito Fiscal - CCF): Ventas a otros contribuyentes de IVA (registra el Débito Fiscal del 13%).JSON DTE Tipo 05 / 06 (Notas de Débito / Crédito): Ajustes, devoluciones o anulaciones sobre ventas previas.JSON DTE Tipo 11 (Factura de Exportación): Ventas fuera del territorio nacional (tasa 0% IVA).CSV / XLSX de Ventas (Reportes POS): Cierre diario de cajas registradoras, reportes de pasarelas de pago (BAC, Wompi, etc.) o resúmenes del Libro de Ventas a Consumidor Final.2. Compras y Gastos (Documentos Recibidos)Formatos: JSON DTE, PDF con texto, PDF escaneado (Imagen), JPG/PNG.Costo de IA: $0.00 para JSON y PDF texto; ~$0.00015 USD solo para PDFs escaneados o imágenes procesados por Visión.Documentos Específicos:JSON DTE Tipo 03 (CCF Recibido): Compras y servicios prestados por proveedores contribuyentes (registra el Crédito Fiscal 13%).JSON DTE Tipo 14 (Sujeto Excluido): Empleado cuando la empresa le compra o contrata servicios a una persona natural no inscrita en IVA.PDF DTE Recibidos (Vía correo): Representación gráfica de los DTEs enviado por proveedores (se intenta extraer texto nativo primero; si es imagen pura, pasa a OCR por IA).Facturas Físicas / Tiquetes / Caja Chica (Fotos / Escaneos): Comprobantes impresos de gastos menores o gasolina no digitalizados en DTE.Pólizas de Importación (Declaración de Mercancías - DM / DUA): Documentos de aduana para liquidar el IVA de importación, el Derecho Arancelario a la Importación (DAI) y cargos portuarios (CEPA).3. Tesorería y Bancos (Movimientos Monetarios)Formatos: CSV, XLSX, OFX, TXT, PDF.Costo de IA: $0.00 para ingesta; ~$0.00005 USD en emparejamientos semánticos complejos de conciliación.Documentos Específicos:Extractos Bancarios (CSV / XLSX / OFX): Histórico mensual descargado de las bancas de personas/empresas (BAC Credomatic, Banco CUSCATLAN, Banco Agrícola, Davivienda, etc.).Comprobantes de Pago / Vouchers (PDF / PNG): Capturas de transferencias interbancarias (Transfer365), comprobantes de remesas o depósitos en ventanilla.4. Nómina y Recargos Patronales (Costos de Personal)Formatos: CSV, XLSX, TXT, PDF.Costo de IA: $0.00 (Cálculo determinista legal).Documentos Específicos:Planilla Mensual de Sueldos (Excel / CSV): Reporte de salarios base, horas extra, comisiones, incapacidades e indemnizaciones.Planilla Única ISSS / AFP (PDF / TXT): Archivos de pago de cotizaciones de salud y previsionales para validar el cálculo de aportes patronales (ISSS 7.5%, AFP 8.75%) y retenciones de empleados.5. Documentos de Configuración y CierreFormatos: CSV, XLSX.Costo de IA: $0.00.Documentos Específicos:Catálogo de Cuentas Inicial: Estructura de cuentas de la empresa (NIIF para PYMES) al darla de alta en ERPNext.Balanza de Saldos Iniciales: Saldos de apertura del ejercicio contable.Matriz Resumida de Entrada de RecursosCategoríaFormato PrimarioProcesadorImpacto en API de IAVentas DTE / POSJSON / CSV / XLSXParser PythonNinguno ($0.00)Compras JSON DTEJSONParser PythonNinguno ($0.00)Compras PDF TextoPDF nativoPython (pdfplumber)Ninguno ($0.00)Compras PDF EscaneadoImagen / PDF scanAPI Visión (Gemini/OpenAI)Mínimo (~$0.00015)Extractos BancariosCSV / XLSX / OFXImporter + Rule MatchCasi Nulo ($0.00)Planillas de SueldosXLSX / CSVMotor de NóminaNinguno ($0.00)
## 1. Visión General del Sistema

**KontaFlow SV** es una plataforma de contabilidad automatizada diseñada para el marco fiscal y legal de El Salvador. se encarga de todo el ciclo contable compras,ventas.estado bancarios,planillas ,inventario,Activos,depreciacion,amortizacion,libros fiscales,estados financieros

---

## 2. Arquitectura General del Sistema

```text
[ Fuentes de Entrada ]
 ├── JSON DTE (Hacienda SV) ──┐
 ├── PDF Escaneados (OCR) ────┼──► [ Ingesta & Parser Local ] ──► [ Motor de Reglas & Caché ]
 └── Extractos Bancarios ─────┘                                                │
                                                                               ├─► (Match Exitoso) ──► ERPNext Engine
                                                                               │                         (Auto-Post)
                                                                               └─► (No Encontrado) ──► [ Capa de IA ]
                                                                                                           │
                                                                                                           ▼
                                                                                                  [ Dashboard HITL ]
                                                                                                  (Revisión Humana)
```

### Componentes de la Arquitectura

1. **Capa de Ingesta (Local / Serverless):**
   * **JSON Parser:** Extrae campos de DTEs de El Salvador sin consumir IA.
   * **PDF Vision Parser:** Procesa facturas físicas mediante modelos de visión económica (Gemini Flash / GPT-4o mini).
2. **Capa de Negocio y ERP (ERPNext / Frappe Custom App):**
   * Contabilidad general de partida doble ($Debe = Haber$).
   * Catálogo de Cuentas estándar (NIIF para PYMES) adaptable por empresa.
   * Gestión de impuestos específicos salvadoreños (IVA 13%, FOVIAL $0.20, COTRANS $0.10, Retención 1% IVA, Retención 10% Renta).
3. **Capa de Aprendizaje (Caché de Reglas Contables):**
   * Base de conocimiento jerárquica que aprende de cada corrección o aprobación realizada por el contador.
4. **Capa de IA (Auditoría, Conciliación y RAG Fiscal):**
   * Asignación de cuentas contables ambiguas.
   * Conciliación inteligente de transacciones bancarias.
   * RAG sobre el Código Tributario y Ley del Impuesto sobre la Renta SV.
5. **Interfaz Human-in-the-Loop (HITL):**
   * Panel de control para el contador con semáforo de aprobación (Verde = Automático, Amarillo = Sugerencia de IA, Rojo = Requiere Atención).

---

## 3. Estrategia de Ingesta y Almacenamiento

### 3.1 Separación de Archivos y Metadatos
* **Storage de Archivos (S3 / Local Vault):**  
  Ruta: `storage/{nit_empresa}/{año}/{mes}/{tipo_operacion}/{json|pdf}/{codigoGeneracion}.{ext}`
* **Base de Datos Relacional (PostgreSQL / MariaDB):**  
  Almacena metadatos extraídos, referencias contables y rutas de archivo.

### 3.2 Manejo del `codigoGeneracion`
El `codigoGeneracion` (UUID) es la clave primaria única. Todo documento procesado verifica primero su existencia en la base de datos para garantizar **idempotencia** (prevenir duplicación de facturas).

---

## 4. Sistema de Aprendizaje Contable (3 Capas)

Para minimizar llamadas a la API de IA, el sistema procesa cada transacción bajo la siguiente cascada de resolución:

```text
[ Transacción Entrada ]
        │
        ├── Capa 1: Match Exacto (NIT + Patrón de Ítem) ──────► Asiento Directo (Costo $0)
        │
        ├── Capa 2: Historial Aprobado por Empresa ────────────► Asiento Sugerido (Costo $0)
        │
        └── Capa 3: API de IA con JSON Structured Output ──────► Clasificación por IA (Costo ~$0.0001)
                                                                         │
                                                                         ▼
                                                                [ Registro en Caché ]
```

### DocType Personalizado: `KontaFlow Rule Cache`
* **`empresa_nit`**: NIT de la empresa receptora.
* **`tercero_nit`**: NIT del emisor (proveedor/proveedor de servicio).
* **`patron_texto`**: Expresión o palabra clave (`PREMIUM95`, `HONORARIOS`, etc.).
* **`cuenta_debito`**: Código de la cuenta de gasto/inventario en ERPNext.
* **`cuenta_credito`**: Código de la cuenta de pasivo/bancos.
* **`aplica_fovial`**: Booleano.
* **`aplica_cotrans`**: Booleano.
* **`veces_aplicado`**: Contador de ejecuciones.

---

## 5. Módulos del Ciclo Contable Integral

El sistema cubre la contabilidad completa dividida en módulos de software y automatización:

| Módulo | Fuente de Datos | Nivel de Automatización | Función de la IA |
| :--- | :--- | :--- | :--- |
| **Libro de Compras IVA** | JSON DTE (`03`, `05`, `14`) | 100% Automático | Ninguna (Parseo puro de tributos: IVA, FOVIAL, COTRANS). |
| **Libro de Ventas IVA** | JSON DTE (`01`, `03`) | 100% Automático | Ninguna (Generación automática de asientos de ingresos). |
| **Cuentas por Pagar** | Compras / Recibos Sujeto Excluido | 95% Automático | Asignación de cuenta de gasto para ítems desconocidos. |
| **Conciliación Bancaria** | Extracto Bancario (CSV/OFX) | 85% Automático | Emparejamiento semántico entre descripción del banco y facturas pendientes. |
| **Control de Inventarios** | DTEs + Kardex ERPNext | 90% Automático | Mapeo de códigos de proveedor a catálogo de ítems interno. |
| **Planilla y Sueldos** | Módulo de Nómina SV | 100% Determinista | Cálculo estricto de ISSS, AFP y Retención de Renta. |
| **Depreciación Activos** | Tablas de Amortización SV | 100% Determinista | Cálculo según art. 30 Ley del Impuesto sobre la Renta SV. |
| **Estados Financieros** | Saldos de Cuentas ERPNext | 100% Determinista | Ensamblaje automático del Balance General y Estado de Resultados. |
| **Auditoría & Cierre** | Libro Mayor + Leyes SV | Asistido por IA | Análisis RAG de inconsistencias y deducibilidad de gastos. |

---

## 6. Selección de Modelos de IA y Estructura Financiera

### 6.1 Matriz de Modelos Seleccionados //en proceso se concideran mas modelos  y se busca recomendaciones para futuroS

1. **Extracción Visión/OCR (Facturas PDF/Impresas):**  
   * **Modelo:** `gemini-1.5-flash` / `gpt-4o-mini`  
   * **Configuración:** `temperature=0.0`, `response_format={"type": "json_object"}`  
   * **Propósito:** Convertir imágenes/PDFs a estructura de datos DTE.
2. **Clasificación Contable Semántica (Excepciones):**  
   * **Modelo:** `gpt-4o-mini` / `gemini-1.5-flash`  
   * **Configuración:** Structured Outputs con Zod / Pydantic.  
   * **Propósito:** Asignar catálogo de cuentas según descripción de bienes o servicios.
3. **Auditoría Fiscal & Consultas Complejas:**  
   * **Modelo:** `deepseek-chat` (DeepSeek V3)  
   * **Configuración:** RAG con embeddings de normas salvadoreñas.  
   * **Propósito:** Analizar la deducibilidad de costos y generar notas explicativas a estados financieros.

### 6.2 Estimación Económica para Presupuesto de $300 USD / mes

* **Costo promedio por documento parseado por IA:** $\approx \$0.00015\text{ USD}$
* **Costo promedio por documento en caché/código:** $\$0.00000\text{ USD}$
* **Costo medio ponderado por transacción contable:** $\approx \$0.00005\text{ USD}$

Con este perfil de costos, un presupuesto de **$300 USD/mes** permite procesar hasta **6,000,000 de transacciones contables mensuales**, equivalentes a dar servicio completo a **más de 50 empresas medianas** o **más de 400 pequeñas empresas**.

---

## 7. Mapeo del Estado de Resultados para la IA

ERPNext expone la estructura del Estado de Resultados en un objeto JSON ligero para que la IA tome decisiones contextuales sin leer todo el sistema:

```json
{
  "empresa_nit": "13271603261014",
  "catalogo_gastos": [
    { "codigo": "510101", "nombre": "Materia Prima", "categoria": "Costo de Ventas" },
    { "codigo": "520101", "nombre": "Combustibles y Lubricantes", "categoria": "Gastos de Administración" },
    { "codigo": "520102", "nombre": "Honorarios Profesionales", "categoria": "Gastos de Administración" },
    { "codigo": "520103", "nombre": "Atenciones al Personal", "categoria": "Gastos de Ventas" }
  ]
}
```

---

## 8. Roadmap de Implementación

```text
Fase 1: Infraestructura Base (Semanas 1-2)
 ├── Instalación de Frappe / ERPNext en servidor VPS.
 ├── Creación de la Custom App: `kontaflow_sv`.
 └── Definición de esquemas de Base de Datos y DocTypes para DTE y Caché.
 . Desarrollo Local (Recomendado para arrancar)
Puedes instalar la arquitectura de Frappe / ERPNext directamente en tu equipo (vía Linux nativo o WSL2 en Windows) usando Frappe Bench o Docker (bench-docker).

Ventaja: Desarrollas la Custom App kontaflow_sv, los DocTypes para DTE, los parsers JSON y la integración con la API de Gemini Flash sin incurrir en costos de hosting.

Flujo: C app local con bench new-app kontaflow_sv, trabajas en local subir avances a un repositorio de GitHub.

Fase 2: Motor DTE & Libros de IVA (Semanas 3-4)
 ├── Parser local de JSON DTE (Facturas, CCF, Sujeto Excluido).
 ├── Cálculo determinista de impuestos (IVA, FOVIAL, COTRANS, Retención 1%).
 └── Generador automático de Libros de Compras y Ventas de IVA en Excel/PDF.

Fase 3: Integración de IA & Motor de Partidas (Semanas 5-6)
 ├── Módulo de clasificación en 3 capas (Caché + Historial + IA).
 ├── Integración con API de Gemini Flash / OpenAI con Structured Outputs.
 └── Hook de auto-aprendizaje en ERPNext (`on_submit` de facturas).

Fase 4: Conciliación Bancaria y Módulos Avanzados (Semanas 7-8)
 ├── Importador de extractos bancarios CSV.
 ├── Algoritmo de emparejamiento semántico de depósitos/pagos con IA.
 └── Tablero HITL para revisión del contador.

Fase 5: Pruebas de Escalabilidad y Despliegue (Semanas 9-10)
 ├── Carga masiva de DTEs de prueba para 4 empresas piloto.
 ├── Optimización de tiempos de respuesta e índices PostgreSQL.
 └── Despliegue final en producción.
```

Otros detalles: 
1. Estructura del Catálogo de Cuentas en ERPNext (Account DocType)Para permitir tanto la contabilización automática mediante IA como el registro manual por parte del usuario, el catálogo de cuentas se mapea en la estructura de ERPNext bajo cuatro atributos fundamentales:Clasificación GeneralTipo de Raíz (root_type)Naturaleza ContableEstado Financiero (report_type)Ejemplos de CuentasActivoAssetDeudoraEstado de Situación FinancieraCaja y Bancos, Cuentas por Cobrar, Inventarios, IVA Crédito FiscalPasivoLiabilityAcreedoraEstado de Situación FinancieraProveedores, Retenciones de Ley (ISSS/AFP/ISR), IVA Débito FiscalPatrimonioEquityAcreedoraEstado de Situación FinancieraCapital Social, Reservas Legales, Utilidades AcumuladasIngresosIncomeAcreedoraEstado de ResultadosVentas Locales Gravadas, Exportaciones, Servicios PrestadosCostosExpense (Subclase Costos)DeudoraEstado de ResultadosCosto de Ventas, Compras de Mercadería, Materia PrimaGastosExpenseDeudoraEstado de ResultadosGastos de Administración, Gastos de Ventas, Gastos FinancierosAtributos Clave en la Aplicación kontaflow_svCuentas Transitivas / Puente: Se debe definir una cuenta específica como Gastos por Clasificar (Activo/Gasto transitorio) para registrar partidas donde la IA no alcance el umbral mínimo de confianza.Bandera de Automatización (is_ai_selectable): Campo personalizado (Custom Field) en el DocType Account para indicar si una cuenta puede ser asignada automáticamente por el motor de clasificación o requiere autorización manual (ej. cuentas de Patrimonio o Capital).2. Flujo de Trabajo Inteligente: IA vs. Intervención Humana (HITL)Para evitar duplicidad de trabajo, partidas dobles o sobreescritura de datos, el flujo debe regirse por un sistema de Ciclo de Vida del Documento con estados estrictos y bloqueos a nivel de base de datos (docstatus en ERPNext).[DTE Entrada / JSON] ➔ [Validación Unicidad] ➔ [Motor Determinista (Impuestos)] ➔ [Motor IA (Clasificación)]
                                                                                       │
┌──────────────────────────────────────────────────────────────────────────────────────┘
▼
[Documento en Estado Borrador (Draft / docstatus=0)]
   ├── Nivel de Confianza ≥ 95% ──> [Auto-Sugerido / Listo para Firma]
   └── Nivel de Confianza < 95% ──> [Requiere Revisión Humana (HITL)]
                                             │
                                             ▼
                               [Confirmación / Edición Manual]
                                             │
                                             ▼
                        [Documento Validado (Submitted / docstatus=1)] ──> [Bloqueo Permanente]
Definición de Estados del FlujoEstado 0: Ingesta y Desduplicación (Sistema Base)El sistema recibe el JSON/PDF del DTE.Se valida la clave única codigo_generacion (UUID de Hacienda) en la base de datos. Si ya existe, la ingesta se rechaza inmediatamente.Estado 1: Procesamiento Automático (IA + Reglas)Parte Determinista (Código Python): Calcula montos de IVA (13%), Retención (1%), FOVIAL, COTRANS o Exentos. La IA nunca calcula números.Parte Inferencial (IA - Gemini Flash / Rules Engine): Analiza el emisor, los ítems del DTE y el historial, sugiriendo la cuenta contable de contrapartida (ej. 520103 - Atenciones al Personal) y asigna un puntaje de confianza (confidence_score).Estado 2: Borrador / En Revisión (docstatus = 0)Se crea la partida o factura en modo Borrador.En este estado, la partida es totalmente modificable por el usuario y no afecta los saldos de los libros mayores ni estados financieros.El tablero HITL muestra las partidas en tres categorías:🟢 Verde (Confianza Alta > 95%): Aprobación a un solo clic o auto-aprobación programada.🟡 Amarillo (Confianza Media 70-94%): Sugerencia de cuenta resaltada para revisión rápida.🔴 Rojo (Confianza Baja / Proveedor Nuevo): Requiere asignación manual por parte del contador.Estado 3: Registrado / Validado (docstatus = 1)El contador presiona "Aprobar" (o guarda una partida manual).El documento pasa a Submitted (docstatus = 1). En este instante, ERPNext bloquea la edición del documento en la base de datos.La IA pierde total acceso de escritura sobre este registro, garantizando que no existan sobreescrituras posteriores.3. Matriz de Inconvenientes Técnicos, Operativos y SolucionesInconveniente / RiesgoCausa RaízSolución Técnica en kontaflow_svDuplicidad por DTEs reingresadosEl proveedor reenvía el correo o se carga el mismo JSON manualmente.Índice único en el DocType Inbound DTE utilizando codigo_generacion + sello_recibido.Alucinación de la IA en montos o fechasLa IA intenta interpretar números en lugar de texto.Restringir el alcance de la IA únicamente al mapeo de la cuenta contable. El total, IVA, retenciones y fechas se extraen directamente de los nodos estructurados del JSON.Conflicto entre Partidas Manuales y AutomáticasUn contador registra manualmente un gasto y luego el sistema procesa el DTE del mismo gasto.Algoritmo de emparejamiento preventivo: Antes de crear un Borrador desde un DTE, buscar partidas manuales o facturas existentes en la misma fecha, por el mismo monto y NTI/NIT del emisor, alertando: "Posible partida manual detectada".Condiciones de Carrera (Sobreescritura en simultáneo)El usuario edita una partida en el dashboard mientras la IA intenta actualizar la sugerencia.Uso del mecanismo nativo de optimismo en ERPNext (modified timestamp check). Si el registro cambió en la BD, la transacción de la IA falla automáticamente.Cambio de Criterio Contable del ClienteLa IA clasifica un ítem como "Suministros de Oficina", pero el contador prefiere "Gastos de Organización".Hook de Aprendizaje (on_submit): Cuando el contador modifica manualmente la cuenta sugerida y aprueba la partida, el sistema guarda una regla en la tabla kontaflow_mapping_cache (Proveedor + Descripción ➔ Cuenta asignada) con prioridad sobre la IA.DTEs de Sujeto Excluido o Retenciones EspecialesEstructuras fiscales no estándar en compras a personas naturales sin IVA.Módulo de validación de esquemas JSON específico por tipoDte (01 Factura, 03 CCF, 05 Nota de Crédito, 14 Sujeto Excluido, 07 Retención).