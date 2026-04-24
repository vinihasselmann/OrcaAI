"""Parser de arquivos .txt tabulares de pecas pre-moldadas.

Formato esperado:
- primeira linha: titulo do relatorio (ignorada)
- segunda linha util: cabecalhos separados por ';'
- demais linhas: registros separados por ';'
- linhas de resumo sao descartadas
"""

from __future__ import annotations

import csv
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from app.models.schema import (
    DocumentoImportado,
    PecaAlveolar,
    PecaGenerica,
    PecaGeral,
)

logger = logging.getLogger(__name__)

TIPOS_SUPORTADOS = (
    "geral_pecas",
    "geral_pecas_auxiliares",
    "geral_pecas_genericas",
    "geral_pecas_alveolares",
)

MODEL_BY_TIPO = {
    "geral_pecas": PecaGeral,
    "geral_pecas_auxiliares": PecaGeral,
    "geral_pecas_genericas": PecaGenerica,
    "geral_pecas_alveolares": PecaAlveolar,
}

# Campos que devem permanecer texto, mesmo quando o valor parece numerico.
CAMPOS_SEMPRE_TEXTO = {
    "material",
    "quadrante_montagem",
    "codigo_montagem",
    "modelo",
    "marca_tipo",
    "distribuicao_cabos",
    "continuidade_bitola",
    "condutor_pluvial_diametro",
    "variacao_comprimento_total_cm",
    "variacao_comprimento_cm",
    "aterramento_visibilidade",
}

