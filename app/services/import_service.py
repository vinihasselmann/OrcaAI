"""Servico de orquestracao do processamento web de importacao."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fastapi import UploadFile

from app.agents.budget_agent import BudgetAgent, BudgetAgentError
from app.services.file_service import (
    FileServiceError,
    limpar_arquivos_temporarios,
    salvar_upload_temporario,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImportServiceResult:
    """Resultado padronizado para retorno em interface web."""

    sucesso: bool
    erros: list[str]
    nome_arquivo_gerado: str | None
    resumo: dict[str, Any] | None


def _resultado_para_resumo(resultado: Any) -> dict[str, Any]:
    """Converte resultado do agente em resumo padronizado."""
    return {
        "total_arquivos": resultado.total_arquivos,
        "total_documentos_validos": resultado.total_documentos_validos,
        "total_registros": resultado.total_registros,
        "total_mapeamentos": resultado.total_mapeamentos,
        "linhas_inseridas": resultado.linhas_inseridas,
        "celulas_escritas": resultado.celulas_escritas,
        "total_ignorados": resultado.total_ignorados,
        "total_erros_escrita": resultado.total_erros_escrita,
    }


def processar_uploads_web(
    uploads: list[UploadFile],
    caminho_template_excel: str | Path,
    *,
    pasta_temp: str | Path = "data/temp",
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> ImportServiceResult:
    """Processa uploads web de TXT e retorna resultado padronizado."""
    uploads_validos = [item for item in uploads if item and item.filename]
    if not uploads_validos:
        return ImportServiceResult(
            sucesso=False,
            erros=["Envie ao menos 1 arquivo .txt para processar."],
            nome_arquivo_gerado=None,
            resumo=None,
        )
    if len(uploads_validos) > 4:
        return ImportServiceResult(
            sucesso=False,
            erros=["Envie no maximo 4 arquivos .txt por processamento."],
            nome_arquivo_gerado=None,
            resumo=None,
        )

    caminhos_temporarios: list[Path] = []
    try:
        for upload in uploads_validos:
            caminhos_temporarios.append(
                salvar_upload_temporario(upload=upload, pasta_temp=pasta_temp)
            )

        agente = BudgetAgent()
        resultado = agente.processar_arquivos_txt(
            lista_arquivos=caminhos_temporarios,
            caminho_template_excel=caminho_template_excel,
            progress_callback=progress_callback,
        )

        resumo = _resultado_para_resumo(resultado)
        return ImportServiceResult(
            sucesso=True,
            erros=[],
            nome_arquivo_gerado=resultado.arquivo_saida.name,
            resumo=resumo,
        )
    except (FileServiceError, BudgetAgentError) as exc:
        return ImportServiceResult(
            sucesso=False,
            erros=[str(exc)],
            nome_arquivo_gerado=None,
            resumo=None,
        )
    except Exception as exc:
        logger.exception("Erro inesperado no processar_uploads_web: %s", exc)
        return ImportServiceResult(
            sucesso=False,
            erros=[
                "Erro inesperado durante o processamento. "
                "Verifique os arquivos e tente novamente. "
                f"Detalhe tecnico: {exc}"
            ],
            nome_arquivo_gerado=None,
            resumo=None,
        )
    finally:
        limpar_arquivos_temporarios(caminhos_temporarios)


def processar_caminhos_txt_web(
    caminhos_txt: list[str | Path],
    caminho_template_excel: str | Path,
    *,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> ImportServiceResult:
    """Processa lista de caminhos TXT já persistidos em disco."""
    if not caminhos_txt:
        return ImportServiceResult(
            sucesso=False,
            erros=["Envie ao menos 1 arquivo .txt para processar."],
            nome_arquivo_gerado=None,
            resumo=None,
        )
    if len(caminhos_txt) > 4:
        return ImportServiceResult(
            sucesso=False,
            erros=["Envie no maximo 4 arquivos .txt por processamento."],
            nome_arquivo_gerado=None,
            resumo=None,
        )

    try:
        agente = BudgetAgent()
        resultado = agente.processar_arquivos_txt(
            lista_arquivos=[Path(item) for item in caminhos_txt],
            caminho_template_excel=caminho_template_excel,
            progress_callback=progress_callback,
        )
        return ImportServiceResult(
            sucesso=True,
            erros=[],
            nome_arquivo_gerado=resultado.arquivo_saida.name,
            resumo=_resultado_para_resumo(resultado),
        )
    except (FileServiceError, BudgetAgentError) as exc:
        return ImportServiceResult(
            sucesso=False,
            erros=[str(exc)],
            nome_arquivo_gerado=None,
            resumo=None,
        )
    except Exception as exc:
        logger.exception("Erro inesperado no processar_caminhos_txt_web: %s", exc)
        return ImportServiceResult(
            sucesso=False,
            erros=[
                "Erro inesperado durante o processamento. "
                "Verifique os arquivos e tente novamente. "
                f"Detalhe tecnico: {exc}"
            ],
            nome_arquivo_gerado=None,
            resumo=None,
        )
