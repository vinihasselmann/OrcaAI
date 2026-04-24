from __future__ import annotations

from app.models.schema import DocumentoImportado, MapeamentoExcel, PecaGeral
from app.services.validator import (
    validar_documento_importado,
    validar_escrita_em_coluna,
    validar_mapeamento,
    validar_registro,
)


def test_validar_registro_detecta_valores_invalidos() -> None:
    registro = PecaGeral(
        arquivo_origem="a.txt",
        tipo_arquivo="geral_pecas",
        codigo_montagem="",
        modelo="",
        marca_tipo="",
        quantidade=-1,
        comprimento_total_m=-2,
        area_total_m2=-3,
        volume_total_m3=-4,
    )
    erros = validar_registro(registro, "geral_pecas")

    assert any("identificacao minima" in e for e in erros)
    assert any("nao pode ser negativo" in e for e in erros)


def test_validar_documento_importado_ok() -> None:
    registro = PecaGeral(
        arquivo_origem="a.txt",
        tipo_arquivo="geral_pecas",
        codigo_montagem="CM-001",
        quantidade=1,
        comprimento_total_m=1,
        area_total_m2=1,
        volume_total_m3=1,
    )
    doc = DocumentoImportado(
        arquivo_origem="a.txt",
        tipo_arquivo="geral_pecas",
        cabecalhos_originais=["codigo_montagem"],
        registros=[registro],
    )
    erros = validar_documento_importado(doc)
    assert erros == []


def test_validar_escrita_em_coluna_bloqueia_coluna_invalida_e_formula() -> None:
    erros = validar_escrita_em_coluna(
        coluna_destino="D",
        valor="=A1+B1",
        campo_origem="codigo_montagem",
        possui_formula_destino=True,
    )
    assert any("nao permitida" in e for e in erros)
    assert any("formula" in e.lower() for e in erros)


def test_validar_mapeamento_exige_aba_mvp() -> None:
    m = MapeamentoExcel(
        aba_destino="Resumo",
        linha_destino=2,
        coluna_destino="J",
        celula_destino="J2",
        campo_origem="codigo_montagem",
        valor_convertido="CM-001",
        identificador_registro="CM-001",
        permitido_escrever=True,
    )
    erros = validar_mapeamento(m)
    assert any("2A. Lista de Pe" in e for e in erros)


def test_validar_escrita_em_coluna_aceita_colunas_zero_fixo() -> None:
    erros = validar_escrita_em_coluna(
        coluna_destino="AP",
        valor=0,
        campo_origem="zero_fixo_ap",
        possui_formula_destino=False,
    )
    assert erros == []
