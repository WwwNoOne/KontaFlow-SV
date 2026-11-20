# Desarrollo local de KontaFlow SV

Guía verificada el 9 de noviembre de 2026 en CachyOS (Arch), sin `sudo` ni contenedores. Todo el entorno vive en `~/frappe-kf/`, **fuera** de este repositorio. El repositorio solo contiene la app `kontaflow_sv`.

> **Soporte oficial.** La documentación de Frappe da soporte a macOS y a Debian 13 / Ubuntu 24.04 o superior. Arch/CachyOS queda fuera de lo oficial. Los requisitos de v17 pueden cambiar mientras siga en desarrollo.

## Versiones verificadas

| Componente | Versión | Requisito documentado (develop / v17) |
| --- | --- | --- |
| Python | 3.14.9 | 3.14 |
| Node | v26.13.0 | 24 o superior |
| yarn | 1.22.22 | 1.22 o superior |
| pip | 26.3 | 25.3 o superior |
| frappe-bench | 5.31.1 | n/d |
| Frappe | 17.0.0.dev0, rama `develop`, `09f83e0` | n/d |
| ERPNext | 17.x.x-develop, rama `develop`, `0d2bc1a` | Frappe `>=17.0.0-dev,<18.0.0` |
| MariaDB | **13.0.2** (paquete de Arch) | **11.8** ⚠️ |
| Valkey (reemplaza a Redis) | 9.1.2 | Redis/Valkey 6 o superior |

⚠️ Frappe avisa al crear el sitio: «MariaDB version 13.0.2 is newer than 11.8 which is not yet tested with Frappe Framework». La instalación y las pruebas mínimas pasaron, pero la combinación no está respaldada. Si aparecen fallos de base de datos, el siguiente paso es MariaDB 11.8 en contenedor (podman), con el resto igual.

## Prerrequisitos

```bash
sudo pacman -S --needed mariadb valkey yarn
```

Python 3.14 y Node 24 o superior ya estaban en el sistema. `uv` no estaba en los repositorios, así que se instala `frappe-bench` con `pip` en un venv. `cronie` tampoco está instalado (ver «Limitaciones»).

## 1. Bench

Revisiones fijadas (las que se probaron en KF-01). `develop` avanza a diario; sin fijar, el resultado puede diferir.

| Pieza | Fijada en |
| --- | --- |
| frappe-bench | `5.31.1` |
| Frappe | `09f83e0730b29f6e35218f97328eeabdf71a1a4a` |
| ERPNext | `0d2bc1a9398eccf8003a851c01e2f2d99e594a01` |

Las revisiones se fijan **antes** de instalar: se preparan dos repositorios locales con una rama `kf-pin` en cada SHA y Bench clona desde ellos. Así nunca se instala nada desde `develop`.

```bash
(
  set -euo pipefail
  ERPNEXT_SRC=/ruta/a/KF_Workspace/erpnext   # checkout local de ERPNext; debe contener el SHA fijado
  FRAPPE_SHA=09f83e0730b29f6e35218f97328eeabdf71a1a4a
  ERPNEXT_SHA=0d2bc1a9398eccf8003a851c01e2f2d99e594a01

  mkdir -p ~/frappe-kf/tools ~/frappe-kf/pins && cd ~/frappe-kf
  python3 -m venv tools/venv
  tools/venv/bin/pip install "frappe-bench==5.31.1"
  export PATH=$HOME/frappe-kf/tools/venv/bin:$PATH
  bench --version   # 5.31.1

  # Repositorios locales fijados (rama kf-pin en la revisión exacta)
  git init -q pins/frappe
  git -C pins/frappe fetch -q --depth 1 https://github.com/frappe/frappe.git "$FRAPPE_SHA"
  git -C pins/frappe checkout -q -b kf-pin FETCH_HEAD
  git clone -q --no-checkout "$ERPNEXT_SRC" pins/erpnext
  git -C pins/erpnext checkout -q -b kf-pin "$ERPNEXT_SHA"

  bench init --frappe-path "$PWD/pins/frappe" --frappe-branch kf-pin --python python3.14 \
    --no-backups --skip-redis-config-generation kf-bench
  test "$(git -C kf-bench/apps/frappe rev-parse HEAD)" = "$FRAPPE_SHA" && echo "Frappe fijado: OK"
)
```