# Alias reais/esperados de cabecalhos por tipo de arquivo.
# A chave de cada alias passa por normalizacao (_normalizar_chave).
HEADER_ALIAS_BY_TIPO: dict[str, dict[str, str]] = {
    "geral_pecas": {
        "arquivo_origem": "arquivo_origem",
        "tipo_arquivo": "tipo_arquivo",
        "material": "material",
        "peca_material": "material",
        "quadrante_montagem": "quadrante_montagem",
        "peca_quadrante_de_montagem": "quadrante_montagem",
        "codigo_montagem": "codigo_montagem",
        "codigo_de_montagem": "codigo_montagem",
        "modelo": "modelo",
        "marca_tipo": "marca_tipo",
        "marca_de_tipo": "marca_tipo",
        "quantidade": "quantidade",
        "peca_quantidade": "quantidade",
        "comprimento_total_m": "comprimento_total_m",
        "peca_comprimento_total_m": "comprimento_total_m",
        "area_total_m2": "area_total_m2",
        "peca_area_total_m2": "area_total_m2",
        "volume_total_m3": "volume_total_m3",
        "peca_volume_total_m3": "volume_total_m3",
        "largura_preo_m": "largura_preo_m",
        "peca_largura_preo_m": "largura_preo_m",
        "altura_preo_m": "altura_preo_m",
        "peca_altura_preo_m": "altura_preo_m",
        "taxa_ca_kg_m3": "taxa_ca_kg_m3",
        "taxa_cp_kg_m3": "taxa_cp_kg_m3",
        "altura_engastamento_m": "altura_engastamento_m",
        "peca_altura_engastamento_m": "altura_engastamento_m",
        "variacao_comprimento_total_cm": "variacao_comprimento_total_cm",
        "peca_variacao_comprimento_total_cm": "variacao_comprimento_total_cm",
        "comprimento_maximo_m": "comprimento_maximo_m",
        "peca_comprimento_maximo_m": "comprimento_maximo_m",
        "parte_1_comprimento_m": "parte_1_comprimento_m",
        "parte_2_comprimento_m": "parte_2_comprimento_m",
        "parte_3_comprimento_m": "parte_3_comprimento_m",
        "parte_4_comprimento_m": "parte_4_comprimento_m",
        "continuidade_quantidade": "continuidade_quantidade",
        "continuidade_bitola": "continuidade_bitola",
        "aterramento_visibilidade": "aterramento_visibilidade",
        "condutor_pluvial_diametro": "condutor_pluvial_diametro",
        # Variacoes comuns em exportacoes
        "largura_preo": "largura_preo_m",
        "altura_preo": "altura_preo_m",
        "comprimento_total": "comprimento_total_m",
        "comprimento_maximo": "comprimento_maximo_m",
        "area_total": "area_total_m2",
        "volume_total": "volume_total_m3",
        "taxa_ca": "taxa_ca_kg_m3",
        "taxa_cp": "taxa_cp_kg_m3",
        "variacao_comprimento_total": "variacao_comprimento_total_cm",
        "continuidadade_bitola": "continuidade_bitola",
        "condutor_pluvial": "condutor_pluvial_diametro",
    },
    "geral_pecas_auxiliares": {
        "arquivo_origem": "arquivo_origem",
        "tipo_arquivo": "tipo_arquivo",
        "material": "material",
        "peca_material": "material",
        "quadrante_montagem": "quadrante_montagem",
        "peca_quadrante_de_montagem": "quadrante_montagem",
        "codigo_montagem": "codigo_montagem",
        "codigo_de_montagem": "codigo_montagem",
        "modelo": "modelo",
        "marca_tipo": "marca_tipo",
        "marca_de_tipo": "marca_tipo",
        "quantidade": "quantidade",
        "peca_quantidade": "quantidade",
        "contagem": "quantidade",
        "comprimento_total_m": "comprimento_total_m",
        "peca_comprimento_total_m": "comprimento_total_m",
        "area_total_m2": "area_total_m2",
        "peca_area_total_m2": "area_total_m2",
        "volume_total_m3": "volume_total_m3",
        "peca_volume_total_m3": "volume_total_m3",
        "largura_preo_m": "largura_preo_m",
        "peca_largura_preo_m": "largura_preo_m",
        "altura_preo_m": "altura_preo_m",
        "peca_altura_preo_m": "altura_preo_m",
        "taxa_ca_kg_m3": "taxa_ca_kg_m3",
        "taxa_cp_kg_m3": "taxa_cp_kg_m3",
        "largura_preo": "largura_preo_m",
        "altura_preo": "altura_preo_m",
        "comprimento_total": "comprimento_total_m",
        "area_total": "area_total_m2",
        "volume_total": "volume_total_m3",
        "taxa_ca": "taxa_ca_kg_m3",
        "taxa_cp": "taxa_cp_kg_m3",
    },
    "geral_pecas_genericas": {
            "arquivo_origem": "arquivo_origem",
            "tipo_arquivo": "tipo_arquivo",
            "material": "material",
            "peca_material": "material",
            "quadrante_montagem": "quadrante_montagem",
            "peca_quadrante_de_montagem": "quadrante_montagem",
            "codigo_montagem": "codigo_montagem",
            "codigo_de_montagem": "codigo_montagem",
            "modelo": "modelo",
            "marca_tipo": "marca_tipo",
            "marca_de_tipo": "marca_tipo",
            "quantidade": "quantidade",
            "peca_quantidade": "quantidade",
            "comprimento_total_m": "comprimento_total_m",
            "peca_comprimento_total_m": "comprimento_total_m",
            "area_total_m2": "area_total_m2",
            "peca_area_total_m2": "area_total_m2",
            "volume_total_m3": "volume_total_m3",
            "peca_volume_total_m3": "volume_total_m3",
            "largura_preo_m": "largura_preo_m",
            "peca_largura_preo_m": "largura_preo_m",
            "altura_preo_m": "altura_preo_m",
            "peca_altura_preo_m": "altura_preo_m",
            "espessura_equivalente_cm": "espessura_equivalente_cm",
            "taxa_ca_kg_m3": "taxa_ca_kg_m3",
            "taxa_cp_kg_m3": "taxa_cp_kg_m3",
            "distribuicao_cabos": "distribuicao_cabos",
            "laje_vao_m": "laje_vao_m",
        "volume_preenchimento_alveolo_m3": "volume_preenchimento_alveolo_m3",
        # Variacoes comuns
        "largura_preo": "largura_preo_m",
        "altura_preo": "altura_preo_m",
        "espessura_equivalente": "espessura_equivalente_cm",
        "taxa_ca": "taxa_ca_kg_m3",
        "taxa_cp": "taxa_cp_kg_m3",
        "laje_vao": "laje_vao_m",
        "volume_preenchimento_alveolo": "volume_preenchimento_alveolo_m3",
    },
    "geral_pecas_alveolares": {
        "arquivo_origem": "arquivo_origem",
        "tipo_arquivo": "tipo_arquivo",
        "material": "material",
        "peca_material": "material",
        "quadrante_montagem": "quadrante_montagem",
        "peca_quadrante_de_montagem": "quadrante_montagem",
        "codigo_montagem": "codigo_montagem",
        "codigo_de_montagem": "codigo_montagem",
        "modelo": "modelo",
        "marca_tipo": "marca_tipo",
        "marca_de_tipo": "marca_tipo",
        "quantidade": "quantidade",
        "peca_quantidade": "quantidade",
        "comprimento_total_m": "comprimento_total_m",
        "peca_comprimento_total_m": "comprimento_total_m",
        "area_total_m2": "area_total_m2",
        "peca_area_total_m2": "area_total_m2",
        "volume_total_m3": "volume_total_m3",
        "peca_volume_total_m3": "volume_total_m3",
        "taxa_ca_kg_m3": "taxa_ca_kg_m3",
        "taxa_cp_kg_m3": "taxa_cp_kg_m3",
        "variacao_comprimento_cm": "variacao_comprimento_cm",
        "peca_variacao_comprimento_cm": "variacao_comprimento_cm",
        "comprimento_maximo_m": "comprimento_maximo_m",
        "peca_comprimento_maximo_m": "comprimento_maximo_m",
        # Variacoes comuns
        "taxa_ca": "taxa_ca_kg_m3",
        "taxa_cp": "taxa_cp_kg_m3",
        "variacao_comprimento": "variacao_comprimento_cm",
        "comprimento_maximo": "comprimento_maximo_m",
    },
}

