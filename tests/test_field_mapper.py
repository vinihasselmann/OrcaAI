from __future__ import annotations

from app.models.schema import DocumentoImportado, PecaAlveolar, PecaGenerica, PecaGeral
from app.services.field_mapper import ABA_PRINCIPAL, mapear_documento_para_excel


def test_mapeamento_para_aba_2a_lista_de_pecas() -> None:
    registro = PecaGeral(
        arquivo_origem="arquivo.txt",
        tipo_arquivo="geral_pecas",
        codigo_montagem="CM-123",
        modelo="MOD-123",
        marca_tipo="TIPO-123",
        largura_preo_m=0.3,
        altura_preo_m=0.4,
        taxa_ca_kg_m3=100,
        taxa_cp_kg_m3=80,
        comprimento_maximo_m=12,
        quantidade=2,
        comprimento_total_m=24,
        area_total_m2=6.5,
        volume_total_m3=3.1,
    )
    documento = DocumentoImportado(
        arquivo_origem="arquivo.txt",
        tipo_arquivo="geral_pecas",
        cabecalhos_originais=["codigo_montagem"],
        registros=[registro],
    )
    contexto = {"proxima_linha_por_aba": {ABA_PRINCIPAL: 10}}

    mapeamentos = mapear_documento_para_excel(documento, contexto)
    assert mapeamentos
    assert all(m.aba_destino == ABA_PRINCIPAL for m in mapeamentos)
    assert all(m.linha_destino == 10 for m in mapeamentos)

    colunas = {m.coluna_destino for m in mapeamentos}
    assert {"J", "K", "L", "M", "N", "P", "Q", "S", "V", "W", "X", "Y"}.issubset(colunas)


def test_mapeamento_genericas_envia_laje_vao_para_s_e_zeros_fixos() -> None:
    registro = PecaGenerica(
        arquivo_origem="arquivo.txt",
        tipo_arquivo="geral_pecas_genericas",
        codigo_montagem="CM-G-001",
        modelo="MOD-G",
        marca_tipo="TIPO-G",
        largura_preo_m=0.3,
        taxa_ca_kg_m3=100,
        taxa_cp_kg_m3=80,
        laje_vao_m=6,
        quantidade=2,
        comprimento_total_m=12,
        area_total_m2=5,
        volume_total_m3=2,
    )
    documento = DocumentoImportado(
        arquivo_origem="arquivo.txt",
        tipo_arquivo="geral_pecas_genericas",
        cabecalhos_originais=["codigo_montagem"],
        registros=[registro],
    )

    mapeamentos = mapear_documento_para_excel(
        documento, {"proxima_linha_por_aba": {ABA_PRINCIPAL: 10}}
    )
    por_coluna = {m.coluna_destino: m.valor_convertido for m in mapeamentos}

    assert por_coluna["S"] == 6
    assert por_coluna["Z"] == 0
    assert por_coluna["AA"] == 0
    assert por_coluna["AB"] == 0
    assert por_coluna["AC"] == 0
    assert por_coluna["AD"] == 0
    assert por_coluna["AI"] == 0
    assert por_coluna["AP"] == 0


def test_mapeamento_alveolares_nao_preenche_z_com_txt_e_aplica_zeros_fixos() -> None:
    registro = PecaAlveolar(
        arquivo_origem="arquivo.txt",
        tipo_arquivo="geral_pecas_alveolares",
        codigo_montagem="CM-A-001",
        modelo="MOD-A",
        marca_tipo="TIPO-A",
        variacao_comprimento_cm="10 a 15",
        taxa_ca_kg_m3=100,
        taxa_cp_kg_m3=70,
        comprimento_maximo_m=14,
        quantidade=4,
        comprimento_total_m=56,
        area_total_m2=14,
        volume_total_m3=5,
    )
    documento = DocumentoImportado(
        arquivo_origem="arquivo.txt",
        tipo_arquivo="geral_pecas_alveolares",
        cabecalhos_originais=["codigo_montagem"],
        registros=[registro],
    )

    mapeamentos = mapear_documento_para_excel(
        documento, {"proxima_linha_por_aba": {ABA_PRINCIPAL: 10}}
    )
    por_campo = {m.campo_origem: m.coluna_destino for m in mapeamentos}
    por_coluna = {m.coluna_destino: m.valor_convertido for m in mapeamentos}

    assert "variacao_comprimento_cm" not in por_campo
    assert por_coluna["Z"] == 0
    assert por_coluna["AD"] == 0
    assert por_coluna["AI"] == 0
    assert por_coluna["AP"] == 0
