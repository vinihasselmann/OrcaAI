"""Ponto de entrada da aplicacao via linha de comando."""

from __future__ import annotations

import argparse
import logging

from app.agents.budget_agent import BudgetAgent, BudgetAgentError
from app.config import settings


def _configurar_logging() -> None:
    """Configura logs amigaveis para terminal."""
    nivel = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _criar_parser_argumentos() -> argparse.ArgumentParser:
    """Cria parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        prog="orcamento-ai",
        description="Importador tecnico de arquivos TXT para planilha Excel existente.",
    )
    parser.add_argument(
        "--txt",
        required=True,
        action="append",
        help=(
            "Caminho de arquivo .txt de entrada. "
            "Use --txt repetidas vezes para importar varios arquivos."
        ),
    )
    parser.add_argument(
        "--xlsx",
        required=True,
        help="Caminho da planilha .xlsx existente (ex.: data/templates/orcamento.xlsx).",
    )
    return parser


def main() -> None:
    """Executa o fluxo principal do agente via CLI."""
    _configurar_logging()
    parser = _criar_parser_argumentos()
    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    logger.info("Iniciando %s...", settings.app_name)
    logger.info("Arquivos TXT: %s", args.txt)
    logger.info("Arquivo XLSX: %s", args.xlsx)

    agente = BudgetAgent()
    try:
        resultado = agente.processar_arquivos_txt(
            lista_arquivos=args.txt,
            caminho_template_excel=args.xlsx,
        )
    except BudgetAgentError as exc:
        logger.error("Processamento interrompido com seguranca: %s", exc)
        raise SystemExit(1) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Erro inesperado durante processamento: %s", exc)
        raise SystemExit(1) from exc

    logger.info("Resumo da operacao:")
    logger.info("- Arquivos TXT processados: %s", resultado.total_arquivos)
    logger.info("- Documentos validados: %s", resultado.total_documentos_validos)
    logger.info("- Registros importados: %s", resultado.total_registros)
    logger.info("- Mapeamentos gerados: %s", resultado.total_mapeamentos)
    logger.info("- Linhas inseridas: %s", resultado.linhas_inseridas)
    logger.info("- Celulas escritas: %s", resultado.celulas_escritas)
    logger.info("- Escritas aplicadas: %s", resultado.total_escritos)
    logger.info("- Mapeamentos ignorados: %s", resultado.total_ignorados)
    logger.info("- Erros de escrita: %s", resultado.total_erros_escrita)
    logger.info("- Backup criado: %s", resultado.arquivo_backup)
    logger.info("- Arquivo final: %s", resultado.arquivo_saida)
    logger.info("Finalizado com sucesso.")


if __name__ == "__main__":
    main()
