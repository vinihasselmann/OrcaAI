"""Interface web MVP com FastAPI + Jinja2 para importacao tecnica."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.import_service import processar_uploads_web

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

OUTPUT_DIR = Path(settings.output_dir)
TEMPLATE_XLSX_PATH = Path(settings.template_dir) / "orcamento_base.xlsx"

app = FastAPI(title="orcamento-ai", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _render_template(
    request: Request,
    nome_template: str,
    contexto: dict,
    *,
    status_code: int = 200,
) -> HTMLResponse:
    """Renderiza template com compatibilidade entre versoes de Starlette."""
    contexto_final = {"request": request, **contexto}
    try:
        return templates.TemplateResponse(
            request=request,
            name=nome_template,
            context=contexto_final,
            status_code=status_code,
        )
    except TypeError:
        # Fallback para assinaturas antigas.
        return templates.TemplateResponse(
            nome_template,
            contexto_final,
            status_code=status_code,
        )


@app.get("/", response_class=HTMLResponse)
async def pagina_inicial(request: Request) -> HTMLResponse:
    """Renderiza tela principal de upload."""
    return _render_template(
        request,
        "index.html",
        {
            "erro": None,
            "sucesso": None,
        },
    )


@app.post("/processar", response_class=HTMLResponse)
async def processar_importacao(
    request: Request,
    arquivo_geral: UploadFile | None = File(default=None),
    arquivo_genericas: UploadFile | None = File(default=None),
    arquivo_alveolares: UploadFile | None = File(default=None),
    geral_pecas: UploadFile | None = File(default=None),
    pecas_genericas: UploadFile | None = File(default=None),
    pecas_alveolares: UploadFile | None = File(default=None),
) -> HTMLResponse:
    """Recebe uploads .txt, processa e renderiza resultado."""
    # Suporte aos nomes novos (arquivo_*) e antigos (*pecas), sem quebrar contratos.
    uploads = [
        arquivo_geral or geral_pecas,
        arquivo_genericas or pecas_genericas,
        arquivo_alveolares or pecas_alveolares,
    ]

    if not TEMPLATE_XLSX_PATH.exists():
        return _render_template(
            request,
            "index.html",
            {
                "erro": (
                    "Template Excel nao encontrado em "
                    f"'{TEMPLATE_XLSX_PATH}'."
                ),
                "sucesso": None,
            },
            status_code=400,
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        resultado = processar_uploads_web(
            uploads=uploads,
            caminho_template_excel=TEMPLATE_XLSX_PATH,
            pasta_temp="data/temp",
        )
        if not resultado.sucesso:
            return _render_template(
                request,
                "result.html",
                {
                    "sucesso": False,
                    "erro": "\n".join(resultado.erros),
                    "nome_arquivo": None,
                    "total_arquivos": 0,
                    "total_registros": 0,
                    "linhas_inseridas": 0,
                    "celulas_escritas": 0,
                    "total_erros_escrita": 0,
                },
                status_code=400,
            )

        return _render_template(
            request,
            "result.html",
            {
                "sucesso": True,
                "erro": None,
                "nome_arquivo": resultado.nome_arquivo_gerado,
                "total_arquivos": resultado.resumo["total_arquivos"],
                "total_registros": resultado.resumo["total_registros"],
                "linhas_inseridas": resultado.resumo["linhas_inseridas"],
                "celulas_escritas": resultado.resumo["celulas_escritas"],
                "total_erros_escrita": resultado.resumo["total_erros_escrita"],
            },
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Erro inesperado no processamento web: %s", exc)
        return _render_template(
            request,
            "result.html",
            {
                "sucesso": False,
                "erro": "Erro inesperado durante o processamento. Verifique os arquivos e tente novamente.",
                "nome_arquivo": None,
                "total_arquivos": 0,
                "total_registros": 0,
                "linhas_inseridas": 0,
                "celulas_escritas": 0,
                "total_erros_escrita": 1,
            },
            status_code=500,
        )
    finally:
        for upload in uploads:
            if not upload:
                continue
            try:
                await upload.close()
            except Exception:
                pass


@app.get("/download/{nome_arquivo}")
async def download_arquivo(nome_arquivo: str) -> FileResponse:
    """Faz download seguro do arquivo gerado em data/output."""
    nome_limpo = Path(nome_arquivo).name
    caminho = (OUTPUT_DIR / nome_limpo).resolve()
    output_resolvido = OUTPUT_DIR.resolve()

    if output_resolvido not in caminho.parents and caminho != output_resolvido:
        raise HTTPException(status_code=400, detail="Arquivo de download invalido.")
    if not caminho.exists() or caminho.suffix.lower() != ".xlsx":
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado para download.")

    return FileResponse(
        path=caminho,
        filename=caminho.name,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