`--no-backups` evita el paso que programa backups en cron. Sin esa opción `bench init` termina con `FileNotFoundError: /usr/bin/crontab` si `cronie` no está instalado. Un fallo en cualquier paso detiene el bloque (`set -e`).

## 2. MariaDB de usuario (puerto 3307)

```bash
cd ~/frappe-kf && mkdir -p mariadb/data mariadb/run
mariadb-install-db --no-defaults --datadir=$PWD/mariadb/data --auth-root-authentication-method=normal
cat > mariadb/my.cnf <<CNF
[mysqld]
datadir=$PWD/mariadb/data
socket=$PWD/mariadb/run/mysqld.sock
pid-file=$PWD/mariadb/run/mysqld.pid
port=3307
bind-address=127.0.0.1
character-set-client-handshake=FALSE
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
[mysql]
default-character-set=utf8mb4
CNF
nohup mariadbd --defaults-file=$PWD/mariadb/my.cnf > mariadb/run/server.log 2>&1 &
mariadb -uroot -S $PWD/mariadb/run/mysqld.sock -e "
  ALTER USER 'root'@'localhost' IDENTIFIED BY 'kf_dev_root';
  CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY 'kf_dev_root';
  GRANT ALL ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
  DELETE FROM mysql.global_priv WHERE User='';
  FLUSH PRIVILEGES;"
```

Contraseñas de desarrollo ficticias, solo para esta instancia local. **Elimina los usuarios anónimos** (`DELETE ... User=''`): si no, `bench new-site` falla con `Access denied for user '_xxxx'@'localhost'`.

## 3. Valkey

```bash
export PATH=$HOME/frappe-kf/tools/venv/bin:$PATH
cd ~/frappe-kf/kf-bench
bench setup redis        # genera config/redis_cache.conf y redis_queue.conf (puertos 13000 y 11000)
for n in cache queue; do nohup valkey-server config/redis_$n.conf > logs/valkey_$n.log 2>&1 & done
valkey-cli -p 13000 ping   # PONG
valkey-cli -p 11000 ping   # PONG
```

## 4. Sitio desechable y ERPNext

```bash
(
  set -euo pipefail
  export PATH=$HOME/frappe-kf/tools/venv/bin:$PATH
  cd ~/frappe-kf/kf-bench
  bench new-site kf.localhost --db-host 127.0.0.1 --db-port 3307 \
    --db-root-username root --db-root-password kf_dev_root \
    --admin-password admin_dev_kf --no-mariadb-socket
  bench get-app erpnext ~/frappe-kf/pins/erpnext --branch kf-pin   # repo local fijado en la sección 1
  test "$(git -C apps/erpnext rev-parse HEAD)" = "0d2bc1a9398eccf8003a851c01e2f2d99e594a01" \
    || { echo "ERROR: ERPNext no está en la revisión fijada" >&2; exit 1; }
  bench --site kf.localhost install-app erpnext
)
```

`--no-mariadb-socket` está marcado como obsoleto; el reemplazo es `--mariadb-user-host-login-scope='%'`.

## 5. App `kontaflow_sv`

La app se generó con `bench new-app kontaflow_sv --no-git` (escribe solo en `kf-bench/apps/kontaflow_sv`). Los archivos se trasladaron a la raíz de este repositorio, conservando `README.md`, `docs/` y el historial. **`bench new-app` no se vuelve a ejecutar.** Para que un bench nuevo vea el repositorio se usa `bench get-app --soft-link`, que crea el enlace simbólico y **registra la app en `sites/apps.txt`**. Un `ln -s` manual con `pip install -e` no la registra y `install-app` falla con `App kontaflow_sv not in apps.txt`.

Si `apps/kontaflow_sv` ya existe como directorio (por ejemplo, uno generado por `bench new-app`), se aparta antes. Las comprobaciones detienen el bloque, con código 1, antes de instalar:

