"""Validacoes de integridade para importacao na aba '2A. Lista de Pecas'."""

from __future__ import annotations

import re
from typing import Any

from app.models.schema import DocumentoImportado, MapeamentoExcel
from app.services.field_mapper import ABA_PRINCIPAL, COLUNAS_ZERO_FIXO, MAPPING_RULES

TIPOS_SUPORTADOS = (
    "geral_pecas",
    "geral_pecas_auxiliares",
    "geral_pecas_genericas",
    "geral_pecas_alveolares",
)

CELULA_REGEX = re.compile(r"^[A-Z]+[1-9]\d*$")
COLUNA_REGEX = re.compile(r"^[A-Z]+$")

NUMERIC_FIELDS = {
    "quantidade",
    "comprimento_total_m",
    "area_total_m2",
    "volume_total_m3",
    "largura_preo_m",
    "altura_preo_m",
    "taxa_ca_kg_m3",
    "taxa_cp_kg_m3",
    "altura_engastamento_m",
    "comprimento_maximo_m",
    "parte_1_comprimento_m",
    "parte_2_comprimento_m",
    "parte_3_comprimento_m",
    "parte_4_comprimento_m",
    "continuidade_quantidade",
    "espessura_equivalente_cm",
    "laje_vao_m",
    "volume_preenchimento_alveolo_m3",
}

FIELDS_NAO_NEGATIVOS = {
    "taxa_ca_kg_m3",
    "taxa_cp_kg_m3",
    "quantidade",
    "comprimento_total_m",
    "area_total_m2",
    "volume_total_m3",
}

COLUNAS_IDENTIFICACAO = {"B", "J", "K", "L"}


def _as_dict(obj: Any) -> dict[str, Any]:
    """Converte model/dict para dicionario simples."""
    if hasattr(obj, "model_dump"):
        return dict(obj.model_dump())
    if isinstance(obj, dict):
        return dict(obj)
    raise TypeError(f"Tipo nao suportado para validacao: {type(obj)}")


def _is_blank(valor: Any) -> bool:
    """Retorna True para vazio/nulo."""
    if valor is None:
        return True
    if isinstance(valor, str) and not valor.strip():
        return True
    return False


