"""
DesktopCommanderPy - Tools de procesos con estado (sesiones interactivas).

Equivalente a start_process + read_process_output + interact_with_process
+ list_sessions + force_terminate de Desktop Commander original.

Permite:
  - Arrancar un proceso largo y obtener su PID
  - Leer su output de forma incremental sin bloquearse
  - Enviarle input (REPLs Python/Node, shells, etc.)
  - Listar sesiones activas
  - Terminar procesos con o sin gracia
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Annotated, Optional

from core.tools.session_manager import ProcessSession, sessions
from core.tools.utils import (
    check_command_allowed,
    get_default_timeout,
    get_shell,
    load_security_config,
)

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "security_config.yaml"
_security_config: dict | None = None


def _cfg() -> dict:
    global _security_config
    if _security_config is None:
        _security_config = load_security_config(_CONFIG_PATH)
    return _security_config


def _blocked() -> list[str]:
    return _cfg()["security"].get("blocked_commands", [])


# ---------------------------------------------------------------------------
# start_process
# ---------------------------------------------------------------------------

async def start_process(
    command: Annotated[str, "Comando a ejecutar. Puede ser una shell interactiva (python -i, node -i) o cualquier proceso largo."],
    working_directory: Annotated[str, "Directorio de trabajo. Por defecto el home del usuario."] = "",
    timeout_seconds: Annotated[int, "Timeout en segundos para la lectura inicial de output. 0 = usar configuración."] = 10,
) -> str:
    """Arranca un proceso en segundo plano y devuelve su PID.

    A diferencia de execute_command, el proceso queda vivo y con su
    stdout/stderr siendo capturados en un buffer interno. Usa
    read_process_output para leer el output acumulado e
    interact_with_process para enviar input (ideal para REPLs).

    Devuelve el PID y el output inicial (primeros segundos de arranque).
    """
    check_command_allowed(command, _blocked())

    shell_args = get_shell(_cfg())
    cwd = working_directory or str(Path.home())
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    logger.info("start_process: %r (cwd=%s)", command, cwd)

    proc = await asyncio.create_subprocess_exec(
        *shell_args, command,
        stdin=asyncio.subprocess.PIPE,    # PIPE para poder enviar input
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT, # merge stderr→stdout
        cwd=cwd,
        env=env,
    )

    session = ProcessSession(
        pid=proc.pid,
        command=command,
        process=proc,
    )

    # Arrancar el drenador de output en background
    task = asyncio.create_task(sessions.drain_output(session))
    session._drain_task = task
    sessions.register(session)

    # Leer output inicial
    t = timeout_seconds if timeout_seconds > 0 else get_default_timeout(_cfg())
    initial_lines, finished = await sessions.read_output(session, timeout_seconds=min(t, 5))
    output = "".join(initial_lines)

    status = "finished" if finished else "running"
    result = f"[PID {proc.pid}] Process started ({status})\n"
    result += f"Command: {command}\n"
    result += f"Working dir: {cwd}\n"
    if output:
        result += f"\n--- Initial output ---\n{output.rstrip()}"
    else:
        result += "\n(no initial output yet)"
    return result



# ---------------------------------------------------------------------------
# read_process_output
# ---------------------------------------------------------------------------

async def read_process_output(
    pid: Annotated[int, "PID del proceso (obtenido de start_process)."],
    timeout_seconds: Annotated[float, "Segundos máximos esperando output nuevo. Default 5."] = 5.0,
    max_lines: Annotated[int, "Máximo de líneas a devolver. Default 200."] = 200,
) -> str:
    """Lee el output acumulado de un proceso activo.

    Espera hasta timeout_seconds por output nuevo. Si el proceso ha
    terminado, devuelve todo el output pendiente en el buffer.
    Llama a esta tool repetidamente para leer output de forma incremental.

    Devuelve el output y el estado del proceso (running/finished).
    """
    session = sessions.get(pid)
    if session is None:
        return f"[ERROR] No existe sesión con PID {pid}. Usa list_sessions para ver los PIDs activos."

    lines, finished = await sessions.read_output(
        session,
        timeout_seconds=timeout_seconds,
        max_lines=max_lines,
    )

    output = "".join(lines)
    status = f"finished (exit={session.exit_code})" if finished else "running"

    result = f"[PID {pid}] Status: {status}  |  Lines read: {len(lines)}  |  Total emitted: {session.total_lines}\n"
    if output:
        result += f"\n{output.rstrip()}"
    else:
        result += "\n(no new output)"

    if finished:
        result += f"\n\n[Process finished with exit code {session.exit_code}]"

    return result


# ---------------------------------------------------------------------------
# interact_with_process
# ---------------------------------------------------------------------------

async def interact_with_process(
    pid: Annotated[int, "PID del proceso (obtenido de start_process)."],
    input_text: Annotated[str, "Texto a enviar al stdin del proceso. Se añade \\n automáticamente si no lo tiene."],
    timeout_seconds: Annotated[float, "Segundos esperando respuesta tras enviar input. Default 8."] = 8.0,
    max_lines: Annotated[int, "Máximo de líneas de respuesta a devolver. Default 200."] = 200,
) -> str:
    """Envía input a un proceso activo y devuelve su respuesta.

    Ideal para REPLs interactivos: Python (-i), Node.js (-i), shells, etc.
    El input se escribe en el stdin del proceso y se espera output nuevo.

    Ejemplo de flujo:
      1. start_process('python -i')       → PID 1234
      2. interact_with_process(1234, 'import pandas as pd')
      3. interact_with_process(1234, 'df = pd.read_csv("datos.csv")')
      4. interact_with_process(1234, 'print(df.describe())')
      5. kill_process(1234)
    """
    session = sessions.get(pid)
    if session is None:
        return f"[ERROR] No existe sesión con PID {pid}."

    if session.finished or session.process.returncode is not None:
        return f"[ERROR] El proceso PID {pid} ya terminó (exit={session.exit_code})."

    if session.process.stdin is None:
        return f"[ERROR] El proceso PID {pid} no tiene stdin disponible."

    # Añadir newline si no lo tiene
    text = input_text if input_text.endswith("\n") else input_text + "\n"

    try:
        session.process.stdin.write(text.encode("utf-8"))
        await session.process.stdin.drain()
    except (BrokenPipeError, ConnectionResetError) as exc:
        return f"[ERROR] No se pudo escribir en stdin de PID {pid}: {exc}"

    # Leer respuesta
    lines, finished = await sessions.read_output(
        session,
        timeout_seconds=timeout_seconds,
        max_lines=max_lines,
    )

    output = "".join(lines)
    status = f"finished (exit={session.exit_code})" if finished else "running"

    result = f"[PID {pid}] Sent: {input_text!r}  |  Status: {status}\n"
    if output:
        result += f"\n{output.rstrip()}"
    else:
        result += "\n(no output after input)"
    return result



# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------

async def list_sessions() -> str:
    """Lista todas las sesiones de proceso activas (start_process).

    Muestra PID, comando, estado, tiempo activo y líneas emitidas.
    Las sesiones terminadas se limpian automáticamente al listarlas.
    """
    all_sessions = sessions.all()

    if not all_sessions:
        return "No hay sesiones activas. Usa start_process para arrancar una."

    # Limpiar sesiones terminadas con más de 60s de antigüedad
    for s in all_sessions:
        if s.finished and s.age_seconds() > 60:
            sessions.remove(s.pid)

    all_sessions = sessions.all()
    if not all_sessions:
        return "No hay sesiones activas (las terminadas fueron limpiadas)."

    header = f"{'PID':>7}  {'Estado':<22}  {'Tiempo':>8}  {'Líneas':>7}  Comando"
    separator = "-" * 70
    rows = [header, separator]

    for s in sorted(all_sessions, key=lambda x: x.pid):
        age = f"{s.age_seconds():.0f}s"
        rows.append(
            f"{s.pid:>7}  {s.status():<22}  {age:>8}  {s.total_lines:>7}  {s.command[:40]}"
        )

    rows.append(f"\nTotal: {len(all_sessions)} sesión(es) activa(s)")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# force_terminate
# ---------------------------------------------------------------------------

async def force_terminate(
    pid: Annotated[int, "PID del proceso a matar inmediatamente."],
) -> str:
    """Mata un proceso inmediatamente sin esperar a que termine limpiamente.

    Equivale a SIGKILL en Linux o TerminateProcess en Windows.
    Usa kill_process con force=False para un cierre más limpio (SIGTERM).
    Limpia la sesión del registro tras terminar.
    """
    import psutil

    session = sessions.get(pid)

    try:
        proc = psutil.Process(pid)
        name = proc.name()
        proc.kill()
        if session:
            session.finished = True
            session.exit_code = -9
            sessions.remove(pid)
        logger.info("force_terminate: PID=%d (%s) killed", pid, name)
        return f"Proceso {pid} ({name}) eliminado forzosamente."
    except psutil.NoSuchProcess:
        if session:
            sessions.remove(pid)
        return f"El proceso {pid} no existe (ya terminó)."
    except psutil.AccessDenied:
        return f"Acceso denegado para terminar PID {pid}. Requiere permisos elevados."
    except Exception as exc:
        logger.error("force_terminate PID=%d: %s", pid, exc)
        raise