```bash
(
  set -euo pipefail
  export PATH=$HOME/frappe-kf/tools/venv/bin:$PATH
  REPO=/ruta/a/este/repositorio                 # raíz del repo, donde está pyproject.toml
  cd ~/frappe-kf/kf-bench

  # 1. Validar el repositorio antes de tocar el bench
  grep -q '^name = "kontaflow_sv"' "$REPO/pyproject.toml" \
    || { echo "ERROR: $REPO no contiene el pyproject.toml de kontaflow_sv" >&2; exit 1; }

  # 2. Apartar lo que haya en apps/kontaflow_sv (directorio o enlace anterior)
  if [ -L apps/kontaflow_sv ]; then rm apps/kontaflow_sv
  elif [ -e apps/kontaflow_sv ]; then mv apps/kontaflow_sv ~/frappe-kf/kontaflow_sv.apartado-$(date +%Y%m%d%H%M%S); fi

  # 3. Enlazar y registrar la app
  bench get-app kontaflow_sv "$REPO" --soft-link

  # 4. Comprobar el enlace; si algo falla, el bloque se detiene aquí
  [ "$(readlink -f apps/kontaflow_sv)" = "$(readlink -f "$REPO")" ] \
    || { echo "ERROR: el enlace no apunta al repositorio indicado" >&2; exit 1; }
  [ ! -e "apps/kontaflow_sv/$(basename "$REPO")" ] \
    || { echo "ERROR: hay un enlace anidado dentro de apps/kontaflow_sv" >&2; exit 1; }
  grep -qx kontaflow_sv sites/apps.txt \
    || { echo "ERROR: kontaflow_sv no está en sites/apps.txt" >&2; exit 1; }
  echo "enlace correcto"

  # 5. Instalar en el sitio (solo se llega aquí si todo lo anterior pasó)
  bench --site kf.localhost install-app kontaflow_sv
)
```

Si una comprobación falla, corrige `REPO` y vuelve a ejecutar el bloque completo: el paso 2 retira el enlace anterior.

ERPNext está declarado como dependencia en `hooks.py` (`required_apps`) y en `pyproject.toml` (`[tool.bench.frappe-dependencies]`).

## 6. Verificación

```bash
export PATH=$HOME/frappe-kf/tools/venv/bin:$PATH
cd ~/frappe-kf/kf-bench
bench --site kf.localhost list-apps
bench --site kf.localhost set-config allow_tests true
bench --site kf.localhost run-tests --app kontaflow_sv
```

Resultado obtenido:

```
frappe       17.x.x-develop (09f83e0) develop
erpnext      17.x.x-develop (0d2bc1a) develop
kontaflow_sv 0.0.1                    feature_claude

kontaflow_sv.tests.test_instalacion.TestInstalacion
   ✔ test_apps_instaladas
   ✔ test_modulo_registrado
Ran 2 tests in 0.015s — OK
```

En un bench creado con las revisiones fijadas, `list-apps` muestra `frappe 17.0.0-dev kf-pin` y `erpnext 17.0.0-dev kf-pin`, porque se instalan desde la rama local `kf-pin`; los SHA son los mismos.

## Ingesta de DTE de compra (KF-02): migración, pruebas y lint

Tras traer los DocTypes `KontaFlow DTE Compra*` hay que sincronizarlos en el sitio. `bench migrate` es la vía estándar de Frappe y no destructiva; se ejecutó en `kf.localhost`:

```bash
export PATH=$HOME/frappe-kf/tools/venv/bin:$PATH
cd ~/frappe-kf/kf-bench
bench --site kf.localhost migrate
bench --site kf.localhost run-tests --app kontaflow_sv                                   # toda la app
bench --site kf.localhost run-tests --app kontaflow_sv --module kontaflow_sv.tests.test_dte_compra_parser   # solo el parser, sin base de datos
```

Resultado obtenido: 82 pruebas unitarias y 63 de integración, todas OK (unos 90 s: cada clase crea sus empresas y las de concurrencia son reales).

