from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from app.models.schema import MapeamentoExcel
from app.services.excel_writer import aplicar_mapeamentos_excel
from tests.conftest import criar_template_base


def test_escrita_segura_excel_append_sem_sobrescrever_formula(tmp_path: Path) -> None:
    template = criar_template_base(tmp_path / "orcamento_base.xlsx")
    output_dir = tmp_path / "output"

    # Coloca formula na proxima linha para validar bloqueio.
    wb = load_workbook(template)
    ws = wb["2A. Lista de Peças"]
    ws["K3"] = "=A1+B1"
    wb.save(template)
    wb.close()

    mapeamentos = [
        MapeamentoExcel(
            aba_destino="2A. Lista de Peças",
            linha_destino=999,  # writer usa append seguro e ignora sobrescrita direta
            coluna_destino="J",
            celula_destino="J999",
            campo_origem="codigo_montagem",
            valor_convertido="CM-NOVO",
            identificador_registro="CM-NOVO",
            permitido_escrever=True,
        ),
        MapeamentoExcel(
            aba_destino="2A. Lista de Peças",
            linha_destino=999,
            coluna_destino="K",
            celula_destino="K999",
            campo_origem="modelo",
            valor_convertido="MOD-NOVO",
            identificador_registro="CM-NOVO",
            permitido_escrever=True,
        ),
        MapeamentoExcel(
            aba_destino="2A. Lista de Peças",
            linha_destino=999,
            coluna_destino="D",  # nao permitida
            celula_destino="D999",
            campo_origem="campo_invalido",
            valor_convertido="NAO",
            identificador_registro="CM-NOVO",
            permitido_escrever=True,
        ),
    ]

    resultado = aplicar_mapeamentos_excel(
        caminho_planilha=template,
        mapeamentos=mapeamentos,
        output_dir=output_dir,
        criar_backup=False,
    )

    assert resultado.celulas_escritas == 2
    assert resultado.linhas_inseridas == 1
    assert resultado.total_ignorados >= 1
    assert resultado.arquivo_saida.exists()

    wb_out = load_workbook(resultado.arquivo_saida, data_only=False)
    ws_out = wb_out["2A. Lista de Peças"]
    # Como K3 possui formula, a proxima linha disponivel para append e a 4.
    assert ws_out["J4"].value == "CM-NOVO"
    assert ws_out["K4"].value == "MOD-NOVO"
    assert ws_out["K3"].value == "=A1+B1"  # formula preservada
    wb_out.close()