TOKENS_UNICOS_POR_TIPO: dict[str, set[str]] = {
    "geral_pecas": {
        "altura_preo_m",
        "continuidade_bitola",
        "parte_4_comprimento_m",
    },
    "geral_pecas_genericas": {
        "espessura_equivalente_cm",
        "distribuicao_cabos",
        "volume_preenchimento_alveolo_m3",
    },
    "geral_pecas_alveolares": {
        "variacao_comprimento_cm",
    },
}

TITLE_HINTS_BY_TIPO: dict[str, tuple[str, ...]] = {
    "geral_pecas_auxiliares": ("geral_pecas_auxiliares",),
    "geral_pecas_genericas": ("geral_pecas_genericas",),
    "geral_pecas_alveolares": ("geral_pecas_alveolares",),
    "geral_pecas": ("geral_pecas",),
}

NUMERO_REGEX = re.compile(r"^[+-]?(?:(?:\d{1,3}(?:\.\d{3})+)|\d+)(?:[.,]\d+)?$")


class ParserTxtError(Exception):
    """Erro de parse para importacao de arquivos txt tabulares."""


def _normalizar_chave(texto: str) -> str:
    """Normaliza cabecalhos para chave tecnica comparavel."""
    base = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(char for char in base if not unicodedata.combining(char))
    sem_acentos = sem_acentos.lower().strip()
    sem_acentos = re.sub(r"[\(\)\[\]\{\}%]", " ", sem_acentos)
    sem_acentos = re.sub(r"[^\w\s]", " ", sem_acentos)
    sem_acentos = re.sub(r"\s+", "_", sem_acentos).strip("_")
    sem_acentos = re.sub(r"_+", "_", sem_acentos)
    return sem_acentos


def _split_linha_tabular(linha: str) -> list[str]:
    """Quebra uma linha semicolon em colunas, respeitando aspas."""
    return next(csv.reader([linha], delimiter=";", quotechar='"'))


def _eh_linha_vazia(linha: str) -> bool:
    """Retorna True para linhas vazias ou apenas separadores."""
    if not linha or not linha.strip():
        return True
    conteudo = linha.replace(";", "").strip()
    return not conteudo


def _eh_linha_resumo(valores: list[str]) -> bool:
    """Detecta linhas de resumo que nao devem virar registros."""
    for valor in valores:
        if isinstance(valor, str) and _normalizar_chave(valor).startswith("total"):
            return True
    return False


def carregar_arquivo_txt(caminho: str | Path) -> list[str]:
    """Carrega um arquivo txt e devolve linhas sem quebra de linha final."""
    caminho_path = Path(caminho)
    if not caminho_path.exists():
        raise ParserTxtError(f"Arquivo nao encontrado: {caminho_path}")
    if caminho_path.suffix.lower() != ".txt":
        raise ParserTxtError(f"Arquivo invalido (esperado .txt): {caminho_path}")

    logger.info("Carregando arquivo txt: %s", caminho_path)

    raw = caminho_path.read_bytes()
    if not raw:
        raise ParserTxtError(f"Arquivo vazio: {caminho_path}")

    # Detecta BOM e/ou padrao com byte nulo comum em UTF-16.
    encodings_tentativa: list[str]
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff") or b"\x00" in raw[:200]:
        encodings_tentativa = ["utf-16", "utf-16-le", "utf-16-be", "utf-8-sig", "latin-1"]
    else:
        encodings_tentativa = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

    linhas: list[str] | None = None
    ultimo_erro: Exception | None = None
    for encoding in encodings_tentativa:
        try:
            texto = raw.decode(encoding)
            linhas = [linha.rstrip("\n\r") for linha in texto.splitlines()]
            logger.info("Arquivo lido com encoding: %s", encoding)
            break
        except UnicodeDecodeError as exc:
            ultimo_erro = exc
            continue

    if linhas is None:
        raise ParserTxtError(
            f"Nao foi possivel decodificar o arquivo: {caminho_path}. Erro: {ultimo_erro}"
        )

    if not linhas:
        raise ParserTxtError(f"Arquivo vazio: {caminho_path}")

    # Protecao extra para exportacoes UTF-16 que chegam com byte nulo no texto.
    if any("\x00" in linha for linha in linhas[:10]):
        logger.warning(
            "Texto com byte nulo detectado. Aplicando sanitizacao de '\\x00': %s",
            caminho_path,
        )
        linhas = [linha.replace("\x00", "") for linha in linhas]

    return linhas