**Cotejo con los esquemas JSON de Hacienda** (`tests/test_esquema_ccf_v3.py` y `tests/test_esquema_ccf_v4.py`, 5 pruebas cada uno): comparan caso por caso lo que opinan el esquema y el parser. Los esquemas son archivos de Hacienda que no están en el repositorio; sin su variable, esas pruebas se omiten (el resultado muestra `skipped=5` por archivo):

```bash
# v3: copia pública del esquema (el ZIP oficial no trae fe-ccf-v3)
# v4: el ZIP oficial de Hacienda; solo se lee el miembro fe-ccf-v4.json, en memoria
KF_ESQUEMA_CCF_V3=/ruta/a/fe-ccf-v3-copia-publica.json \
KF_ESQUEMAS_ZIP=/ruta/a/JSON-Schemas-Hacienda.zip \
  bench --site kf.localhost run-tests --app kontaflow_sv
```

Requiere `jsonschema` (ya instalado en el entorno del bench). El esquema debe cargarse con `Decimal` para los importes: con `float`, `multipleOf` da falsos positivos.

**Pruebas de concurrencia real** (`tests/test_ingesta_concurrente.py`): lanzan 6 procesos (`tests/trabajador_concurrente.py`), cada uno con su propia conexión y transacción, sincronizados a una hora de salida común. Para que los otros procesos vean los datos, esta clase **confirma** (commit) una empresa de prueba con nombre propio de la ejecución y la elimina al terminar (la limpieza se registra con `addClassCleanup` y confirma en un `finally`, de modo que no queda nada a medias). Si una ejecución se interrumpe sin llegar a la limpieza, quedan empresas `KF Prueba C <token>` y `KF Prueba Z <token>` con su DTE: el token las identifica como de una ejecución anterior (nunca se reutilizan) y hay que borrarlas a mano.

El choque entre dos solicitudes llega de dos formas según `innodb_snapshot_isolation` de MariaDB (activo por defecto desde 11.6, también en la 11.8 documentada). Con él activo, el error 1020 **revierte la transacción completa** del que pierde. Ambos modos están cubiertos y se verificó con mutaciones; para repetirlo en un servidor desechable:

```bash
mariadb -uroot -pkf_dev_root -h127.0.0.1 -P3307 -e "SET GLOBAL innodb_snapshot_isolation=OFF"   # modo anterior
# ... ejecutar test_ingesta_concurrente ...
mariadb -uroot -pkf_dev_root -h127.0.0.1 -P3307 -e "SET GLOBAL innodb_snapshot_isolation=ON"    # restaurar
```

Las pruebas de integración crean las empresas `KF Prueba A` y `KF Prueba B` (con NIT ficticios) y un `Warehouse Type` «Transit» que ERPNext da por existente al crear una `Company`, porque este sitio no pasó por el asistente de configuración. Todo se deshace al terminar la clase de pruebas. **Las pruebas solo borran sus propios registros**: la limpieza (`tests/limpieza.py`) exige indicar las empresas de prueba y se niega a actuar sin alcance, y los conteos se limitan a esas empresas, de modo que el sitio puede tener otros DTE sin que las pruebas los vean ni los toquen. No se usa `BootStrapTestData` de ERPNext, que modifica el sitio completo al importarse.

Lint con la configuración del `pyproject.toml` (`ruff` se instaló solo en el venv de herramientas, fuera del repo, con `~/frappe-kf/tools/venv/bin/pip install ruff`):

```bash
~/frappe-kf/tools/venv/bin/ruff check kontaflow_sv     # All checks passed
~/frappe-kf/tools/venv/bin/ruff format --check kontaflow_sv
```

`ruff format --check` marca `kontaflow_sv/hooks.py` (plantilla generada por Frappe en KF-01, sin cambios de formato en KF-02).

## Arranque diario

En una terminal nueva `bench` **no** está en el `PATH`: vive en el venv de `~/frappe-kf/tools/venv`. MariaDB y Valkey tampoco arrancan solos tras un reinicio.

