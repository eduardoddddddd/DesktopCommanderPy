# DesktopCommanderPy

> Servidor MCP propio en Python — alternativa segura, extensible y 100% tuya a Desktop Commander.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocolo-MCP-green.svg)](https://modelcontextprotocol.io)
[![FastMCP](https://img.shields.io/badge/fastmcp-3.1.1-orange.svg)](https://github.com/jlowin/fastmcp)
[![Tests](https://img.shields.io/badge/tests-28%2F28%20OK-brightgreen.svg)]()
[![Tools](https://img.shields.io/badge/tools-26-blueviolet.svg)]()
[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-yellow.svg)](LICENSE)

---

## ¿Qué es esto?

**DesktopCommanderPy** es un servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
escrito completamente en Python que da a Claude (o cualquier IA compatible con MCP) acceso
controlado a tu máquina local y a tus sistemas externos.

Módulos actuales:
- **Filesystem** — lectura, escritura, búsqueda, edición quirúrgica
- **Terminal** — ejecución de comandos bloqueantes y streaming
- **Procesos** — gestión con psutil y sesiones interactivas (REPLs)
- **SAP HANA Cloud** — conexión, consultas, administración vía hdbcli

Construido como alternativa personal a [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP):

- **Control total** — cada línea de código es tuya, sin cajas negras
- **Seguridad desde el principio** — sandbox de rutas, blacklist de comandos, credenciales por variables de entorno
- **Extensible** — añadir un módulo nuevo es copiar un fichero y registrar las tools en server.py
- **Multiplataforma** — Windows (PowerShell) primario, Linux/macOS con detección automática

---

## Estado actual

| Componente | Estado |
|------------|--------|
| Tests | ✅ 28/28 passing |
| Integración Claude Desktop | ✅ Conectado y verificado (2026-03-26) |
| Protocolo MCP negociado | 2025-11-25 |
| FastMCP | 3.1.1 |
| Python | 3.12.10 |
| hdbcli (HANA) | 2.28.17 |
| Tools disponibles | **26** |

---

## Estructura del proyecto

```
DesktopCommanderPy/
├── main.py                          # Entry point: stdio o HTTP/SSE
├── pyproject.toml                   # Dependencias, build con hatchling
├── config/
│   ├── security_config.yaml         # Sandbox: dirs, blacklist, límites
│   ├── hana_config.yaml             # Credenciales HANA (NO en git, ver .gitignore)
│   └── hana_config.yaml.example     # Plantilla de configuración HANA
├── core/
│   ├── server.py                    # FastMCP + registro de las 26 tools
│   └── tools/
│       ├── filesystem.py            # 9 tools de sistema de archivos
│       ├── terminal.py              # 2 tools de terminal
│       ├── process.py               # 2 tools de procesos (psutil)
│       ├── process_sessions.py      # 5 tools de sesiones interactivas
│       ├── session_manager.py       # SessionManager con asyncio.Queue
│       ├── hana.py                  # 8 tools SAP HANA Cloud
│       └── utils.py                 # Seguridad, config, plataforma
└── tests/
    └── test_basic.py                # 15 tests: seguridad, filesystem, stdio
```

---

## Instalación

```powershell
cd C:\Users\Edu\DesktopCommanderPy
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install hdbcli              # módulo SAP HANA Cloud
pip install pytest pytest-asyncio   # solo para tests
```

---

## Configuración de seguridad

`config/security_config.yaml`:

```yaml
security:
  allowed_directories:
    - "C:/Users/Edu/Documents"
    - "C:/Users/Edu/Desktop"
    - "C:/Users/Edu/DesktopCommanderPy"
    - "C:/Users/Edu/VerbaSant"
    # añadir más según necesidad

  blocked_commands:
    - "format"
    - "diskpart"
    - "net user"
    - "reg add"
    - "reg delete"
    - "shutdown"

  write_blocked_extensions: [".exe", ".dll", ".sys"]
  max_file_size_bytes: 10485760
  max_read_lines: 2000

terminal:
  default_timeout_seconds: 30
  max_output_chars: 500000
```

> ⚠️ **Si `allowed_directories` está vacío, el sandbox está desactivado.**

---

## Arrancar el servidor

```powershell
py main.py                        # stdio — Claude Desktop
py main.py --http --port 8080     # HTTP/SSE — clientes remotos
py main.py --log-level DEBUG      # con logs detallados
```

---

## Configurar en Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "DesktopCommanderPy": {
      "command": "C:\\Users\\Edu\\DesktopCommanderPy\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Edu\\DesktopCommanderPy\\main.py"],
      "env": {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

Para añadir las credenciales HANA directamente aquí (opción recomendada):

```json
"env": {
  "PYTHONUTF8": "1",
  "PYTHONIOENCODING": "utf-8",
  "HANA_HOST": "tu-instancia.hanacloud.ondemand.com",
  "HANA_PORT": "443",
  "HANA_USER": "DBADMIN",
  "HANA_PASSWORD": "tu_password",
  "HANA_SCHEMA": ""
}
```

---

## Las 26 tools MCP disponibles

### Filesystem (9 tools)

| Tool | Descripción |
|------|-------------|
| `read_file` | Lee fichero con paginación offset/length |
| `write_file` | Escribe o añade contenido. Crea dirs intermedios. |
| `edit_file_diff` | Edición quirúrgica find/replace. Solo el fragmento cambiado. |
| `list_directory` | Lista con tamaños. Soporta recursivo con max_depth. |
| `search_files` | Búsqueda por glob (*.py) y/o contenido. fnmatch nativo. |
| `get_file_info` | Metadatos + preview primeras 10 líneas. |
| `create_directory` | mkdir -p sandbox-aware. |
| `move_file` | Mueve/renombra dentro del sandbox. |
| `read_multiple_files` | Lee N ficheros en una llamada. |

### Terminal (2 tools)

| Tool | Descripción |
|------|-------------|
| `execute_command` | Ejecuta y captura stdout+stderr. Timeout configurable. |
| `execute_command_streaming` | Recoge línea a línea. Para pip install, builds, etc. |

### Gestión de procesos psutil (2 tools)

| Tool | Descripción |
|------|-------------|
| `list_processes` | Tabla PID/nombre/CPU%/memoria. Filtrable y ordenable. |
| `kill_process` | SIGTERM (graceful) o SIGKILL (forzado). |

### Sesiones interactivas (5 tools) ⭐

| Tool | Descripción |
|------|-------------|
| `start_process` | Arranca proceso con stdin PIPE. Devuelve PID + output inicial. |
| `read_process_output` | Lee buffer acumulado sin bloquear. |
| `interact_with_process` | Envía texto al stdin, espera respuesta. REPLs, shells. |
| `list_sessions` | Tabla de sesiones: PID, estado, tiempo activo, líneas. |
| `force_terminate` | SIGKILL + limpia sesión del registro. |

**Flujo ejemplo — REPL Python interactivo:**
```
start_process("python -i")
  → [PID 4521] Process started (running)

interact_with_process(4521, "import pyswisseph as swe")
interact_with_process(4521, "print(swe.calc_ut(2460000, 0))")
  → ((189.43, 1.0, 0.0, ...), 0)

interact_with_process(4521, "exit()")
```

### SAP HANA Cloud — hdbcli (8 tools) 🔷

| Tool | Descripción |
|------|-------------|
| `hana_test_connection` | Verifica credenciales. Devuelve versión, usuario, schema, SSL. |
| `hana_execute_query` | SELECT / DML / CALL con tabla formateada. Límite de filas. |
| `hana_execute_ddl` | CREATE/ALTER/DROP. Requiere `confirm=True` explícito. |
| `hana_list_schemas` | Schemas visibles. Marca los de sistema (_SYS*, SYS, PUBLIC). |
| `hana_list_tables` | Tablas, vistas, Calc Views con nº columnas y tipo. |
| `hana_describe_table` | Estructura: tipo, longitud, nullable, PK, comentario. |
| `hana_get_row_count` | Filas de N tablas vía M_TABLE_STATISTICS (rápido, sin full scan). |
| `hana_get_system_info` | Memoria usada/límite, conexiones activas, alertas del sistema. |

---

## Configurar credenciales SAP HANA Cloud

Las credenciales **nunca se hardcodean en código** y `config/hana_config.yaml` está
en `.gitignore` para que nunca lleguen a GitHub.

### Opción A — Variables de entorno en claude_desktop_config.json (recomendada)

Ventajas: no hay fichero de credenciales en disco, fácil de cambiar por entorno.

```json
"env": {
  "HANA_HOST": "xxxxxxxx-xxxx.hana.trial-us10.hanacloud.ondemand.com",
  "HANA_PORT": "443",
  "HANA_USER": "DBADMIN",
  "HANA_PASSWORD": "tu_password_aqui",
  "HANA_SCHEMA": ""
}
```

### Opción B — Fichero local config/hana_config.yaml

```yaml
hana:
  host: "xxxxxxxx-xxxx.hana.trial-us10.hanacloud.ondemand.com"
  port: 443
  user: "DBADMIN"
  password: "tu_password_aqui"
  schema: ""
  encrypt: true
  sslValidateCertificate: true
  max_rows: 200
```

Copiar la plantilla y rellenar:
```powershell
copy config\hana_config.yaml.example config\hana_config.yaml
# editar hana_config.yaml con datos reales
```

### Cómo obtener el host en BTP Free Tier

1. Entra en [BTP Cockpit](https://cockpit.btp.cloud.sap)
2. Selecciona tu subaccount → **Instances and Subscriptions**
3. Busca tu instancia **SAP HANA Cloud**
4. Haz clic en los tres puntos → **Open in SAP HANA Database Explorer**
5. El host está en la barra de conexión:
   `xxxxxxxx-xxxx.hana.trial-us10.hanacloud.ondemand.com`
   (el puerto siempre es **443** en HANA Cloud)

### Verificar la conexión tras configurar

Reinicia Claude Desktop y ejecuta:
```
hana_test_connection()
```

Respuesta esperada:
```
✓ Conexión exitosa a SAP HANA Cloud
  Host:           tu-instancia.hanacloud.ondemand.com:443
  Usuario:        DBADMIN
  Schema actual:  DBADMIN
  Versión HANA:   4.00.000.00.1234567890
  Conexiones propias activas: 1
  SSL/TLS:        activado
```

### Flujo típico de exploración

```
hana_test_connection()                           → verifica credenciales
hana_get_system_info()                           → estado del Free Tier
hana_list_schemas()                              → schemas disponibles
hana_list_tables("DBADMIN")                      → tablas del schema
hana_describe_table("MI_TABLA", "DBADMIN")       → estructura de la tabla
hana_get_row_count("ORDERS,ITEMS,CUSTOMERS")     → filas sin full scan
hana_execute_query("SELECT TOP 10 * FROM ORDERS") → datos
hana_execute_ddl("CREATE TABLE TEST (ID INT)", confirm=True)
```

### Límites del Free Tier a tener en cuenta

- **Memoria:** 30 GB RAM total (monitorizeable con `hana_get_system_info`)
- **Almacenamiento:** 120 GB disco
- **Conexiones simultáneas:** limitadas — `hana_get_system_info` muestra el contador
- **La instancia se para sola** si no hay actividad en un período — `hana_test_connection`
  te dirá si está caída con un error de conexión claro

---

## Tests

```powershell
.venv\Scripts\pytest.exe tests/ -v
```

Salida esperada: `15 passed in ~1.6s`

| Suite | Tests | Qué cubre |
|-------|-------|-----------|
| `TestPathSecurity` | 4 | Sandbox de rutas permitidas |
| `TestCommandSecurity` | 3 | Blacklist de comandos peligrosos |
| `TestFilesystemTools` | 7 | read/write/edit/list/search/info |
| `TestStdioTransport` | 1 | Integridad del canal JSON-RPC (crítico) |

---

## Guía operacional — patrones y limitaciones conocidas

Sección de referencia rápida para uso desde Claude Desktop.

---

### P1 — `execute_command` no encuentra `python`, `python3` ni `cmd`

**Síntoma:** `python: command not found` o similar al ejecutar comandos Python.

**Causa:** Claude Desktop arranca con un PATH minimal de escritorio, no el PATH
completo de la sesión de usuario. `execute_command` hereda ese PATH restringido.

**Solución A (fix permanente, ya integrado):** `build_subprocess_env()` en `utils.py`
enriquece automáticamente el PATH del subprocess con los directorios del venv activo,
el Python base y el launcher `py.exe`. Desde la versión actual esto es transparente.

**Solución B (si A falla):** usar `Desktop Commander:start_process` con `py` explícito:
```
Desktop Commander:start_process { command: "py script.py", timeout_ms: 25000 }
```

---

### P2 — `C:/temp/` bloqueado para escritura

**Causa:** `security_config.yaml` tiene una lista explícita de `allowed_directories`.
`C:\temp` no está en ella, no es un bug.

**Directorios permitidos en este sistema:**
- `C:/Users/Edu/Documents` (y subdirectorios, incluido `ClaudeWork`)
- `C:/Users/Edu/Desktop`
- `C:/Users/Edu/Downloads`
- `C:/Users/Edu/DesktopCommanderPy`
- `C:/Users/Edu/VerbaSant`
- `C:/Users/Edu/AstroExtracto`
- `C:/Users/Edu/AstroCompendium`
- `C:/Users/Edu/MetaAstrum`
- `C:/Users/Edu/VTTs`
- `C:/Users/Edu/astro_cartas`

Destino por defecto recomendado: `C:/Users/Edu/Documents/`

---

### P3 — `Desktop Commander:write_file` (Node.js) bloquea la palabra `dd`

**Causa:** El servidor Node.js Desktop Commander tiene su propio blacklist de
comandos de shell. La cadena `dd` coincide como substring, bloqueando cualquier
fichero cuyo contenido incluya esa secuencia (nombres de variable, paths, texto).

**Solución:** usar `DesktopCommanderPy:write_file` para escribir ficheros con
contenido arbitrario — no tiene ese filtro. Reservar `Desktop Commander:write_file`
solo si DesktopCommanderPy no responde por permisos de path.

---

### P4 — Encoding: `UnicodeEncodeError` con caracteres especiales en Windows

**Causa:** La consola de Windows usa cp1252 por defecto. Caracteres como `≤`, `°`,
`→` causan `UnicodeEncodeError` si el script no fuerza UTF-8.

**Solución A (preferida, ya integrada):** `build_subprocess_env()` fija
`PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8` en todos los subprocesos.

**Solución B:** lanzar con `py -X utf8 script.py`.

**Solución C:** añadir al inicio del script:
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

**Solución D (fallback):** evitar caracteres especiales en el output:
usar `d` en vez de `°`, `<=` en vez de `≤`, `->` en vez de `→`.

---

### P5 — REPL interactivo frágil: no pegar funciones multilínea

**Síntoma:** errores de indentación o sintaxis al enviar bloques de código
al REPL (`py -i` + `interact_with_process`).

**Causa:** el protocolo de sesiones interactivas no maneja bien los bloques
multilínea — el REPL ve las líneas de forma fragmentada.

**Solución:** **siempre escribir el script completo a fichero y ejecutarlo de
una sola vez.** Nunca intentar pegar funciones o clases enteras en el REPL.

Patrón correcto:
```
DesktopCommanderPy:write_file  → C:/Users/Edu/Documents/script.py
Desktop Commander:start_process → py -X utf8 C:/Users/Edu/Documents/script.py
```

---

### P6 — `present_files` solo funciona con rutas `/mnt/...` del contenedor Claude

**Causa:** `present_files` genera enlaces de descarga solo para el filesystem
interno del contenedor Claude (`/mnt/user-data/outputs/`). No puede crear
enlaces para `C:\Users\Edu\...`.

**Solución:** indicar al usuario la ruta local donde está guardado el fichero.
No hay workaround disponible desde el servidor MCP.

---

## 🐛 Bugs críticos resueltos — diario de guerra

### Bug 1 — `spawn uv ENOENT`: Claude Desktop no arrancaba

**Período:** 8 de marzo al 26 de marzo de 2026.

**Síntomas:**
- `%APPDATA%\Claude\logs\mcp-server-*.log` → `spawn uv ENOENT` en bucle
- `main1.log` → `Request timed out: isGuestConnected` repetido cada pocos segundos
- Claude Desktop colgado en la pantalla de carga
- Más de 10 procesos de Claude bloqueados en segundo plano (detectados por Gemini CLI)

**Causa raíz:**
El MCP oficial Desktop Commander usa `uv` para gestionar su entorno Python.
`uv` no estaba instalado o no estaba en el **PATH que hereda Claude Desktop al
arrancar como aplicación de escritorio** — que es diferente al PATH de la terminal.

**Solución:**
```powershell
# 1. Instalar uv (script oficial Astral)
# → binario en C:\Users\Edu\.local\bin\uv.exe

# 2. Añadir al PATH de usuario del SISTEMA (no solo de la sesión)
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    "C:\Users\Edu\.local\bin;" + [System.Environment]::GetEnvironmentVariable("PATH","User"),
    "User"
)

# 3. Verificar
[System.Environment]::GetEnvironmentVariable("PATH","User")
# debe empezar por: C:\Users\Edu\.local\bin;...

# 4. Reiniciar Claude Desktop
```

**Verificación:**
```powershell
C:\Users\Edu\.local\bin\uv.exe --version
# uv 0.11.1
```

---

### Bug 2 — Banner ASCII de FastMCP: Claude Desktop se colgaba al conectar

**Síntomas:**
- Claude Desktop arrancaba pero nunca terminaba de inicializar el MCP propio
- El servidor arrancaba (visible en logs) pero Claude nunca recibía respuesta de `initialize`
- Detectado y diagnosticado por **Gemini CLI** analizando los logs

**Causa raíz:**
FastMCP imprime por defecto un **banner ASCII decorativo por `stdout`** al arrancar.
Claude Desktop usa **JSON-RPC estricto sobre stdout**: cualquier byte no-JSON rompe el
protocolo y deja a Claude esperando indefinidamente sin mensaje de error.

```
╭────────────────────────────╮
│   FastMCP Server v3.x      │   ← esto va a stdout y destruye el canal JSON-RPC
╰────────────────────────────╯
```

**La regla fundamental del transporte stdio MCP:**
> `stdout` es un canal binario exclusivo para JSON-RPC.
> Absolutamente nada más puede escribirse en él. Logs, banners y mensajes van a `stderr`.

**Solución:**
```python
# main.py — CRÍTICO: nunca eliminar este flag
mcp.run(transport="stdio", show_banner=False)
```

**Test de regresión:** `TestStdioTransport::test_server_stdout_is_clean_on_startup`
lanza el proceso real y verifica que el primer byte de stdout sea `{`.
Si una actualización futura de FastMCP cambia el comportamiento, el test falla antes
de llegar a Claude Desktop.

---

### Bug 3 — Deadlock stdin: Python/pytest devolvían output vacío

**Síntomas:**
- `Get-Date`, `where.exe`, `dir` → funcionaban perfectamente
- Cualquier proceso Python (incluido pytest) → output vacío, timeout o cuelgue total
- El proceso Python aparecía en el gestor de tareas corriendo pero sin terminar

**Causa raíz:**
Al lanzar subprocesos sin especificar `stdin`, el hijo **hereda el stdin del padre** —
que en este caso es el canal JSON-RPC de Claude Desktop. Python y otros intérpretes
leen stdin al arrancar para detectar modo interactivo. Al hacerlo, bloquean esperando
input que nunca llega → deadlock en cascada:

```
Claude Desktop → [JSON-RPC stdin] → Servidor MCP
                                         ↓
                                    asyncio.create_subprocess_exec
                                         ↓ (sin stdin=DEVNULL)
                                    Python hijo hereda stdin MCP
                                         ↓
                                    Python lee stdin → BLOQUEO ETERNO
                                         ↓
                                    Servidor MCP espera al hijo → BLOQUEO
                                         ↓
                                    Claude Desktop espera al servidor → BLOQUEO
```

**Solución:**
```python
proc = await asyncio.create_subprocess_exec(
    *shell_args, command,
    stdin=asyncio.subprocess.DEVNULL,   # ← el hijo ve /dev/null, no el canal MCP
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
    cwd=cwd,
    env=env,
)
```

Aplicado en `execute_command` y `execute_command_streaming`.

**Nota:** Las sesiones interactivas (`start_process`) usan `stdin=PIPE` deliberadamente
— es lo que permite enviarles input con `interact_with_process`. La diferencia es que
ahí el stdin lo gestiona el servidor, no lo hereda del canal MCP.

---

## Arquitectura — Gestor de sesiones

`session_manager.py` implementa un `SessionManager` singleton con un dict
`{pid: ProcessSession}` por proceso activo.

Cada `ProcessSession` contiene:
- El objeto `asyncio.subprocess.Process`
- Un `asyncio.Queue` donde se acumula todo el output
- Un `asyncio.Task` que drena `stdout` en background línea a línea
- Metadatos: comando, timestamp de inicio, líneas emitidas, estado

```
start_process("python -i")
    ├── create_subprocess_exec(stdin=PIPE, stdout=PIPE)
    ├── ProcessSession(pid, queue=Queue())
    ├── asyncio.create_task(drain_output(session))   ← background forever
    └── sessions.register(session)

drain_output [Task en background]:
    async for line in process.stdout:
        await queue.put(line)
    await queue.put(None)   ← señal de fin de stream

interact_with_process(pid, "print('hola')"):
    ├── process.stdin.write(b"print('hola')\n")
    ├── await process.stdin.drain()
    └── read_output(session, timeout=8s)
            └── asyncio.wait_for(queue.get(), 0.5s) × N iteraciones
```

---

## Historial de commits

| Hash | Descripción |
|------|-------------|
| `6b36288` | Scaffold inicial: 10 tools, seguridad, 14 tests |
| `a0b278e` | Fix: fnmatch para glob en search_files → 15/15 tests |
| `69414d0` | Config: rutas reales, fix hatch build target |
| `4172d29` | Chore: ignorar scripts auxiliares _*.bat / _*.py |
| `b0914b0` | **Fix: show_banner=False** — banner FastMCP rompía JSON-RPC |
| `2e3e609` | **Fix: stdin=DEVNULL** — deadlock heredando stdin MCP |
| `b2ba6a2` | Docs: README completo en castellano |
| `4c5691a` | Feat: sesiones interactivas + mkdir/move/multi-read → 18 tools |
| `6dbbdf3` | Docs: README con arquitectura, bugs y roadmap detallado |
| `ecf9c2e` | **Feat: módulo SAP HANA Cloud** — hdbcli, 8 tools → 26 total |
| `(próximo)` | **Fix: word-boundary blacklist + build_subprocess_env + PATH fix → 28/28 tests** |

---

### Bug 4 — Matching de substring en blacklist: `dd` bloqueaba `address`, `adding`, `hidden`…

**Detectado:** 28 de marzo de 2026.

**Síntomas:**
- `Desktop Commander:write_file` (Node.js) bloqueaba ficheros con contenido normal
  que contenía la cadena `dd` (variables, paths, palabras)
- Pero también el propio `check_command_allowed` de DesktopCommanderPy afectado:
  comandos legítimos como `black --reformat .` eran bloqueados si contenían
  subcadenas coincidentes con tokens de la blacklist

**Causa raíz:**
El matching era `blocked.lower() in cmd_lower` — búsqueda de substring pura.
El token `"dd"` en `blocked_commands` coincidía en cualquier posición:

```python
# Antes del fix — INCORRECTO
"dd" in "address"   # True → bloqueaba 'address'
"dd" in "adding"    # True → bloqueaba 'adding'
"format" in "reformat"  # True → bloqueaba '--reformat'
```

**Solución:**
```python
# Después del fix — word-boundary regex
pattern = r"\b" + re.escape(blocked.lower()) + r"\b"
re.search(pattern, "address")   # None → permitido ✓
re.search(pattern, "dd if=...")  # Match → bloqueado ✓
re.search(r"\bformat\b", "--reformat")  # None → permitido ✓
re.search(r"\bformat\b", "format C:")   # Match → bloqueado ✓
```

Los patrones multi-palabra como `"net user"` siguen funcionando exactamente igual.

---

### Bug 5 — PATH minimal: subprocesos no encontraban `python`, `python3`, `pip`

**Detectado:** 28 de marzo de 2026.

**Síntomas:**
- `execute_command("python script.py")` → `python: command not found`
- `execute_command("pip install X")` → error similar
- `Get-Date`, `dir`, `where.exe` → funcionaban sin problema

**Causa raíz:**
Claude Desktop se lanza como aplicación de escritorio de Windows, **no** desde
una terminal de usuario. El PATH que hereda es el PATH del sistema, sin las
entradas que el instalador de Python añade al PATH del usuario:

```
PATH de terminal usuario:  C:\Users\Edu\AppData\Local\Programs\Python\Python312\Scripts;...
PATH heredado por Claude:  C:\Windows\System32;C:\Windows;...  (sin Python)
```

**Solución — `build_subprocess_env()` en `utils.py`:**
```python
def build_subprocess_env(extra=None):
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Prepend: venv Scripts, base Python Scripts, C:\Windows (py.exe), LOCALAPPDATA Python
    ...
    return env
```

Aplicado en `execute_command` y `execute_command_streaming`. Los subprocesos
ahora reciben el PATH completo independientemente de cómo arrancó Claude Desktop.

---

## Roadmap| Feature | Prioridad |
|---------|-----------|
| Tests para módulo HANA (mock de hdbcli) | 🔴 Alta |
| `get_config` / `set_config_value` en runtime | 🟡 Media |
| Audit log con rotación | 🟡 Media |
| `copy_file` | 🟡 Media |
| `start_search` asíncrono con paginación | 🟡 Media |
| Restricciones allowed_dirs por tool | 🟢 Baja |
| Modo multi-IA: HTTP + auth token | 🟢 Baja |
| Tools astrología (pyswisseph, VTTs) | 🟢 Baja |
| Tools SAP adicionales (pyrfc, RFC ping) | 🟢 Baja |

---

## Licencia

MIT — haz lo que quieras, conserva la nota de copyright.
