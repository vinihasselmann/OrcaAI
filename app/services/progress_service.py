"""Gerenciamento simples de jobs de progresso para o frontend."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ProgressJob:
    """Estado serializavel de um job de processamento."""

    job_id: str
    status: str = "pending"
    phase: str = "fila"
    progress: int = 0
    message: str = "Aguardando processamento."
    logs: list[dict[str, str]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None


class ProgressService:
    """Store em memoria para acompanhar jobs de importacao."""

    def __init__(self) -> None:
        self._jobs: dict[str, ProgressJob] = {}
        self._lock = Lock()

    def create_job(self) -> ProgressJob:
        """Cria e registra um novo job."""
        job = ProgressJob(job_id=uuid4().hex)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> ProgressJob | None:
        """Retorna job pelo id."""
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        phase: str | None = None,
        progress: int | None = None,
        message: str | None = None,
        log_tone: str = "info",
        append_log: bool = True,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> ProgressJob | None:
        """Atualiza campos do job e adiciona log quando desejado."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            if status is not None:
                job.status = status
            if phase is not None:
                job.phase = phase
            if progress is not None:
                job.progress = max(0, min(100, int(progress)))
            if message is not None:
                job.message = message
                if append_log:
                    job.logs.append({"message": message, "tone": log_tone})
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            return job

    def as_payload(self, job_id: str) -> dict[str, Any] | None:
        """Serializa job para resposta JSON."""
        job = self.get_job(job_id)
        if not job:
            return None
        return {
            "job_id": job.job_id,
            "status": job.status,
            "phase": job.phase,
            "progress": job.progress,
            "message": job.message,
            "logs": list(job.logs),
            "result": job.result,
            "error": job.error,
        }