El script `arrancar-servicios.sh` (se crea una vez, **fuera** del repo) arranca solo lo que falta:
- Si MariaDB o Valkey ya responden, los **reutiliza** sin tocarlos.
- Solo borra `mysqld.pid` y `mysqld.sock` cuando el PID guardado no corresponde a un `mariadbd` vivo.
- Espera como máximo 60 s por servicio. Si alguno no responde, imprime el error con las últimas líneas de su log y termina con código 1.

```bash
cat > ~/frappe-kf/tools/arrancar-servicios.sh <<'SCRIPT'
#!/usr/bin/env bash
# Arranca MariaDB y Valkey de KontaFlow solo si no están activos.
# Sale con código 1 si alguno no responde dentro del tiempo límite.
set -u
KF=${KF:-$HOME/frappe-kf}
ESPERA=${ESPERA:-60}

mariadb_ok() { mariadb -uroot -pkf_dev_root -h127.0.0.1 -P3307 -e "select 1" >/dev/null 2>&1; }
valkey_ok() { valkey-cli -p "$1" ping 2>/dev/null | grep -q PONG; }
esperar() { # esperar "<nombre>" <comando...>
  local nombre=$1 i=0; shift
  until "$@"; do
    i=$((i + 1))
    if [ "$i" -ge "$ESPERA" ]; then echo "ERROR: $nombre no respondió en ${ESPERA}s" >&2; return 1; fi
    sleep 1
  done
  echo "$nombre: activo"
}

fallo=0

# MariaDB
pid_file=$KF/mariadb/run/mysqld.pid
if mariadb_ok; then
  echo "MariaDB: ya activo"
else
  if [ -f "$pid_file" ] && [ "$(ps -p "$(cat "$pid_file")" -o comm= 2>/dev/null)" = "mariadbd" ]; then
    echo "MariaDB: proceso vivo (pid $(cat "$pid_file")), esperando a que responda"
  else
    rm -f "$pid_file" "$KF/mariadb/run/mysqld.sock"   # restos de un apagado sin cierre limpio
    mkdir -p "$KF/mariadb/run"
    nohup mariadbd --defaults-file="$KF/mariadb/my.cnf" > "$KF/mariadb/run/server.log" 2>&1 &
  fi
  esperar MariaDB mariadb_ok || { tail -n 5 "$KF/mariadb/run/server.log" >&2; fallo=1; }
fi

# Valkey (caché y cola)
for par in cache:13000 queue:11000; do
  nombre=${par%%:*}; puerto=${par##*:}
  if valkey_ok "$puerto"; then
    echo "Valkey $nombre: ya activo"
  else
    (cd "$KF/kf-bench" && nohup valkey-server "config/redis_$nombre.conf" > "logs/valkey_$nombre.log" 2>&1 &)
    esperar "Valkey $nombre" valkey_ok "$puerto" || { tail -n 5 "$KF/kf-bench/logs/valkey_$nombre.log" >&2; fallo=1; }
  fi
done
exit "$fallo"
SCRIPT
chmod +x ~/frappe-kf/tools/arrancar-servicios.sh
```

Cada día, o tras un reinicio:

```bash
export PATH=$HOME/frappe-kf/tools/venv/bin:$PATH
bench --version   # 5.31.1
~/frappe-kf/tools/arrancar-servicios.sh || echo "Revisa los logs en ~/frappe-kf/mariadb/run/ y ~/frappe-kf/kf-bench/logs/"
cd ~/frappe-kf/kf-bench
bench start       # servidor de desarrollo (no se ejecutó en KF-01)
```

Sitio: `http://kf.localhost:8000`, usuario `Administrator`, contraseña `admin_dev_kf`. No se probó `bench start` ni el acceso web.

## KF-04.3 · Vista previa del Libro de Compras en Desk

Usa un sitio de desarrollo con el asistente inicial de Frappe y ERPNext completado.
Arranca los servicios, instala el reporte y abre Desk.

```bash
cd ~/frappe-kf/kf-bench
~/frappe-kf/tools/arrancar-servicios.sh
bench --site kf.localhost migrate
bench start
```

