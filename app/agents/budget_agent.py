"""Agente de orquestracao do fluxo TXT -> Excel em lote."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl.utils import column_index_from_string

from app.config import settings
from app.models.schema import DocumentoImportado, MapeamentoExcel
from app.services.excel_reader import (
    abrir_workbook_existente,
    listar_abas,
    localizar_cabecalhos,
)
from app.services.excel_writer import ResultadoEscrita, aplicar_mapeamentos_excel
from app.services.field_mapper import ABA_PRINCIPAL, MAPPING_RULES, mapear_documento_para_excel
from app.services.txt_parser import parsear_documento
from app.services.validator import validar_documento_importado, validar_lista_mapeamentos

logger = logging.getLogger(__name__)

COORD_REGEX = re.compile(r"^([A-Z]+)(\d+)$")
COLUNAS_CHAVE_APPEND = ("J", "K", "L")


class BudgetAgentError(Exception):
    """Erro seguro de execucao do agente."""


@dataclass(slots=True)
class ResultadoProcessamento:
    """Resumo final da importacao."""

    arquivos_txt: list[Path]
    arquivo_xlsx_template: Path
    arquivo_saida: Path
    arquivo_backup: Path | None
    total_arquivos: int
    total_documentos_validos: int
    total_registros: int
    total_mapeamentos: int
    total_escritos: int
    total_ignorados: int
    total_erros_escrita: int
    linhas_inseridas: int
    celulas_escritas: int


class BudgetAgent:
    """Orquestra importacao tecnica de um ou mais TXT para Excel."""

    def __init__(self) -> None:
        self._logger = logger

    @staticmethod
    def _normalizar_texto(valor: Any) -> str:
        if valor is None:
            return ""
        return str(valor).strip().lower()

    @staticmethod
    def _extrair_coluna_de_coordenada(coordenada: str | None) -> str | None:
        if not coordenada:
            return None
        match = COORD_REGEX.match(coordenada.strip().upper())
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _extrair_linha_de_coordenada(coordenada: str | None) -> int | None:
        if not coordenada:
            return None
        match = COORD_REGEX.match(coordenada.strip().upper())
        if not match:
            return None
        return int(match.group(2))

    @staticmethod
    def _gerar_identificador_da_linha(
        codigo_montagem: Any,
        modelo: Any,
        marca_tipo: Any,
    ) -> str | None:
        codigo = str(codigo_montagem or "").strip()
        if codigo:
            return codigo
        model = str(modelo or "").strip()
        marca = str(marca_tipo or "").strip()
        if model and marca:
            return f"{model}|{marca}"
        if marca:
            return marca
        return None

    def _obter_campos_mapeados_por_aba(self) -> dict[str, set[str]]:
        campos_por_aba: dict[str, set[str]] = {}
        for regra in MAPPING_RULES.values():
            aba = str(regra.get("aba_destino") or "").strip()
            if not aba:
                continue
            mapa_colunas = regra.get("mapeamento_colunas", {})
            campos = {
                str(campo).strip()
                for campo in mapa_colunas.keys()
                if str(campo).strip()
            }
            campos_por_aba[aba] = campos
        return campos_por_aba

    def gerar_contexto_planilha(self, caminho_xlsx: str | Path) -> dict[str, Any]:
        """Gera contexto tecnico para mapeamento e validacoes."""
        caminho = Path(caminho_xlsx)
        workbook = abrir_workbook_existente(caminho, read_only=True, data_only=False)
        try:
            abas_disponiveis = listar_abas(workbook)
            campos_por_aba = self._obter_campos_mapeados_por_aba()

            cabecalhos_por_aba: dict[str, dict[str, str]] = {}
            indices_busca: dict[str, dict[str, dict[str, int]]] = {}
            linhas_por_identificador: dict[str, dict[str, int]] = {}
            max_linha_por_aba: dict[str, int] = {}
            proxima_linha_por_aba: dict[str, int] = {}

            for aba, campos_mapeados in campos_por_aba.items():
                if aba not in abas_disponiveis:
                    self._logger.warning("Aba de destino '%s' nao encontrada.", aba)
                    continue

                encontrados = localizar_cabecalhos(
                    workbook=workbook,
                    nome_aba=aba,
                    cabecalhos_esperados=sorted(campos_mapeados),
                    linha_inicial=1,
                    linha_final=50,
                )

                linha_cabecalho = None
                campos_coluna: dict[str, str] = {}
                for campo, coord in encontrados.items():
                    coluna = self._extrair_coluna_de_coordenada(coord)
                    if coluna:
                        campos_coluna[campo] = coluna
                    row = self._extrair_linha_de_coordenada(coord)
                    if row is not None:
                        linha_cabecalho = row if linha_cabecalho is None else min(
                            linha_cabecalho, row
                        )

                cabecalhos_por_aba[aba] = campos_coluna
                if linha_cabecalho is None:
                    self._logger.warning("Cabecalhos nao detectados na aba '%s'.", aba)
                    continue

                worksheet = workbook[aba]

                ultima_linha_com_dados = 1
                for row_num in range(2, worksheet.max_row + 1):
                    if any(
                        worksheet[f"{col}{row_num}"].value is not None
                        and str(worksheet[f"{col}{row_num}"].value).strip()
                        for col in COLUNAS_CHAVE_APPEND
                    ):
                        ultima_linha_com_dados = row_num
                max_linha_por_aba[aba] = ultima_linha_com_dados
                proxima_linha_por_aba[aba] = ultima_linha_com_dados + 1

                campos_busca: list[str] = []
                for regra in MAPPING_RULES.values():
                    if regra.get("aba_destino") == aba:
                        campos_busca = list(regra.get("chave_busca_linha", []))
                        break

                idx_por_campo: dict[str, int] = {}
                for campo in campos_busca:
                    col = campos_coluna.get(campo)
                    if col:
                        idx_por_campo[campo] = column_index_from_string(col) - 1

                aba_indices: dict[str, dict[str, int]] = {campo: {} for campo in idx_por_campo}
                aba_identificadores: dict[str, int] = {}

                for row_num, valores in enumerate(
                    worksheet.iter_rows(min_row=linha_cabecalho + 1, values_only=True),
                    start=linha_cabecalho + 1,
                ):
                    if not any(v is not None and str(v).strip() for v in valores):
                        continue

                    valores_busca: dict[str, Any] = {}
                    for campo, col_idx in idx_por_campo.items():
                        if col_idx >= len(valores):
                            continue
                        valor = valores[col_idx]
                        valores_busca[campo] = valor
                        norm = self._normalizar_texto(valor)
                        if norm and norm not in aba_indices[campo]:
                            aba_indices[campo][norm] = row_num

                    identificador = self._gerar_identificador_da_linha(
                        codigo_montagem=valores_busca.get("codigo_montagem"),
                        modelo=valores_busca.get("modelo"),
                        marca_tipo=valores_busca.get("marca_tipo"),
                    )
                    if identificador:
                        ident_norm = self._normalizar_texto(identificador)
                        if ident_norm and ident_norm not in aba_identificadores:
                            aba_identificadores[ident_norm] = row_num

                indices_busca[aba] = aba_indices
                linhas_por_identificador[aba] = aba_identificadores

            return {
                "abas_disponiveis": abas_disponiveis,
                "cabecalhos_por_aba": cabecalhos_por_aba,
                "indices_busca": indices_busca,
                "linhas_por_identificador": linhas_por_identificador,
                "max_linha_por_aba": max_linha_por_aba,
                "proxima_linha_por_aba": proxima_linha_por_aba,
            }
        finally:
            workbook.close()

    def processar_arquivo_txt(
        self,
        caminho_txt: str | Path,
        caminho_xlsx: str | Path,
    ) -> ResultadoProcessamento:
        """Compatibilidade para fluxo antigo (arquivo unico)."""
        return self.processar_arquivos_txt(
            lista_arquivos=[caminho_txt],
            caminho_template_excel=caminho_xlsx,
        )

    def processar_arquivos_txt(
        self,
        lista_arquivos: list[str | Path],
        caminho_template_excel: str | Path,
    ) -> ResultadoProcessamento:
        """Executa importacao de um ou mais TXT em um unico processamento."""
        if not lista_arquivos:
            raise BudgetAgentError("Nenhum arquivo TXT foi informado para importacao.")

        txt_paths = [Path(item) for item in lista_arquivos]
        template_path = Path(caminho_template_excel)

        self._logger.info("1/10 Recebendo lista de arquivos TXT...")
        for path in txt_paths:
            if not path.exists():
                raise BudgetAgentError(f"Arquivo TXT nao encontrado: {path}")
            if path.suffix.lower() != ".txt":
                raise BudgetAgentError(f"Arquivo invalido (esperado .txt): {path}")

        self._logger.info("2/10 Identificando tipo e parseando cada arquivo...")
        documentos: list[DocumentoImportado] = []
        for path in txt_paths:
            self._logger.info("Parseando: %s", path)
            documentos.append(parsear_documento(path))

        self._logger.info("3/10 Validando documentos importados...")
        erros_documento: list[str] = []
        for path, doc in zip(txt_paths, documentos):
            erros = validar_documento_importado(doc)
            for erro in erros:
                erros_documento.append(f"{path.name}: {erro}")
        if erros_documento:
            detalhes = "\n".join(f"- {erro}" for erro in erros_documento[:30])
            raise BudgetAgentError(
                "Falha na validacao dos documentos importados.\n"
                f"Foram encontrados {len(erros_documento)} erro(s):\n{detalhes}"
            )

        self._logger.info("4/10 Validando template Excel existente...")
        if not template_path.exists():
            raise BudgetAgentError(f"Template Excel nao encontrado: {template_path}")
        if template_path.suffix.lower() != ".xlsx":
            raise BudgetAgentError(
                f"Template invalido (esperado .xlsx): {template_path}"
            )

        self._logger.info("5/10 Gerando contexto de leitura da planilha...")
        contexto_planilha = self.gerar_contexto_planilha(template_path)
        if ABA_PRINCIPAL not in contexto_planilha.get("abas_disponiveis", []):
            raise BudgetAgentError(
                f"Aba obrigatoria '{ABA_PRINCIPAL}' nao encontrada no template."
            )

        self._logger.info("6/10 Mapeando registros para a aba '%s'...", ABA_PRINCIPAL)
        mapeamentos_totais: list[MapeamentoExcel] = []
        proxima_linha = contexto_planilha.get("proxima_linha_por_aba", {}).get(
            ABA_PRINCIPAL, 2
        )
        for doc in documentos:
            contexto_planilha.setdefault("proxima_linha_por_aba", {})[ABA_PRINCIPAL] = proxima_linha
            maps = mapear_documento_para_excel(
                documento=doc,
                contexto_planilha=contexto_planilha,
            )
            mapeamentos_totais.extend(maps)
            proxima_linha += len(doc.registros)

        if not mapeamentos_totais:
            raise BudgetAgentError("Nenhum mapeamento foi gerado para escrita.")

        self._logger.info("7/10 Validando mapeamentos...")
        erros_mapeamento = validar_lista_mapeamentos(
            mapeamentos_totais, contexto_planilha=contexto_planilha
        )
        if erros_mapeamento:
            detalhes = "\n".join(f"- {erro}" for erro in erros_mapeamento[:30])
            raise BudgetAgentError(
                "Falha na validacao dos mapeamentos.\n"
                f"Foram encontrados {len(erros_mapeamento)} erro(s):\n{detalhes}"
            )
        if not any(item.permitido_escrever for item in mapeamentos_totais):
            raise BudgetAgentError(
                "Nenhum mapeamento foi autorizado para escrita. "
                "Verifique os dados importados e colunas permitidas."
            )

        self._logger.info("8/10 Escrevendo em modo append seguro...")
        resultado_escrita: ResultadoEscrita = aplicar_mapeamentos_excel(
            caminho_planilha=template_path,
            mapeamentos=mapeamentos_totais,
            output_dir=settings.output_dir,
            criar_backup=True,
        )

        self._logger.info("9/10 Arquivo final salvo em: %s", resultado_escrita.arquivo_saida)
        self._logger.info("10/10 Importacao concluida com sucesso.")

        total_registros = sum(len(doc.registros) for doc in documentos)
        return ResultadoProcessamento(
            arquivos_txt=txt_paths,
            arquivo_xlsx_template=template_path,
            arquivo_saida=resultado_escrita.arquivo_saida,
            arquivo_backup=resultado_escrita.arquivo_backup,
            total_arquivos=len(txt_paths),
            total_documentos_validos=len(documentos),
            total_registros=total_registros,
            total_mapeamentos=resultado_escrita.total_mapeamentos,
            total_escritos=resultado_escrita.total_escritos,
            total_ignorados=resultado_escrita.total_ignorados,
            total_erros_escrita=resultado_escrita.total_erros,
            linhas_inseridas=resultado_escrita.linhas_inseridas,
            celulas_escritas=resultado_escrita.celulas_escritas,
        )
