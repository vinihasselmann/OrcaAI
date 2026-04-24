"""Mapeamento de registros importados para a aba '2A. Lista de Pecas'."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.models.schema import DocumentoImportado, MapeamentoExcel

TIPOS_SUPORTADOS = (
    "geral_pecas",
    "geral_pecas_genericas",
    "geral_pecas_alveolares",
)

ABA_PRINCIPAL = "2A. Lista de Peças"
MODO_APPEND_SEGURO = "append_seguro"
MODO_ATUALIZAR_IDENTIFICADOR = "atualizar_por_identificador"  # futuro
COLUNAS_ZERO_FIXO = (
    "Z",
    "AA",
    "AB",
    "AC",
    "AD",
    "AI",
    "AJ",
    "AK",
    "AL",
    "AM",
    "AN",
    "AO",
    "AP",
)


class FieldMapperError(Exception):
    """Erro de mapeamento entre registro importado e planilha Excel."""


# Regras em tipos primitivos para facilitar migracao futura para JSON/YAML.
MAPPING_RULES: dict[str, dict[str, Any]] = {
    "geral_pecas": {
        "aba_destino": ABA_PRINCIPAL,
        "modo_escrita": MODO_APPEND_SEGURO,
        "chave_busca_linha": ["codigo_montagem", "modelo", "marca_tipo"],
        "mapeamento_colunas": {
            # Colunas base (solicitadas)
            "codigo_montagem": "J",
            "modelo": "K",
            "marca_tipo": "L",
            "largura_preo_m": "M",
            "altura_preo_m": "N",
            "taxa_ca_kg_m3": "P",
            "taxa_cp_kg_m3": "Q",
            "comprimento_maximo_m": "S",
            "quantidade": "V",
            "comprimento_total_m": "W",
            "area_total_m2": "X",
            "volume_total_m3": "Y",
            # Complementos (quando existentes)
            "parte_1_comprimento_m": "AA",
            "parte_2_comprimento_m": "AB",
            "parte_3_comprimento_m": "AC",
            "parte_4_comprimento_m": "AD",
            "continuidade_quantidade": "AE",
            "continuidade_bitola": "AF",
            "condutor_pluvial_diametro": "AH",
        },
    },
    "geral_pecas_genericas": {
        "aba_destino": ABA_PRINCIPAL,
        "modo_escrita": MODO_APPEND_SEGURO,
        "chave_busca_linha": ["codigo_montagem", "modelo", "marca_tipo"],
        "mapeamento_colunas": {
            "codigo_montagem": "J",
            "modelo": "K",
            "marca_tipo": "L",
            "largura_preo_m": "M",
            "taxa_ca_kg_m3": "P",
            "taxa_cp_kg_m3": "Q",
            "laje_vao_m": "S",
            "quantidade": "V",
            "comprimento_total_m": "W",
            "area_total_m2": "X",
            "volume_total_m3": "Y",
            # Complementos (quando existentes)
            "espessura_equivalente_cm": "AE",
            "distribuicao_cabos": "AF",
            "volume_preenchimento_alveolo_m3": "AH",
        },
    },
    "geral_pecas_alveolares": {
        "aba_destino": ABA_PRINCIPAL,
        "modo_escrita": MODO_APPEND_SEGURO,
        "chave_busca_linha": ["codigo_montagem", "modelo", "marca_tipo"],
        "mapeamento_colunas": {
            "codigo_montagem": "J",
            "modelo": "K",
            "marca_tipo": "L",
            "taxa_ca_kg_m3": "P",
            "taxa_cp_kg_m3": "Q",
            "comprimento_maximo_m": "S",
            "quantidade": "V",
            "comprimento_total_m": "W",
            "area_total_m2": "X",
            "volume_total_m3": "Y",
        },
    },
}


def _as_dict(registro: Any) -> dict[str, Any]:
    """Converte registro model/dict para dicionario."""
    if hasattr(registro, "model_dump"):
        return dict(registro.model_dump())
    if isinstance(registro, dict):
        return dict(registro)
    raise FieldMapperError(f"Tipo de registro nao suportado: {type(registro)}")


def _coagir_valor_excel(valor: Any) -> str | float | int | None:
    """Coage valor para tipos aceitos no mapeamento."""
    if valor is None:
        return None
    if isinstance(valor, bool):
        return int(valor)
    if isinstance(valor, (str, float, int)):
        return valor
    return str(valor)


def _normalizar_identificador(valor: Any) -> str:
    """Normaliza texto para indices internos."""
    if valor is None:
        return ""
    return str(valor).strip().lower()


def gerar_identificador_registro(registro: Any) -> str:
    """Gera identificador tecnico com prioridade:

    1) codigo_montagem
    2) modelo + marca_tipo
    3) marca_tipo
    """
    dados = _as_dict(registro)

    codigo = str(dados.get("codigo_montagem") or "").strip()
    if codigo:
        return codigo

    modelo = str(dados.get("modelo") or "").strip()
    marca = str(dados.get("marca_tipo") or "").strip()
    if modelo and marca:
        return f"{modelo}|{marca}"
    if marca:
        return marca

    raise FieldMapperError(
        "Nao foi possivel gerar identificador do registro. "
        "Informe codigo_montagem, ou modelo+marca_tipo, ou marca_tipo."
    )


def obter_regras_mapeamento(tipo_arquivo: str) -> dict[str, Any]:
    """Retorna regras de mapeamento por tipo de arquivo."""
    if tipo_arquivo not in TIPOS_SUPORTADOS:
        raise FieldMapperError(f"Tipo de arquivo nao suportado: {tipo_arquivo}")
    return deepcopy(MAPPING_RULES[tipo_arquivo])


def transformar_registro_em_colunas_alvo(
    registro: Any,
    regras: dict[str, Any],
) -> dict[str, str | float | int | None]:
    """Transforma registro importado em dicionario `{coluna_excel: valor}`."""
    dados = _as_dict(registro)
    mapa_colunas = regras.get("mapeamento_colunas", {})
    if not isinstance(mapa_colunas, dict) or not mapa_colunas:
        raise FieldMapperError("Regras sem 'mapeamento_colunas' validas.")

    colunas_alvo: dict[str, str | float | int | None] = {}
    for campo_origem, coluna_destino in mapa_colunas.items():
        coluna = str(coluna_destino or "").strip().upper()
        if not coluna:
            continue
        valor = _coagir_valor_excel(dados.get(campo_origem))
        # Em modo append seguro, so escreve quando ha valor explicitamente informado.
        if valor is None:
            continue
        colunas_alvo[coluna] = valor

    return colunas_alvo


def _aplicar_colunas_zero_fixo(
    colunas_alvo: dict[str, str | float | int | None],
) -> dict[str, str | float | int | None]:
    """Garante preenchimento padrao com zero em colunas tecnicas fixas."""
    resultado = dict(colunas_alvo)
    for coluna in COLUNAS_ZERO_FIXO:
        resultado[coluna] = 0
    return resultado


def gerar_proxima_linha_disponivel(
    contexto_planilha: dict[str, Any],
    aba_destino: str = ABA_PRINCIPAL,
) -> int:
    """Retorna a proxima linha disponivel para append seguro."""
    proxima = (
        contexto_planilha.get("proxima_linha_por_aba", {}).get(aba_destino)
        if isinstance(contexto_planilha, dict)
        else None
    )
    if isinstance(proxima, int) and proxima > 0:
        return proxima

    max_linha = (
        contexto_planilha.get("max_linha_por_aba", {}).get(aba_destino)
        if isinstance(contexto_planilha, dict)
        else None
    )
    if isinstance(max_linha, int) and max_linha > 0:
        return max_linha + 1

    # Fallback conservador (linha 1 geralmente cabecalho).
    return 2


def _resolver_linha_destino(
    registro: Any,
    regras: dict[str, Any],
    contexto_planilha: dict[str, Any],
    fallback_append_row: int,
) -> int:
    """Resolve linha de destino.

    Atualmente usa append seguro.
    Mantem estrutura preparada para atualizacao por identificador.
    """
    modo = str(regras.get("modo_escrita") or MODO_APPEND_SEGURO).strip().lower()
    aba_destino = str(regras.get("aba_destino") or ABA_PRINCIPAL).strip()

    if modo == MODO_ATUALIZAR_IDENTIFICADOR:
        # Futuro: atualizar linha existente por identificador
        ident = _normalizar_identificador(gerar_identificador_registro(registro))
        linha = (
            contexto_planilha.get("linhas_por_identificador", {})
            .get(aba_destino, {})
            .get(ident)
        )
        if isinstance(linha, int) and linha > 0:
            return linha
        return fallback_append_row

    return fallback_append_row


def mapear_registro_para_excel(
    registro: Any,
    regras: dict[str, Any],
    contexto_planilha: dict[str, Any],
    *,
    linha_destino_forcada: int | None = None,
) -> list[MapeamentoExcel]:
    """Mapeia um registro em instrucoes de escrita Excel."""
    aba_destino = str(regras.get("aba_destino") or "").strip()
    if not aba_destino:
        raise FieldMapperError("Regra invalida: 'aba_destino' obrigatoria.")

    linha_base = (
        linha_destino_forcada
        if isinstance(linha_destino_forcada, int) and linha_destino_forcada > 0
        else gerar_proxima_linha_disponivel(contexto_planilha, aba_destino)
    )
    linha_destino = _resolver_linha_destino(
        registro=registro,
        regras=regras,
        contexto_planilha=contexto_planilha,
        fallback_append_row=linha_base,
    )
    identificador = gerar_identificador_registro(registro)
    colunas_alvo = _aplicar_colunas_zero_fixo(
        transformar_registro_em_colunas_alvo(registro, regras)
    )

    instrucoes: list[MapeamentoExcel] = []
    for campo_origem, coluna_destino in regras.get("mapeamento_colunas", {}).items():
        coluna = str(coluna_destino).strip().upper()
        valor = colunas_alvo.get(coluna)

        if valor is None:
            # Nao gera instrucoes para campo sem valor.
            continue

        instrucoes.append(
            MapeamentoExcel(
                aba_destino=aba_destino,
                linha_destino=linha_destino,
                coluna_destino=coluna,
                celula_destino=f"{coluna}{linha_destino}",
                campo_origem=campo_origem,
                valor_convertido=valor,
                identificador_registro=identificador,
                permitido_escrever=True,
            )
        )

    for coluna in COLUNAS_ZERO_FIXO:
        instrucoes.append(
            MapeamentoExcel(
                aba_destino=aba_destino,
                linha_destino=linha_destino,
                coluna_destino=coluna,
                celula_destino=f"{coluna}{linha_destino}",
                campo_origem=f"zero_fixo_{coluna.lower()}",
                valor_convertido=0,
                identificador_registro=identificador,
                permitido_escrever=True,
            )
        )

    return instrucoes


def mapear_documento_para_excel(
    documento: DocumentoImportado,
    contexto_planilha: dict[str, Any],
) -> list[MapeamentoExcel]:
    """Mapeia documento completo para lista de instrucoes de escrita."""
    regras = obter_regras_mapeamento(documento.tipo_arquivo)
    aba_destino = str(regras.get("aba_destino") or ABA_PRINCIPAL).strip()
    proxima_linha = gerar_proxima_linha_disponivel(contexto_planilha, aba_destino)

    instrucoes: list[MapeamentoExcel] = []
    for registro in documento.registros:
        instrucoes.extend(
            mapear_registro_para_excel(
                registro=registro,
                regras=regras,
                contexto_planilha=contexto_planilha,
                linha_destino_forcada=proxima_linha,
            )
        )
        proxima_linha += 1

    return instrucoes