En otra terminal, abre `bench --site kf.localhost console`. Crea las empresas y los
borradores ficticios con los helpers de la suite. Conserva la consola abierta para
la limpieza. La contraseña solo se usa para el usuario temporal de esta prueba.

```python
from getpass import getpass

import frappe
from frappe.utils.password import update_password
from kontaflow_sv.ingesta.servicio import ingestar_dte_compra
from kontaflow_sv.tests.fixtures import FixturesDePrueba
from kontaflow_sv.tests.test_libro_compras_vista_previa import ccf_con_importes
from kontaflow_sv.tests.utilidades import NIT_EMPRESA_A, NIT_EMPRESA_B

frappe.set_user("Administrator")
fx = FixturesDePrueba()
fx.preparar()
empresa = fx.empresa("A", NIT_EMPRESA_A)
ajena = fx.empresa("B", NIT_EMPRESA_B)
usuario = fx.usuario("contador", empresa.name, "Accounts User")
update_password(usuario, getpass("Contraseña temporal: "))
dte_1 = ingestar_dte_compra(
    empresa.name, ccf_con_importes(1, "2026-09-01", gravada="100.00", iva="12.00")
)["name"]
dte_2 = ingestar_dte_compra(
    empresa.name, ccf_con_importes(2, "2026-09-30", gravada="10.00", version_dte=4)
)["name"]
frappe.db.commit()
print(empresa.name, ajena.name, usuario, dte_1, dte_2)
```

1. Entra en `http://kf.localhost:8000` con `Administrator`. Busca **Vista previa del Libro de Compras** en la barra de búsqueda de Desk. Verifica que **Empresa** y **Mes** sean obligatorios y que el mes aparezca vacío al abrir el reporte sin parámetros.
2. Selecciona la empresa A y escribe `2026-09`. Deben aparecer dos borradores y una fila **Total**. Comprueba el aviso de un borrador con advertencias, el detalle de IVA de `12,00` frente a una base de `100,00`, y el total de `110,00` gravadas y `13,30` de IVA del DTE. Exentas y no sujetas suman cero. Los separadores dependen del idioma del sitio.
3. Abre el primer enlace en **Borrador**. Si se muestra un panel lateral, selecciona **Abrir en página completa**. Verifica que abra `dte_1` y que su estado sea **Borrador**. La fila **Total** debe tener vacía esa columna.
4. Regresa al reporte, cambia el mes a `2026-10` y verifica que aparezca el mensaje «No hay borradores de CCF para la empresa y el mes indicados» con el reporte vacío.
5. Abre una sesión privada con el usuario temporal. Repite la consulta y el enlace para la empresa A. Busca la empresa B en el filtro y comprueba que no se pueda seleccionar con ese usuario.

Al terminar, cierra la sesión privada y elimina solo los datos de esta ejecución
desde la misma consola.

```python
frappe.set_user("Administrator")
fx.limpiar()
frappe.db.commit()
```

## KF-05 · Exportar a Excel el Libro de Compras

Usa un sitio de desarrollo con el asistente inicial completado. Arranca los
servicios y Desk como en KF-04.3. Para preparar los datos ficticios, conserva la
empresa, el usuario limitado y el segundo borrador de esa sección. Al crear el
primer borrador, usa esta variante para comprobar exentas y no sujetas.

```python
dte_1 = ingestar_dte_compra(
    empresa.name,
    ccf_con_importes(
        1, "2026-09-01", gravada="100.00", exenta="5.05", no_suj="2.10", iva="12.00"
    ),
)["name"]
```

