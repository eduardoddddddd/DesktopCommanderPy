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
controlado a tu máquina local: sistema de archivos, terminal y gestión de procesos.

Construido como alternativa personal a [Desktop Commander](https://github.com/wonderwhy-er/DesktopCommanderMCP),
este proyecto prioriza:

- **Seguridad desde el principio** — sandbox de rutas permitidas, blacklist de comandos, restricción de extensiones
- **Control total** — lees y controlas cada línea de código
- **Extensibilidad** — estructura modular limpia, fácil añadir nuevas tools
- **Multiplataforma** — Windows (PowerShell) como primario, Linux/macOS listos

---

## Estado actual

| Componente | Estado |
|------------|--------|
| Tests | ✅ 15/15 passing |
| Integración Claude Desktop | ✅ Conectado y verificado (2026-03-26) |
| Versión FastMCP | 3.1.1 |
| Protocolo MCP negociado | 2025-11-25 |
| Plataforma probada | Windows 11 / Python 3.12 |

---

## Estructura del proyecto

```
DesktopCommanderPy/
├── main.py                     # Entry point (transporte stdio o HTTP)
├── pyproject.toml              # Dependencias y configuración de build
├── config/
│   └── security_config.yaml   # Dirs permitidos, blacklist, límites
├── core/
│   ├── server.py               # Instancia FastMCP + registro de tools
│   └── tools/
│       ├── filesystem.py       # read/write/edit_diff/list/search/get_info
│       ├── terminal.py         # execute_command + streaming
│       ├── process.py          # list_processes + kill_process
│       └── utils.py            # Helpers de seguridad, config, plataforma
└── tests/
    └── test_basic.py           # 15 tests: seguridad, filesystem, integridad stdio
```

---

## Instalación

### Requisitos

- Python 3.11 o 3.12
- pip (incluido con Python)

### Pasos

```powershell
cd C:\Users\Edu\DesktopCommanderPy
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install pytest pytest-asyncio   # solo para ejecutar tests
```

---

## Configuración

Edita `config/security_config.yaml` antes del primer uso:

```yaml
security:
  allowed_directories:
    - "C:/Users/TuUsuario/Documents"
    - "C:/projects"
  blocked_commands:
    - "format"
    - "diskpart"
```

> ⚠️ **Si `allowed_directories` está vacío, el sandbox está desactivado (modo dev).**
> Añade siempre tus rutas reales antes de usar en producción.

---

## Ejecución del servidor

```powershell
# Modo stdio (Claude Desktop) — por defecto
py main.py

# Modo HTTP/SSE (clientes remotos, Gemini CLI, etc.)
py main.py --http --port 8080

# Modo debug
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

Reinicia Claude Desktop tras guardar.

---

## Tools MCP disponibles

| Tool | Descripción |
|------|-------------|
| `read_file` | Lee fichero de texto con paginación (offset/length) |
| `write_file` | Escribe o añade contenido a un fichero |
| `edit_file_diff` | Edición quirúrgica por find/replace (diff-based) |
| `list_directory` | Lista directorio con tamaños, recursivo opcional |
| `search_files` | Búsqueda por patrón glob y/o contenido |
| `get_file_info` | Metadatos del fichero + preview de las primeras líneas |
| `execute_command` | Ejecuta comando shell, captura stdout+stderr completo |
| `execute_command_streaming` | Comandos largos con recogida línea a línea |
| `list_processes` | Lista procesos activos (filtrable, ordenable) |
| `kill_process` | Termina proceso por PID (graceful o forzado) |

---

## Ejecutar los tests

```powershell
.venv\Scripts\pytest tests/ -v
```

---

## 🐛 Bugs críticos resueltos durante el desarrollo

Esta sección documenta los tres problemas reales que se encontraron al integrar
el servidor con Claude Desktop. Se registran aquí para que no vuelvan a aparecer.

---

### Bug 1 — `uv` no encontrado: `spawn uv ENOENT`

**Síntoma:** Claude Desktop no arrancaba. El log
`%APPDATA%\Claude\logs\mcp-server-*.log` mostraba `spawn uv ENOENT` en bucle
desde el 8 de marzo. `main1.log` registraba `Request timed out: isGuestConnected`
hasta el 26. La app se quedaba colgada esperando una respuesta del MCP que
nunca llegaba.

**Causa raíz:** El MCP oficial Desktop Commander usa `uv` para gestionar
su entorno Python. `uv` no estaba instalado en el sistema, o estaba instalado
pero no en el PATH que Claude Desktop ve al arrancar (que es distinto al PATH
de tu terminal).

**Solución:**
1. Instalar `uv` manualmente descargando y ejecutando el script oficial.
2. El binario quedó en `C:\Users\Edu\.local\bin\uv.exe`.
3. Añadir `C:\Users\Edu\.local\bin` al PATH de usuario **del sistema** (no solo
   de la sesión actual) para que Claude Desktop lo herede:

```powershell
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    "C:\Users\Edu\.local\bin;" + [System.Environment]::GetEnvironmentVariable("PATH","User"),
    "User"
)
```

4. Reiniciar Claude Desktop para que cargue el nuevo PATH.

---

### Bug 2 — Claude Desktop se colgaba al conectar: banner ASCII de FastMCP

**Síntoma:** Después de instalar `uv`, Claude Desktop seguía bloqueándose o
tardando mucho en conectar. Los logs mostraban que el servidor nuestro
(DesktopCommanderPy) arrancaba pero Claude nunca terminaba de inicializarlo.

**Causa raíz:** FastMCP imprime por defecto un banner decorativo en ASCII por
`stdout` al arrancar. Claude Desktop se comunica con el servidor MCP mediante
**JSON-RPC estricto sobre stdout**. Cualquier byte que no sea JSON válido en ese
canal rompe el protocolo: Claude Desktop lo descarta o se bloquea esperando un
mensaje que nunca llega correctamente.

El banner tiene este aspecto en stdout antes del primer mensaje JSON-RPC:
```
╭─────────────────────────────────────────╮
│          FastMCP Server v3.x            │
╰─────────────────────────────────────────╯
```

**Solución:** Pasar `show_banner=False` en la llamada `mcp.run()`:

```python
# CRÍTICO: show_banner=False es OBLIGATORIO en transporte stdio.
# Claude Desktop usa JSON-RPC estricto sobre stdout.
# Cualquier output no-JSON (incluido el banner de FastMCP) corrompe
# el canal y provoca que Claude Desktop se cuelgue o no conecte.
# NO eliminar este flag.
mcp.run(transport="stdio", show_banner=False)
```

**Test de regresión añadido:** `TestStdioTransport::test_server_stdout_is_clean_on_startup`
lanza el proceso real y verifica que el primer byte de stdout sea `{`.
Si una actualización futura de FastMCP cambia el comportamiento del banner,
el test lo detectará antes de llegar a Claude Desktop.

Bug detectado inicialmente por Gemini CLI al analizar los logs de Claude Desktop.

---

### Bug 3 — `execute_command` con Python/pytest devolvía vacío: deadlock stdin

**Síntoma:** Comandos simples como `Get-Date` funcionaban correctamente.
Pero cualquier comando que arrancase un proceso Python (incluido pytest)
devolvía salida vacía y eventualmente timeout, o en algunos casos colgaba
Claude Desktop completamente.

**Causa raíz:** Al lanzar un subproceso con `asyncio.create_subprocess_exec`,
el proceso hijo **heredaba el stdin del servidor MCP**, que está conectado al
canal JSON-RPC de Claude Desktop. Procesos como Python, pytest o cualquier
intérprete intentan leer stdin durante el arranque. Al hacerlo, se bloqueaban
esperando input que nunca llega (el canal está ocupado con mensajes MCP),
causando un deadlock completo: proceso hijo bloqueado → servidor MCP bloqueado
esperando respuesta del hijo → Claude Desktop bloqueado esperando al servidor.

**Solución:** Pasar `stdin=asyncio.subprocess.DEVNULL` en ambas funciones de
`terminal.py`:

```python
proc = await asyncio.create_subprocess_exec(
    *shell_args, command,
    stdin=asyncio.subprocess.DEVNULL,   # impide que el hijo herede el stdin MCP
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.STDOUT,
    cwd=cwd,
    env=env,
)
```

Aplica a `execute_command` y a `execute_command_streaming`.

---

## Roadmap — lo que falta para igualar Desktop Commander original

### Features pendientes (por prioridad)

| Feature | Descripción | Prioridad |
|---------|-------------|-----------|
| `start_process` + `read_process_output` + `interact_with_process` | Gestión de procesos con estado: arrancar un proceso largo, leer su output incremental, enviarle input. Permite REPLs Python/Node interactivos, pipelines, etc. Es la mayor diferencia funcional con Desktop Commander. | 🔴 Alta |
| `create_directory` | Crear directorios (faltó en el scaffold inicial) | 🔴 Alta |
| `move_file` / `copy_file` | Mover y copiar ficheros y directorios | 🟡 Media |
| `read_multiple_files` | Leer varios ficheros en una sola llamada MCP | 🟡 Media |
| `start_search` / `stop_search` / `get_more_search_results` | Búsqueda asíncrona con sesión: lanza búsqueda en background, pagina resultados. Desktop Commander la usa para búsquedas grandes sin bloquear. | 🟡 Media |
| `get_config` / `set_config_value` | Leer y modificar la configuración del servidor en tiempo de ejecución sin reiniciar | 🟡 Media |
| `list_sessions` | Listar procesos con sesión activa | 🟢 Baja |
| `force_terminate` | Matar proceso con prejuicio (SIGKILL inmediato) | 🟢 Baja |
| Audit log | Registrar cada operación con timestamp, herramienta y resultado | 🟢 Baja |
| Restricciones por tool | `allowed_directories` separado para terminal vs filesystem | 🟢 Baja |

### La diferencia más importante: procesos con estado

Desktop Commander original tiene `start_process` + `interact_with_process` +
`read_process_output`, que permite este flujo:

```
1. start_process("python -i")           → PID 1234
2. interact_with_process(1234, "import pandas as pd")
3. interact_with_process(1234, "df = pd.read_csv('datos.csv')")
4. interact_with_process(1234, "print(df.describe())")
5. read_process_output(1234)            → resultados del análisis
6. kill_process(1234)
```

Nuestro `execute_command` solo hace procesos bloqueantes de un solo disparo.
Para implementar procesos con estado hace falta un gestor de sesiones con un
dict `{pid: (process, buffer)}` y tools adicionales. Es el siguiente gran
milestone del proyecto.

---

## Historial de versiones

| Commit | Descripción |
|--------|-------------|
| `6b36288` | Scaffold inicial: 10 tools, seguridad, tests |
| `a0b278e` | Fix: usar fnmatch para glob en search_files (14/14 tests) |
| `69414d0` | Config: rutas reales, fix hatch build target |
| `4172d29` | Chore: ignorar scripts de desarrollo (_*.bat, _*.py) |
| `b0914b0` | **Fix: show_banner=False** — banner FastMCP rompía JSON-RPC stdio |
| `2e3e609` | **Fix: stdin=DEVNULL** — deadlock heredando stdin MCP en subprocesos |

---

## Licencia

MIT — haz lo que quieras, conserva la nota de copyright.
