"""
DesktopCommanderPy - Gestor de sesiones de procesos con estado.

Mantiene un dict global de procesos activos con sus buffers de output.
Permite arrancar procesos, leer su output de forma incremental y
enviarles input (REPLs, shells interactivas, compilaciones largas, etc.)

Diseño:
  - SessionManager es un singleton (instancia global `sessions`)
  - Cada sesión guarda el proceso asyncio, un asyncio.Queue para output,
    y metadatos (comando, timestamps, líneas totales emitidas)
  - Un task asyncio por sesión drena stdout+stderr al Queue
  - Las tools leen del Queue con timeout para no bloquear

CRÍTICO: stdin=DEVNULL en execute_command normal, pero en sesiones
interactivas necesitamos stdin=PIPE para poder enviar input.
"""

import asyncio
import logging
import os
import platform
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclass de sesión
# ---------------------------------------------------------------------------

@dataclass
class ProcessSession:
    pid: int
    command: str
    process: asyncio.subprocess.Process
    output_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    started_at: float = field(default_factory=time.time)
    total_lines: int = 0
    finished: bool = False
    exit_code: Optional[int] = None
    _drain_task: Optional[asyncio.Task] = field(default=None, repr=False)

    def age_seconds(self) -> float:
        return time.time() - self.started_at

    def status(self) -> str:
        if self.finished:
            return f"finished (exit={self.exit_code})"
        if self.process.returncode is not None:
            return f"exited (exit={self.process.returncode})"
        return "running"



# ---------------------------------------------------------------------------
# Singleton SessionManager
# ---------------------------------------------------------------------------

class SessionManager:
    """Registro global de procesos con estado activos."""

    def __init__(self) -> None:
        self._sessions: dict[int, ProcessSession] = {}

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def register(self, session: ProcessSession) -> None:
        self._sessions[session.pid] = session
        logger.info("Session registered: PID=%d  cmd=%r", session.pid, session.command)

    def get(self, pid: int) -> Optional[ProcessSession]:
        return self._sessions.get(pid)

    def remove(self, pid: int) -> None:
        if pid in self._sessions:
            del self._sessions[pid]
            logger.info("Session removed: PID=%d", pid)

    def all(self) -> list[ProcessSession]:
        return list(self._sessions.values())

    # ------------------------------------------------------------------
    # Drenador de output (corre como asyncio.Task por sesión)
    # ------------------------------------------------------------------

    async def drain_output(self, session: ProcessSession) -> None:
        """Lee stdout+stderr del proceso y los mete en el Queue de la sesión."""
        try:
            assert session.process.stdout is not None
            async for raw in session.process.stdout:
                line = raw.decode("utf-8", errors="replace")
                await session.output_queue.put(line)
                session.total_lines += 1
        except Exception as exc:
            logger.debug("drain_output ended for PID=%d: %s", session.pid, exc)
        finally:
            # Señal de fin de stream
            await session.output_queue.put(None)
            session.exit_code = await session.process.wait()
            session.finished = True
            logger.info("Session PID=%d finished (exit=%s)", session.pid, session.exit_code)

    # ------------------------------------------------------------------
    # Lectura de output con timeout
    # ------------------------------------------------------------------

    async def read_output(
        self,
        session: ProcessSession,
        timeout_seconds: float = 5.0,
        max_lines: int = 200,
    ) -> tuple[list[str], bool]:
        """
        Lee hasta max_lines del Queue de la sesión.

        Retorna (líneas, proceso_terminado).
        Se detiene si pasa timeout_seconds sin output nuevo.
        """
        lines: list[str] = []
        deadline = time.monotonic() + timeout_seconds

        while len(lines) < max_lines:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                item = await asyncio.wait_for(
                    session.output_queue.get(), timeout=min(remaining, 0.5)
                )
                if item is None:   # fin de stream
                    return lines, True
                lines.append(item)
                # Reset deadline si llega output: espera más output próximo
                deadline = time.monotonic() + min(timeout_seconds, 2.0)
            except asyncio.TimeoutError:
                # Sin output en el intervalo — salimos si el proceso terminó
                if session.finished or session.process.returncode is not None:
                    return lines, True
                break

        finished = session.finished or session.process.returncode is not None
        return lines, finished


# Instancia global — importar desde aquí
sessions = SessionManager()
