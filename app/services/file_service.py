"""Servicos utilitarios para arquivos temporarios de upload web."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class FileServiceError(Exception):
    """Erro relacionado ao gerenciamento de arquivos de upload."""


def _sanitizar_nome_arquivo(nome: str) -> str:
    """Sanitiza nome para evitar caracteres inseguros."""
    base = Path(nome).name
    sem_espacos = re.sub(r"\s+", "_", base.strip())
    seguro = re.sub(r"[^a-zA-Z0-9._-]", "", sem_espacos)
    return seguro or "arquivo.txt"


def validar_arquivo_txt(upload: UploadFile) -> None:
    """Valida se arquivo possui extensao .txt."""
    nome = Path(upload.filename or "").name
    if not nome:
        raise FileServiceError("Arquivo sem nome informado.")
    if Path(nome).suffix.lower() != ".txt":
        raise FileServiceError(f"Arquivo invalido '{nome}'. Apenas .txt e permitido.")


def gerar_nome_unico_seguro(nome_original: str) -> str:
    """Gera nome unico e seguro para salvar arquivo temporario."""
    nome_limpo = _sanitizar_nome_arquivo(nome_original)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    token = uuid4().hex[:8]
    return f"{timestamp}_{token}_{nome_limpo}"


def salvar_upload_temporario(
    upload: UploadFile,
    *,
    pasta_temp: str | Path = "data/temp",
) -> Path:
    """Salva upload em pasta temporaria e retorna caminho final."""
    validar_arquivo_txt(upload)

    pasta = Path(pasta_temp)
    pasta.mkdir(parents=True, exist_ok=True)

    nome_arquivo = gerar_nome_unico_seguro(upload.filename or "arquivo.txt")
    caminho_final = pasta / nome_arquivo

    conteudo = upload.file.read()
    if not conteudo:
        raise FileServiceError(f"Arquivo vazio: {upload.filename}")
    caminho_final.write_bytes(conteudo)
    return caminho_final


def limpar_arquivos_temporarios(caminhos: list[Path]) -> None:
    """Remove arquivos temporarios existentes."""
    for caminho in caminhos:
        try:
            if caminho.exists() and caminho.is_file():
                caminho.unlink()
        except Exception:
            # Limpeza nunca deve quebrar o fluxo principal.
            continue

