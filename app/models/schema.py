"""Schemas pydantic para importacao tabular de pecas pre-moldadas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


def _parse_float_like(value: Any) -> float | None:
    """Converte valores textuais tabulares para float quando possivel.

    Regras:
    - `None`, string vazia, "-", "--", "n/a" viram `None`.
    - aceita formatos com virgula decimal: "12,34".
    - aceita separador de milhar com ponto: "1.234,56".
    - aceita formatos padrao com ponto decimal: "1234.56".
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return float(value)

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None

        lowered = text.lower()
        if lowered in {"-", "--", "n/a", "na", "none", "null"}:
            return None

        # Ex.: 1.234,56 -> 1234.56
        if "," in text:
            text = text.replace(".", "").replace(",", ".")

        try:
            return float(text)
        except ValueError:
            return None

    return None


class BaseSchemaImportacao(BaseModel):
    """Base para schemas de importacao com validadores comuns."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
        validate_assignment=True,
    )


class BasePeca(BaseSchemaImportacao):
    """Campos base compartilhados entre todos os tipos de peca importada."""

    arquivo_origem: str
    tipo_arquivo: str
    material: str | None = None
    quadrante_montagem: str | None = None
    codigo_montagem: str | None = None
    modelo: str | None = None
    marca_tipo: str | None = None
    quantidade: float | None = None
    comprimento_total_m: float | None = None
    area_total_m2: float | None = None
    volume_total_m3: float | None = None

    @field_validator(
        "quantidade",
        "comprimento_total_m",
        "area_total_m2",
        "volume_total_m3",
        mode="before",
    )
    @classmethod
    def _converter_numericos_base(cls, value: Any) -> float | None:
        """Converte campos numericos base para float."""
        return _parse_float_like(value)


class PecaGeral(BasePeca):
    """Schema para registros do tipo `geral_pecas`."""

    largura_preo_m: float | None = None
    altura_preo_m: float | None = None
    taxa_ca_kg_m3: float | None = None
    taxa_cp_kg_m3: float | None = None
    altura_engastamento_m: float | None = None
    variacao_comprimento_total_cm: str | None = None
    comprimento_maximo_m: float | None = None
    parte_1_comprimento_m: float | None = None
    parte_2_comprimento_m: float | None = None
    parte_3_comprimento_m: float | None = None
    parte_4_comprimento_m: float | None = None
    continuidade_quantidade: float | None = None
    continuidade_bitola: str | None = None
    aterramento_visibilidade: str | None = None
    condutor_pluvial_diametro: str | None = None

    @field_validator(
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
        mode="before",
    )
    @classmethod
    def _converter_numericos(cls, value: Any) -> float | None:
        """Converte campos numericos de `PecaGeral` para float."""
        return _parse_float_like(value)


class PecaGenerica(BasePeca):
    """Schema para registros do tipo `geral_pecas_genericas`."""

    largura_preo_m: float | None = None
    altura_preo_m: float | None = None
    espessura_equivalente_cm: float | None = None
    taxa_ca_kg_m3: float | None = None
    taxa_cp_kg_m3: float | None = None
    distribuicao_cabos: str | None = None
    laje_vao_m: float | None = None
    volume_preenchimento_alveolo_m3: float | None = None

    @field_validator(
        "largura_preo_m",
        "altura_preo_m",
        "espessura_equivalente_cm",
        "taxa_ca_kg_m3",
        "taxa_cp_kg_m3",
        "laje_vao_m",
        "volume_preenchimento_alveolo_m3",
        mode="before",
    )
    @classmethod
    def _converter_numericos(cls, value: Any) -> float | None:
        """Converte campos numericos de `PecaGenerica` para float."""
        return _parse_float_like(value)


class PecaAlveolar(BasePeca):
    """Schema para registros do tipo `geral_pecas_alveolares`."""

    taxa_ca_kg_m3: float | None = None
    taxa_cp_kg_m3: float | None = None
    variacao_comprimento_cm: str | None = None
    comprimento_maximo_m: float | None = None

    @field_validator(
        "taxa_ca_kg_m3",
        "taxa_cp_kg_m3",
        "comprimento_maximo_m",
        mode="before",
    )
    @classmethod
    def _converter_numericos(cls, value: Any) -> float | None:
        """Converte campos numericos de `PecaAlveolar` para float."""
        return _parse_float_like(value)


class DocumentoImportado(BaseSchemaImportacao):
    """Representa o documento bruto importado do arquivo tabular."""

    arquivo_origem: str
    tipo_arquivo: str
    cabecalhos_originais: list[str]
    registros: list[Any]


class MapeamentoExcel(BaseSchemaImportacao):
    """Representa o mapeamento de um campo importado para a planilha Excel."""

    aba_destino: str
    linha_destino: int | None = None
    coluna_destino: str | None = None
    celula_destino: str | None = None
    campo_origem: str
    valor_convertido: str | float | int | None
    identificador_registro: str
    permitido_escrever: bool = False

    @field_validator("linha_destino", mode="before")
    @classmethod
    def _validar_linha_destino(cls, value: Any) -> int | None:
        """Normaliza `linha_destino` para inteiro positivo quando informado."""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        line = int(value)
        if line <= 0:
            raise ValueError("linha_destino deve ser maior que zero.")
        return line

    @field_validator("coluna_destino", mode="before")
    @classmethod
    def _normalizar_coluna_destino(cls, value: Any) -> str | None:
        """Normaliza coluna do Excel para maiusculo quando informado."""
        if value is None:
            return None
        text = str(value).strip()
        return text.upper() or None


class RegraImportacao(BaseSchemaImportacao):
    """Define regras de importacao por tipo de arquivo tabular."""

    tipo_arquivo: str
    chave_identificacao: str
    campos_obrigatorios: list[str]
    campos_numericos: list[str]
    campos_texto: list[str]
