from __future__ import annotations

from pathlib import Path

from app.services.txt_parser import parsear_documento
from tests.conftest import (
    conteudo_txt_geral_pecas,
    conteudo_txt_geral_pecas_alveolares,
    conteudo_txt_geral_pecas_genericas,
)


def _gravar(tmp_path: Path, nome: str, conteudo: str) -> Path:
    caminho = tmp_path / nome
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_parser_geral_pecas(tmp_path: Path) -> None:
    arquivo = _gravar(tmp_path, "geral_pecas.txt", conteudo_txt_geral_pecas())
    doc = parsear_documento(arquivo)

    assert doc.tipo_arquivo == "geral_pecas"
    assert len(doc.registros) == 1
    assert doc.registros[0].codigo_montagem == "CM-001"
    assert doc.registros[0].quantidade == 2.0


def test_parser_geral_pecas_genericas(tmp_path: Path) -> None:
    arquivo = _gravar(tmp_path, "geral_pecas_genericas.txt", conteudo_txt_geral_pecas_genericas())
    doc = parsear_documento(arquivo)

    assert doc.tipo_arquivo == "geral_pecas_genericas"
    assert len(doc.registros) == 1
    assert doc.registros[0].espessura_equivalente_cm == 12.5
    # Deve permanecer texto tecnico.
    assert doc.registros[0].distribuicao_cabos == "653  ...  1006,99"


def test_parser_geral_pecas_alveolares(tmp_path: Path) -> None:
    arquivo = _gravar(tmp_path, "geral_pecas_alveolares.txt", conteudo_txt_geral_pecas_alveolares())
    doc = parsear_documento(arquivo)

    assert doc.tipo_arquivo == "geral_pecas_alveolares"
    assert len(doc.registros) == 1
    assert doc.registros[0].variacao_comprimento_cm == "10 a 15"
    assert doc.registros[0].comprimento_maximo_m == 14.0