def extrair_cabecalhos(linhas: list[str]) -> list[str]:
    """Extrai os cabecalhos da primeira linha tabular valida apos o titulo."""
    if not linhas:
        raise ParserTxtError("Nao ha linhas para extrair cabecalhos.")

    # Primeira linha do relatorio e ignorada.
    for linha in linhas[1:]:
        if _eh_linha_vazia(linha):
            continue
        colunas = [col.strip() for col in _split_linha_tabular(linha)]
        if len(colunas) <= 1:
            continue
        if any(col for col in colunas):
            logger.info("Cabecalhos extraidos com %s colunas.", len(colunas))
            return colunas

    raise ParserTxtError("Nao foi possivel identificar cabecalhos no arquivo.")


def detectar_tipo_arquivo(linhas: list[str]) -> str:
    """Detecta o tipo do arquivo com base em cabecalhos tecnicos conhecidos."""
    titulo_norm = _normalizar_chave(linhas[0]) if linhas else ""
    for tipo, hints in TITLE_HINTS_BY_TIPO.items():
        if any(hint in titulo_norm for hint in hints):
            logger.info("Tipo detectado pelo titulo: %s", tipo)
            return tipo

    cabecalhos = extrair_cabecalhos(linhas)
    cabecalhos_norm = {_normalizar_chave(c) for c in cabecalhos}

    score_por_tipo: dict[str, int] = {}
    for tipo, aliases in HEADER_ALIAS_BY_TIPO.items():
        conhecidos = set(aliases.keys())
        score_alias = len(cabecalhos_norm & conhecidos)
        score_unicos = len(cabecalhos_norm & TOKENS_UNICOS_POR_TIPO.get(tipo, set())) * 3
        score_por_tipo[tipo] = score_alias + score_unicos

    tipo_detectado = max(score_por_tipo, key=score_por_tipo.get)
    melhor_score = score_por_tipo[tipo_detectado]

    if melhor_score <= 0:
        raise ParserTxtError(
            "Nao foi possivel detectar tipo de arquivo. "
            f"Cabecalhos encontrados: {cabecalhos}"
        )

    logger.info(
        "Tipo detectado: %s (score=%s, scores=%s)",
        tipo_detectado,
        melhor_score,
        score_por_tipo,
    )
    return tipo_detectado


def normalizar_valor(valor: str) -> str | float | None:
    """Normaliza um valor tabular para integracao com schemas.

    Conversoes:
    - vazio / '-', '--', 'n/a' -> None
    - numero com ',' ou '.' decimal -> float
    - demais valores -> string limpa
    """
    if valor is None:
        return None

    texto = str(valor).strip()
    if texto == "":
        return None

    lowered = texto.lower()
    if lowered in {"-", "--", "n/a", "na", "null", "none"}:
        return None

    # Mantem strings tecnicas que contem padroes mistos (ex.: "653  ...  1006,99").
    if not NUMERO_REGEX.match(texto):
        return texto

    texto_float = texto
    if "," in texto_float and "." in texto_float:
        # padrao brasileiro: 1.234,56
        texto_float = texto_float.replace(".", "").replace(",", ".")
    elif "," in texto_float:
        # 123,45
        texto_float = texto_float.replace(",", ".")

    try:
        return float(texto_float)
    except ValueError:
        return texto


def converter_linha_em_dict(cabecalhos: list[str], linha: str) -> dict[str, str | None]:
    """Converte linha bruta tabular para dicionario com cabecalho original."""
    valores = [col.strip() for col in _split_linha_tabular(linha)]

    if len(valores) < len(cabecalhos):
        valores.extend([""] * (len(cabecalhos) - len(valores)))
    elif len(valores) > len(cabecalhos):
        valores = valores[: len(cabecalhos)]

    return dict(zip(cabecalhos, valores, strict=True))


