from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.web import app
import app.web as web_module
from tests.conftest import conteudo_txt_geral_pecas, criar_template_base


def _configurar_ambiente_web(tmp_path: Path, monkeypatch) -> Path:
    template = criar_template_base(tmp_path / "templates" / "orcamento_base.xlsx")
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(web_module, "TEMPLATE_XLSX_PATH", template)
    monkeypatch.setattr(web_module, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(settings, "output_dir", str(output_dir), raising=False)
    return output_dir


def test_get_root_renderiza_pagina_inicial() -> None:
    client = TestClient(app)
    resp = client.get("/")

    assert resp.status_code == 200
    assert "orcamento-ai" in resp.text
    assert "Processar orçamento" in resp.text


def test_post_processar_gera_arquivo_final_e_permite_download(tmp_path: Path, monkeypatch) -> None:
    output_dir = _configurar_ambiente_web(tmp_path, monkeypatch)
    client = TestClient(app)

    files = {
        "geral_pecas": ("0.Geral Pecas.txt", conteudo_txt_geral_pecas().encode("utf-8"), "text/plain"),
    }
    resp = client.post("/processar", files=files)

    assert resp.status_code == 200
    assert "Importação concluída" in resp.text

    match = re.search(r"/download/([^\"']+)", resp.text)
    assert match, "Link de download nao encontrado no HTML de resultado."
    nome_arquivo = match.group(1)

    arquivo_gerado = output_dir / nome_arquivo
    assert arquivo_gerado.exists()

    dl = client.get(f"/download/{nome_arquivo}")
    assert dl.status_code == 200
    assert "spreadsheetml.sheet" in dl.headers.get("content-type", "")
    assert len(dl.content) > 0

