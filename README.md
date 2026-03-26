# DesktopCommanderPy

> Servidor MCP propio en Python — alternativa segura, extensible y 100% tuya a Desktop Commander.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocolo-MCP-green.svg)](https://modelcontextprotocol.io)
[![FastMCP](https://img.shields.io/badge/fastmcp-3.1.1-orange.svg)](https://github.com/jlowin/fastmcp)
[![Tests](https://img.shields.io/badge/tests-15%2F15%20OK-brightgreen.svg)]()
[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-yellow.svg)](LICENSE)

---

## ¿Qué es esto?

**DesktopCommanderPy** es un servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
escrito completamente en Python que da a Claude (o cualquier IA compatible con MCP) acceso
controlado a tu máquina local: sistema de archivos, terminal, procesos bloqueantes y
**sesiones de proceso interactivas** (REPLs, shells, scripts largos).

Construido como alternativa personal a [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP),
este proyecto prioriza:

- **Seguridad desde el principio** — sandbox de rutas, blacklist de comandos, restricción de extensiones
- **Control total** — lees y controlas cada línea de código, sin dependencias ocultas
- **Equiparable al original** — 18 tools que cubren toda la funcionalidad de Desktop Commander
- **Extensibilidad** — estructura modular limpia, fácil añadir tools propias (SAP, astrología, etc.)
- **Multiplataforma** — Windows (PowerShell) primario, Linux/macOS listos con detección automática

---

## Estado actual

| Componente | Estado |
|------------|--------|
| Tests | ✅ 15/15 passing |
| Integración Claude Desktop | ✅ Conectado y verificado (2026-03-26) |
| Protocolo MCP negociado | 2025-11-25 |
| FastMCP | 3.1.1 |
| Python | 3.12.10 |
| Plataforma probada | Windows 11 |
| Tools disponibles | **18** |

---

## Estructura del proyecto

```
DesktopCommanderPy/
├── main.py                          # Entry point: stdio (Claude Desktop) o HTTP/SSE
├── pyproject.toml                   # Dependencias, build con hatchling
├── config/
│   └── security_config.yaml        # Sandbox: dirs permitidos, blacklist, límites
├── core/
│   ├── server.py                    # Instancia FastMCP + registro de las 18 tools
│   └── tools/
│       ├── filesystem.py            # read/write/edit_diff/list/search/info/mkdir/move/multi-read
│       ├── terminal.py              # execute_command + streaming (procesos bloqueantes)
│       ├── process.py               # list_processes + kill_process (psutil)
│       ├── process_sessions.py      # start/read/interact/list_sessions/force_terminate
│       ├── session_manager.py       # SessionManager singleton con asyncio.Queue por proceso
│       └── utils.py                 # Seguridad, config loader, detección de plataforma
└── tests/
    └── test_basic.py                # 15 tests: seguridad, filesystem, integridad stdio
```

---

## Instalación

### Requisitos

- Python 3.11 o 3.12 (recomendado 3.12)
- pip (incluido con Python)
- Git (para clonar y actualizar)

### Pasos

```powershell
cd C:\Users\Edu\DesktopCommanderPy
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install pytest pytest-asyncio   # solo para tests
```

---

## Configuración de seguridad

Edita `config/security_config.yaml` antes de usar:

```yaml
security:
  # Directorios donde el servidor puede operar (y todos sus subdirectorios)
  allowed_directories:
    - "C:/Users/Edu/Documents"
    - "C:/Users/Edu/Desktop"
    - "C:/Users/Edu/Downloads"
    - "C:/Users/Edu/Documents/ClaudeWork"
    - "C:/Users/Edu/DesktopCommanderPy"
    - "C:/Users/Edu/VerbaSant"
    # añadir más según necesidad

  # Comandos NUNCA ejecutables, independientemente del contexto
  blocked_commands:
    - "format"
    - "diskpart"
    - "net user"
    - "reg add"
    - "reg delete"
    - "shutdown"
    # ver lista completa en el archivo

  # Extensiones nunca escribibles
  write_blocked_extensions:
    - ".exe"
    - ".dll"
    - ".sys"

  max_file_size_bytes: 10485760   # 10 MB
  max_read_lines: 2000

terminal:
  default_timeout_seconds: 30
  max_output_chars: 500000
```

> ⚠️ **Si `allowed_directories` está vacío, el sandbox está desactivado (modo dev).**
> Configura siempre tus rutas antes de usar en producción.

---

## Arrancar el servidor

```powershell
# Modo stdio — para Claude Desktop (por defecto)
py main.py

# Modo HTTP/SSE — para clientes remotos, Gemini CLI, etc.
py main.py --http --port 8080

# Con nivel de log detallado
py main.py --log-level DEBUG
```

---

## Configurar en Claude Desktop

Edita `%APPDATA%\Claude\claude_desktop_config.json`:

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

Reinicia Claude Desktop tras guardar el fichero.

---

## Las 18 tools MCP disponibles

### Filesystem

| Tool | Descripción |
|------|-------------|
| `read_file` | Lee fichero de texto con paginación (offset/length). Trunca si es muy largo. |
| `write_file` | Escribe o añade contenido a un fichero. Crea directorios intermedios. |
| `edit_file_diff` | Edición quirúrgica por find/replace. Solo el fragmento cambiado, no el fichero entero. |
| `list_directory` | Lista directorio con tamaños y tipos. Soporta recursivo con max_depth. |
| `search_files` | Búsqueda por patrón glob (*.py) y/o contenido. Usa fnmatch nativo. |
| `get_file_info` | Metadatos del fichero (tamaño, fechas, extensión) + preview primeras 10 líneas. |
| `create_directory` | Crea directorio y todos los intermedios (equivale a mkdir -p). |
| `move_file` | Mueve o renombra ficheros y directorios dentro del sandbox. |
| `read_multiple_files` | Lee N ficheros en una sola llamada. Útil para comparar módulos. |

### Terminal (procesos bloqueantes)

| Tool | Descripción |
|------|-------------|
| `execute_command` | Ejecuta comando y devuelve stdout+stderr completo. Con timeout configurable. |
| `execute_command_streaming` | Igual pero recoge línea a línea. Para compilaciones, pip install, etc. |

### Gestión de procesos (psutil)

| Tool | Descripción |
|------|-------------|
| `list_processes` | Lista procesos activos con PID, nombre, CPU%, memoria. Filtrable y ordenable. |
| `kill_process` | Termina proceso por PID. Modo graceful (SIGTERM) o forzado (SIGKILL). |

### Sesiones de proceso interactivas ⭐

| Tool | Descripción |
|------|-------------|
| `start_process` | Arranca un proceso con stdin PIPE. Devuelve PID + output inicial. |
| `read_process_output` | Lee el buffer acumulado del proceso sin bloquearlo. Paginable. |
| `interact_with_process` | Envía texto al stdin y espera respuesta. Para REPLs, shells, etc. |
| `list_sessions` | Tabla de sesiones activas: PID, estado, tiempo activo, líneas emitidas. |
| `force_terminate` | SIGKILL inmediato + limpia la sesión del registro interno. |

### Flujo ejemplo con sesiones interactivas

```
1. start_process("python -i")
   → [PID 4521] Process started (running)

2. interact_with_process(4521, "import pyswisseph as swe")
   → (sin output, Python cargó el módulo)

3. interact_with_process(4521, "print(swe.calc_ut(2460000, 0))")
   → ((189.43, 1.0, 0.0, 0.0, 0.0, 0.0), 0)

4. interact_with_process(4521, "exit()")
5. list_sessions()
   → (sesión terminada, se limpia automáticamente)
```

---

## Tests

```powershell
.venv\Scripts\pytest.exe tests/ -v
```

Salida esperada:
```
15 passed in 1.6s
```

Cobertura de tests:
- `TestPathSecurity` — sandbox de rutas (4 tests)
- `TestCommandSecurity` — blacklist de comandos (3 tests)
- `TestFilesystemTools` — read/write/edit/list/search/info (7 tests)
- `TestStdioTransport` — integridad del canal JSON-RPC (1 test crítico)

---

## 🐛 Bugs críticos resueltos — diario de guerra

Esta sección documenta los tres problemas reales encontrados durante la integración
con Claude Desktop. Se mantiene aquí como referencia permanente.

---

### Bug 1 — `spawn uv ENOENT`: Claude Desktop no arrancaba

**Cuándo ocurrió:** Desde el 8 de marzo de 2026. Claude Desktop no arrancaba.

**Síntomas:**
- El log `%APPDATA%\Claude\logs\mcp-server-*.log` mostraba `spawn uv ENOENT` en bucle.
- `main1.log` registraba `Request timed out: isGuestConnected` repetidamente hasta el 26 de marzo.
- La aplicación Claude Desktop se quedaba colgada en la pantalla de carga.
- Más de 10 procesos de Claude bloqueados en segundo plano (detectados y cerrados por Gemini CLI).

**Causa raíz:**
El MCP oficial Desktop Commander usa `uv` (gestor de paquetes Python de Astral) para
arrancar su entorno. `uv` no estaba instalado, o estaba instalado pero **no en el PATH
que hereda Claude Desktop** al arrancar como aplicación de escritorio. El PATH de las
aplicaciones de escritorio en Windows es diferente al PATH de la sesión de terminal.

**Solución:**
```powershell
# 1. Instalar uv (script oficial de Astral)
# Descargado y ejecutado manualmente — quedó en C:\Users\Edu\.local\bin\uv.exe

# 2. Verificar instalación
C:\Users\Edu\.local\bin\uv.exe --version
# uv 0.11.1

# 3. Añadir al PATH de usuario del SISTEMA (no solo de la sesión)
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    "C:\Users\Edu\.local\bin;" + [System.Environment]::GetEnvironmentVariable("PATH","User"),
    "User"
)

# 4. Verificar que quedó al principio del PATH
[System.Environment]::GetEnvironmentVariable("PATH","User")
# C:\Users\Edu\.local\bin;C:\Users\Edu\AppData\Local\...

# 5. Reiniciar Claude Desktop
```

**Verificación posterior:**
```powershell
where uv
# C:\Users\Edu\.local\bin\uv.exe  ← correcto
```

---

### Bug 2 — Banner ASCII de FastMCP: Claude Desktop se colgaba al conectar

**Cuándo ocurrió:** Al implementar DesktopCommanderPy por primera vez.

**Síntomas:**
- Claude Desktop arrancaba pero se quedaba colgado sin terminar de conectar al MCP.
- El log mostraba que el proceso del servidor arrancaba, pero Claude nunca recibía
  la respuesta de `initialize`.
- Detectado y diagnosticado por **Gemini CLI** al analizar los logs.

**Causa raíz:**
FastMCP imprime por defecto un **banner decorativo en ASCII por `stdout`** al arrancar:
```
╭────────────────────────────╮
│   FastMCP Server v3.x      │
╰────────────────────────────╯
```
Claude Desktop se comunica con el servidor MCP mediante **JSON-RPC estricto sobre stdout**.
Cualquier byte que no sea JSON válido en ese canal rompe el protocolo: Claude Desktop lo
descarta, se desincroniza y se queda esperando indefinidamente. No hay reintentos ni
mensajes de error claros — simplemente se cuelga.

**La regla fundamental del transporte stdio MCP:**
> stdout es un canal de comunicación binario exclusivo para JSON-RPC.
> Ningún proceso MCP puede escribir nada más en stdout — ni logs, ni banners,
> ni mensajes de bienvenida. Todo eso va a stderr.

**Solución:**
```python
# En main.py — CRÍTICO: NO eliminar este flag nunca
mcp.run(transport="stdio", show_banner=False)
```

**Test de regresión añadido:**
`TestStdioTransport::test_server_stdout_is_clean_on_startup` — lanza el proceso real
del servidor y verifica que el **primer byte de stdout sea `{`** (JSON-RPC válido).
Si una actualización futura de FastMCP cambia el comportamiento del banner, el test
falla antes de llegar a Claude Desktop.

---

### Bug 3 — Deadlock stdin: `execute_command` con Python devolvía vacío

**Cuándo ocurrió:** Durante las pruebas en vivo del servidor ya conectado.

**Síntomas:**
- Comandos simples (`Get-Date`, `where.exe`, `dir`) funcionaban perfectamente.
- Cualquier comando que arrancara un proceso Python — incluido pytest — devolvía
  **salida vacía** y eventualmente timeout.
- En algunos casos Claude Desktop se colgaba completamente.
- El proceso Python se veía en el gestor de tareas corriendo pero sin terminar nunca.

**Causa raíz:**
Al lanzar subprocesos con `asyncio.create_subprocess_exec` sin especificar `stdin`,
el proceso hijo **hereda el stdin del proceso padre** — que en este caso es el servidor
MCP, cuyo stdin está conectado al canal JSON-RPC de Claude Desktop.

Procesos como Python, pytest, Node.js y otros interpretes intentan **leer stdin** durante
el arranque (para detectar si están en modo interactivo, cargar `sitecustomize.py`, etc.).
Al hacerlo, bloquean esperando input que nunca llega — el canal está ocupado con tráfico
MCP. Resultado: **deadlock completo**:

```
Claude Desktop → [JSON-RPC stdin] → Servidor MCP
                                         ↓
                                    asyncio.create_subprocess_exec
                                         ↓
                                    Python hijo hereda stdin MCP
                                         ↓
                                    Python hijo lee stdin → BLOQUEO
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

**Nota importante:** Las sesiones interactivas (`start_process`) usan `stdin=PIPE`
deliberadamente — es lo que permite enviar input con `interact_with_process`.
La diferencia es que en sesiones el stdin lo controla el servidor, no lo hereda
del canal MCP.

---

## Arquitectura interna — Gestor de sesiones

El módulo `session_manager.py` implementa un `SessionManager` singleton que mantiene
un registro `{pid: ProcessSession}` de todos los procesos activos.

Cada `ProcessSession` contiene:
- El objeto `asyncio.subprocess.Process`
- Un `asyncio.Queue` donde se acumula todo el output del proceso
- Un `asyncio.Task` que drena `stdout` en background y mete líneas en el Queue
- Metadatos: comando, timestamp de inicio, líneas totales emitidas, estado

El drenador de output corre como tarea asyncio independiente por cada sesión.
`read_output` usa `asyncio.wait_for` con timeout para leer del Queue sin bloquear
el event loop del servidor.

```
start_process("python -i")
    │
    ├── asyncio.create_subprocess_exec → Process(pid=4521, stdin=PIPE, stdout=PIPE)
    ├── ProcessSession(pid=4521, queue=Queue(), ...)
    ├── asyncio.create_task(drain_output(session))  ← corre en background
    └── sessions.register(session)

drain_output (Task corriendo en background):
    async for line in process.stdout:
        await session.output_queue.put(line)
    await session.output_queue.put(None)  ← señal de fin

interact_with_process(4521, "print('hola')"):
    ├── process.stdin.write(b"print('hola')\n")
    ├── await process.stdin.drain()
    └── read_output(session, timeout=8s)
            └── asyncio.wait_for(queue.get(), timeout=0.5s) × N
```

---

## Historial de commits

| Hash | Descripción |
|------|-------------|
| `6b36288` | Scaffold inicial: 10 tools, seguridad, 14 tests |
| `a0b278e` | Fix: fnmatch para glob en `search_files` (14/14 → 15/15 tests) |
| `69414d0` | Config: rutas reales de Edu, fix hatch build target en pyproject.toml |
| `4172d29` | Chore: ignorar scripts auxiliares `_*.bat` y `_*.py` en git |
| `b0914b0` | **Fix: `show_banner=False`** — banner FastMCP rompía JSON-RPC stdio |
| `2e3e609` | **Fix: `stdin=DEVNULL`** — deadlock heredando stdin MCP en subprocesos |
| `b2ba6a2` | Docs: README completo en castellano con bugs y roadmap |
| `4c5691a` | **Feat: 18 tools** — sesiones interactivas + mkdir + move + multi-read |

---

## Roadmap

### Pendiente de menor prioridad

| Feature | Descripción |
|---------|-------------|
| `get_config` / `set_config_value` | Leer y modificar configuración en runtime sin reiniciar |
| Audit log | Registrar cada operación: timestamp, tool, ruta, resultado |
| Restricciones por tool | `allowed_directories` separado para terminal vs filesystem |
| `copy_file` | Copiar ficheros (move_file ya existe) |
| `start_search` async | Búsqueda en background con paginación de resultados (como DC original) |

### Ideas propias (no en Desktop Commander original)

| Idea | Descripción |
|------|-------------|
| Tools SAP | RFC ping, lista de transportes, estado de sistema vía pyrfc |
| Tools astrología | Ejecutar cálculos pyswisseph, leer corpus VTTs, consultar AstroCompendium |
| Modo multi-IA | HTTP + auth token para que Claude y Gemini usen el mismo servidor simultáneamente |
| Clipboard | `clipboard_get` / `clipboard_set` para automatización de escritorio |

---

## Licencia

MIT — haz lo que quieras, conserva la nota de copyright.