def _resolver_campo_modelo(tipo_arquivo: str, cabecalho_original: str) -> str | None:
    """Resolve um cabecalho original para o campo tecnico do model."""
    alias = HEADER_ALIAS_BY_TIPO[tipo_arquivo]
    chave = _normalizar_chave(cabecalho_original)
    return alias.get(chave)


def _mapear_dados_para_modelo(
    tipo_arquivo: str,
    arquivo_origem: str,
    registro_bruto: dict[str, str | None],
) -> dict[str, Any]:
    """Mapeia campos do txt para nomes de campos do schema."""
    dados: dict[str, Any] = {
        "arquivo_origem": arquivo_origem,
        "tipo_arquivo": tipo_arquivo,
    }

    for cabecalho, valor in registro_bruto.items():
        campo = _resolver_campo_modelo(tipo_arquivo, cabecalho)
        if not campo:
            continue

        if campo in CAMPOS_SEMPRE_TEXTO:
            dados[campo] = None if valor is None or str(valor).strip() == "" else str(valor).strip()
            continue

        dados[campo] = normalizar_valor(valor or "")

    return dados


def _aplicar_mapeamento_posicional_por_tipo(
    tipo_arquivo: str,
    linha: str,
    dados_modelo: dict[str, Any],
) -> dict[str, Any]:
    """Aplica mapeamentos por posicao fixa quando o layout exigir."""
    dados = dict(dados_modelo)
    valores = [col.strip() for col in _split_linha_tabular(linha)]

    if tipo_arquivo == "geral_pecas_genericas":
        if len(valores) > 5 and not dados.get("largura_preo_m"):
            dados["largura_preo_m"] = normalizar_valor(valores[5])
        if len(valores) > 6 and not dados.get("altura_preo_m"):
            dados["altura_preo_m"] = normalizar_valor(valores[6])

    return dados


def parsear_registros(
    linhas: list[str],
    cabecalhos: list[str],
    tipo_arquivo: str,
    arquivo_origem: str,
) -> list[PecaGeral | PecaGenerica | PecaAlveolar]:
    """Parseia registros de dados e descarta linhas de resumo."""
    if tipo_arquivo not in TIPOS_SUPORTADOS:
        raise ParserTxtError(f"Tipo de arquivo nao suportado: {tipo_arquivo}")

    model_cls = MODEL_BY_TIPO[tipo_arquivo]
    registros: list[PecaGeral | PecaGenerica | PecaAlveolar] = []

    linha_cabecalho_encontrada = False
    for idx, linha in enumerate(linhas, start=1):
        if idx == 1:
            # titulo do relatorio
            continue
        if _eh_linha_vazia(linha):
            continue

        if not linha_cabecalho_encontrada:
            # primeira linha valida apos titulo e considerada cabecalho
            linha_cabecalho_encontrada = True
            continue

        registro_bruto = converter_linha_em_dict(cabecalhos, linha)
        valores = [str(v or "").strip() for v in registro_bruto.values()]
        if _eh_linha_resumo(valores):
            logger.info("Linha de resumo ignorada na linha %s.", idx)
            continue

        try:
            dados_modelo = _mapear_dados_para_modelo(
                tipo_arquivo=tipo_arquivo,
                arquivo_origem=arquivo_origem,
                registro_bruto=registro_bruto,
            )
            dados_modelo = _aplicar_mapeamento_posicional_por_tipo(
                tipo_arquivo=tipo_arquivo,
                linha=linha,
                dados_modelo=dados_modelo,
            )
            registros.append(model_cls(**dados_modelo))
        except Exception as exc:  # pragma: no cover - branch de protecao
            logger.error("Falha ao parsear linha %s: %s", idx, exc)
            raise ParserTxtError(f"Erro ao parsear linha {idx}: {exc}") from exc

    logger.info("Parse concluido: %s registros validos.", len(registros))
    return registros


def parsear_documento(caminho: str | Path) -> DocumentoImportado:
    """Orquestra o parse completo do documento txt em `DocumentoImportado`."""
    caminho_path = Path(caminho)
    linhas = carregar_arquivo_txt(caminho_path)
    tipo_arquivo = detectar_tipo_arquivo(linhas)
    cabecalhos = extrair_cabecalhos(linhas)
    registros = parsear_registros(
        linhas=linhas,
        cabecalhos=cabecalhos,
        tipo_arquivo=tipo_arquivo,
        arquivo_origem=caminho_path.name,
    )

    documento = DocumentoImportado(
        arquivo_origem=caminho_path.name,
        tipo_arquivo=tipo_arquivo,
        cabecalhos_originais=cabecalhos,
        registros=registros,
    )
    logger.info("Documento importado com sucesso: %s", caminho_path.name)
    return documento