def _is_number(valor: Any) -> bool:
    """Retorna True para numero (int/float, exceto bool)."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _campos_mapeados_por_tipo(tipo_arquivo: str) -> set[str]:
    """Retorna campos mapeados no field mapper para o tipo informado."""
    regra = MAPPING_RULES.get(tipo_arquivo, {})
    mapa = regra.get("mapeamento_colunas", {})
    return {str(c).strip() for c in mapa.keys() if str(c).strip()}


def _colunas_permitidas() -> set[str]:
    """Conjunto de colunas permitidas no MVP."""
    cols: set[str] = {"B", "J", "K", "L", "M", "N", "P", "Q", "S", "V", "W", "X", "Y"}
    cols.update(COLUNAS_ZERO_FIXO)
    for regra in MAPPING_RULES.values():
        for col in regra.get("mapeamento_colunas", {}).values():
            if col:
                cols.add(str(col).strip().upper())
    return cols


def _coluna_espera_numero(campo_origem: str, coluna: str) -> bool:
    """Determina se a coluna/campo deve receber numero."""
    if campo_origem in NUMERIC_FIELDS:
        return True
    # Colunas-base numericas da lista de pecas
    if coluna in {"M", "N", "P", "Q", "S", "V", "W", "X", "Y", *COLUNAS_ZERO_FIXO}:
        return True
    return False


def validar_registro(registro: Any, tipo_arquivo: str) -> list[str]:
    """Valida registro importado para escrita segura."""
    erros: list[str] = []
    dados = _as_dict(registro)

    codigo = str(dados.get("codigo_montagem") or "").strip()
    modelo = str(dados.get("modelo") or "").strip()
    marca = str(dados.get("marca_tipo") or "").strip()
    if not codigo and not modelo and not marca:
        erros.append(
            "Registro sem identificacao minima. Informe ao menos "
            "'codigo_montagem' ou 'modelo' ou 'marca_tipo'."
        )

    campos_tipo = _campos_mapeados_por_tipo(tipo_arquivo)

    # Quantidade quando aplicavel (campo mapeado e valor informado)
    if "quantidade" in campos_tipo:
        qtd = dados.get("quantidade")
        if qtd is not None and not _is_number(qtd):
            erros.append("Campo 'quantidade' invalido: deve ser numerico.")

    # Pelo menos um acumulador tecnico quando aplicavel
    campos_acumuladores = [
        c
        for c in ("comprimento_total_m", "area_total_m2", "volume_total_m3")
        if c in campos_tipo
    ]
    if campos_acumuladores:
        if all(_is_blank(dados.get(c)) for c in campos_acumuladores):
            erros.append(
                "Registro sem acumuladores tecnicos. Informe ao menos um entre "
                "'comprimento_total_m', 'area_total_m2' ou 'volume_total_m3'."
            )

    for campo in NUMERIC_FIELDS:
        if campo not in campos_tipo:
            continue
        valor = dados.get(campo)
        if valor is None:
            continue
        if not _is_number(valor):
            erros.append(f"Campo numerico invalido: '{campo}' = '{valor}'.")

    for campo in FIELDS_NAO_NEGATIVOS:
        if campo not in campos_tipo:
            continue
        valor = dados.get(campo)
        if valor is None:
            continue
        if _is_number(valor) and valor < 0:
            erros.append(f"Campo '{campo}' nao pode ser negativo: {valor}.")

    return erros


def validar_documento_importado(documento: DocumentoImportado) -> list[str]:
    """Valida integridade global do documento importado."""
    erros: list[str] = []

    if documento.tipo_arquivo not in TIPOS_SUPORTADOS:
        erros.append(
            f"Tipo de arquivo nao reconhecido: '{documento.tipo_arquivo}'. "
            f"Tipos aceitos: {', '.join(TIPOS_SUPORTADOS)}."
        )

    if not documento.cabecalhos_originais:
        erros.append("Documento sem cabecalhos originais.")

    if not documento.registros:
        erros.append("Documento sem registros para processar.")
        return erros

    for idx, registro in enumerate(documento.registros, start=1):
        for erro in validar_registro(registro, documento.tipo_arquivo):
            erros.append(f"Registro {idx}: {erro}")

    return erros


def validar_escrita_em_coluna(
    coluna_destino: str,
    valor: Any,
    *,
    campo_origem: str | None = None,
    possui_formula_destino: bool = False,
) -> list[str]:
    """Valida seguranca da escrita em uma coluna/celula especifica."""
    erros: list[str] = []
    coluna = str(coluna_destino or "").strip().upper()
    colunas_permitidas = _colunas_permitidas()

    if not coluna:
        erros.append("Coluna destino vazia.")
        return erros

    if not COLUNA_REGEX.match(coluna):
        erros.append(f"Coluna destino invalida: '{coluna_destino}'.")
        return erros

    if coluna not in colunas_permitidas:
        erros.append(
            f"Coluna '{coluna}' nao permitida para escrita no MVP da aba "
            f"'{ABA_PRINCIPAL}'."
        )

    if possui_formula_destino:
        erros.append(
            f"Coluna '{coluna}' aponta para celula com formula. Escrita bloqueada."
        )

    if isinstance(valor, str) and valor.startswith("="):
        erros.append(
            f"Valor para coluna '{coluna}' parece formula ('{valor}'). Escrita bloqueada."
        )

    if _coluna_espera_numero(campo_origem or "", coluna):
        if valor is not None and not _is_number(valor):
            erros.append(
                f"Valor incompativel com coluna numerica '{coluna}': '{valor}'."
            )
        if _is_number(valor) and (campo_origem in FIELDS_NAO_NEGATIVOS or coluna in {"P", "Q", "V", "W", "X", "Y"}):
            if valor < 0:
                erros.append(f"Valor negativo nao permitido em '{coluna}': {valor}.")
    else:
        if coluna in COLUNAS_IDENTIFICACAO and _is_blank(valor):
            erros.append(
                f"Coluna de identificacao '{coluna}' nao deve receber valor vazio."
            )

    return erros


def validar_mapeamento(
    mapeamento: MapeamentoExcel,
    contexto_planilha: dict[str, Any] | None = None,
) -> list[str]:
    """Valida mapeamento individual para escrita segura."""
    erros: list[str] = []

    if _is_blank(mapeamento.aba_destino):
        erros.append("Mapeamento com 'aba_destino' vazio.")
    elif str(mapeamento.aba_destino).strip() != ABA_PRINCIPAL:
        erros.append(
            f"Aba destino invalida: '{mapeamento.aba_destino}'. "
            f"No MVP, apenas '{ABA_PRINCIPAL}' e permitida."
        )

    if _is_blank(mapeamento.campo_origem):
        erros.append("Mapeamento com 'campo_origem' vazio.")

    if _is_blank(mapeamento.identificador_registro):
        erros.append("Mapeamento com 'identificador_registro' vazio.")

    tem_celula = not _is_blank(mapeamento.celula_destino)
    tem_linha_coluna = (
        mapeamento.linha_destino is not None and not _is_blank(mapeamento.coluna_destino)
    )
    if not tem_celula and not tem_linha_coluna:
        erros.append(
            "Mapeamento sem destino. Informe 'celula_destino' ou "
            "'linha_destino + coluna_destino'."
        )

    coluna = str(mapeamento.coluna_destino or "").strip().upper()
    if not coluna and mapeamento.celula_destino:
        cel = str(mapeamento.celula_destino).strip().upper()
        if CELULA_REGEX.match(cel):
            coluna = "".join(ch for ch in cel if ch.isalpha())

    if mapeamento.celula_destino:
        cel = str(mapeamento.celula_destino).strip().upper()
        if not CELULA_REGEX.match(cel):
            erros.append(f"Referencia de celula invalida: '{mapeamento.celula_destino}'.")

    if mapeamento.linha_destino is not None and mapeamento.linha_destino <= 0:
        erros.append(f"'linha_destino' invalida: {mapeamento.linha_destino}.")

    possui_formula_destino = False
    if contexto_planilha and mapeamento.celula_destino:
        formulas = (
            contexto_planilha.get("celulas_com_formula_por_aba", {})
            .get(str(mapeamento.aba_destino), set())
        )
        possui_formula_destino = str(mapeamento.celula_destino).upper() in {
            str(item).upper() for item in formulas
        }

    erros.extend(
        validar_escrita_em_coluna(
            coluna_destino=coluna,
            valor=mapeamento.valor_convertido,
            campo_origem=mapeamento.campo_origem,
            possui_formula_destino=possui_formula_destino,
        )
    )

    if mapeamento.permitido_escrever is False:
        erros.append(
            "Mapeamento nao autorizado para escrita ('permitido_escrever=False')."
        )

    return erros


def validar_lista_mapeamentos(
    mapeamentos: list[MapeamentoExcel],
    contexto_planilha: dict[str, Any] | None = None,
) -> list[str]:
    """Valida lista completa de mapeamentos."""
    erros: list[str] = []

    if not isinstance(mapeamentos, list):
        return ["Parametro 'mapeamentos' deve ser uma lista."]
    if not mapeamentos:
        return ["Lista de mapeamentos vazia."]

    for idx, mapeamento in enumerate(mapeamentos, start=1):
        erros_item = validar_mapeamento(mapeamento, contexto_planilha=contexto_planilha)
        for erro in erros_item:
            erros.append(f"Mapeamento {idx}: {erro}")
    return erros