1. Abre **Vista previa del Libro de Compras**. Selecciona la empresa de prueba, escribe `2026-09` y pulsa **Exportar libro de compras (Excel)**.
2. Abre `<empresa>_Libro de compras_2026-09_borradores.xlsx`. Comprueba que tenga una sola hoja, **LibroCompras**, con las columnas A–T y la cabecera de la empresa, **SEPTIEMBRE**, **2026**, NIT y NRC. Los dos borradores deben ocupar las filas 8 y 9, en orden de emisión.
3. Comprueba **TOTAL** en E11 y los importes de esa fila. Debe mostrar `5,05` en exentas (G), `110,00` en gravadas (J), `13,30` en crédito fiscal (M) y `128,35` en **TOTAL COMPRAS** (R). Bajo el espacio para la firma debe aparecer «Compras no sujetas no incluidas: 1 documento por $2,10».
4. Repite la descarga en una sesión privada con el usuario temporal limitado a la empresa A. La descarga requiere permiso **Exportar** sobre **KontaFlow DTE Compra**, permiso de lectura y acceso a la empresa. Comprueba que una empresa ajena se rechace.
5. Con la misma empresa, cambia el mes a un período vacío, como `2026-10`, y pulsa **Exportar libro de compras (Excel)**. El navegador permanece en el reporte y Desk muestra «No hay borradores de CCF para la empresa y el mes indicados».
6. Elimina los datos ficticios siguiendo la limpieza de KF-04.3.

## KF-06.1 · Ingerir una nota de crédito y una nota de débito

Con los servicios de desarrollo iniciados, ejecuta `bench --site kf.localhost migrate`.
La migración de Frappe crea la tabla hija **KontaFlow DTE Compra Relacionado** y
añade campos opcionales a los DocTypes existentes.

El POST `/api/method/kontaflow_sv.api.ingestar_dte_compra` sigue recibiendo
`company` y `dte_json` (el texto JSON original). Acepta los CCF existentes y los
tipos `05` (nota de crédito) y `06` (nota de débito) v4. Para verificarlo con
datos ficticios, abre `bench --site kf.localhost console` y ejecuta:

```python
import frappe
from kontaflow_sv.api import ingestar_dte_compra
from kontaflow_sv.tests.fixtures import FixturesDePrueba, nc_con_importes, nd_con_importes
from kontaflow_sv.tests.utilidades import NIT_EMPRESA_A

frappe.set_user("Administrator")
fx = FixturesDePrueba()
try:
    fx.preparar()
    empresa = fx.empresa("A", NIT_EMPRESA_A)
    for crear_json in (nc_con_importes, nd_con_importes):
        original = crear_json()
        resultado = ingestar_dte_compra(company=empresa.name, dte_json=original)
        doc = frappe.get_doc("KontaFlow DTE Compra", resultado["name"])
        print(doc.tipo_dte, doc.version, doc.estado, doc.total_gravada, doc.iva)
        print(doc.documentos_relacionados[0].numero_documento, doc.advertencias)
        print(ingestar_dte_compra(empresa.name, original)["resultado"])
finally:
    fx.limpiar()
    frappe.db.commit()
```

Cada nota queda en **Borrador** con gravadas `100,00`, IVA declarado `12,00` y
una advertencia sobre la diferencia con el 13 %. La referencia se guarda con
tipo de documento, tipo de generación, número y fecha de emisión. El reintento
idéntico devuelve `existente`. La consulta, la vista previa y la aplicación de
signos al exportar las notas corresponden a KF-06.2.

## Limitaciones y pendientes

- MariaDB 13.0.2 no está en la matriz probada de Frappe (ver arriba).
- Falta `cronie`: no hay backups programados. No afecta a un sitio desechable.
- Verificado en un bench nuevo creado desde cero con las revisiones fijadas (instalación, sitio, ERPNext, enlace de la app y pruebas). La sección 1 se probó con los mismos comandos, ejecutados desde un script y no pegando el bloque literal, porque la guía usa las rutas definitivas `~/frappe-kf`. Ese bench de prueba se eliminó.
- Los bloques de las secciones 3 a 6 y el arranque diario se ejecutaron tal cual, con solo la ruta y el nombre del sitio sustituidos en la prueba del bench nuevo.
- No se probaron `bench start`, el workers, ni la interfaz web.
- La licencia de la app (`mit`, valor por defecto del generador) es una decisión pendiente. ERPNext y Frappe son GPL-3.0 y MIT respectivamente; confirmar antes de publicar.
- El correo de autor en `pyproject.toml` es ficticio (`dev@kontaflow.invalid`).
