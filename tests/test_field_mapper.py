from __future__ import annotations

from app.models.schema import DocumentoImportado, PecaGeral
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

