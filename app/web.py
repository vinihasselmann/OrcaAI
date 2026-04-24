"""Interface web MVP com FastAPI + Jinja2 para importacao tecnica."""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.file_service import limpar_arquivos_temporarios, salvar_upload_temporario
from app.services.progress_service import ProgressService
from app.services.import_service import processar_caminhos_txt_web, processar_uploads_web

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

OUTPUT_DIR = Path(settings.output_dir)
TEMPLATE_XLSX_PATH = Path(settings.template_dir) / "orcamento_base.xlsx"

app = FastAPI(title="orcamento-ai", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
progress_service = ProgressService()


def _request_prefere_json(request: Request) -> bool:
    """Indica se a requisicao espera payload JSON para UX assincrona."""
    if request.headers.get("x-requested-with", "").strip().lower() == "fetch":
        return True
    accept = request.headers.get("accept", "").lower()
    return "application/json" in accept


def _json_resultado_processamento(
    *,
    sucesso: bool,
    erro: str | None,
    nome_arquivo: str | None,
    total_arquivos: int,
    total_registros: int,
    linhas_inseridas: int,
    celulas_escritas: int,
    total_erros_escrita: int,
    status_code: int = 200,
) -> JSONResponse:
    """Padroniza resposta JSON para a tela unificada."""
    return JSONResponse(
        status_code=status_code,
        content={
            "sucesso": sucesso,
            "erro": erro,
            "nome_arquivo": nome_arquivo,
            "download_url": f"/download/{nome_arquivo}" if sucesso and nome_arquivo else None,
            "resumo": {
                "total_arquivos": total_arquivos,
                "total_registros": total_registros,
                "linhas_inseridas": linhas_inseridas,
                "celulas_escritas": celulas_escritas,
                "total_erros_escrita": total_erros_escrita,
            },
        },
    )


def _executar_job_processamento(
    *,
    job_id: str,
    caminhos_txt: list[Path],
    caminho_template_excel: Path,
) -> None:
    """Executa processamento em thread e atualiza progresso compartilhado."""

    def on_progress(evento: dict[str, object]) -> None:
        progress_service.update(
            job_id,
            status="running",
            phase=str(evento.get("phase") or "processamento"),
            progress=int(evento.get("progress") or 0),
            message=str(evento.get("message") or "Processando..."),
            log_tone=str(evento.get("tone") or "info"),
        )

    try:
        progress_service.update(
            job_id,
            status="running",
            phase="leitura",
            progress=2,
            message="Job iniciado. Preparando processamento...",
            log_tone="info",
        )
        resultado = processar_caminhos_txt_web(
            caminhos_txt,
            caminho_template_excel,
            progress_callback=on_progress,
        )
        if not resultado.sucesso:
            erro = "\n".join(resultado.erros)
            progress_service.update(
                job_id,
                status="error",
                phase="resultado",
                progress=100,
                message=erro,
                log_tone="warn",
                error=erro,
            )
            return

        payload = {
            "sucesso": True,
            "erro": None,
            "nome_arquivo": resultado.nome_arquivo_gerado,
            "download_url": f"/download/{resultado.nome_arquivo_gerado}",
            "resumo": {
                "total_arquivos": resultado.resumo["total_arquivos"],
                "total_registros": resultado.resumo["total_registros"],
                "linhas_inseridas": resultado.resumo["linhas_inseridas"],
                "celulas_escritas": resultado.resumo["celulas_escritas"],
                "total_erros_escrita": resultado.resumo["total_erros_escrita"],
            },
        }
        progress_service.update(
            job_id,
            status="completed",
            phase="resultado",
            progress=100,
            message="Importacao concluida com sucesso.",
            log_tone="ok",
            result=payload,
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Erro inesperado no job de processamento: %s", exc)
        erro = "Erro inesperado durante o processamento. Verifique os arquivos e tente novamente."
        progress_service.update(
            job_id,
            status="error",
            phase="resultado",
            progress=100,
            message=erro,
            log_tone="warn",
            error=erro,
        )
    finally:
        limpar_arquivos_temporarios(caminhos_txt)


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


@app.post("/processar", response_class=HTMLResponse, response_model=None)
async def processar_importacao(
    request: Request,
    arquivo_geral: UploadFile | None = File(default=None),
    arquivo_auxiliares: UploadFile | None = File(default=None),
    arquivo_genericas: UploadFile | None = File(default=None),
    arquivo_alveolares: UploadFile | None = File(default=None),
    geral_pecas: UploadFile | None = File(default=None),
    pecas_auxiliares: UploadFile | None = File(default=None),
    pecas_genericas: UploadFile | None = File(default=None),
    pecas_alveolares: UploadFile | None = File(default=None),
) -> HTMLResponse:
    """Recebe uploads .txt, processa e renderiza resultado."""
    # Suporte aos nomes novos (arquivo_*) e antigos (*pecas), sem quebrar contratos.
    uploads = [
        arquivo_geral or geral_pecas,
        arquivo_auxiliares or pecas_auxiliares,
        arquivo_genericas or pecas_genericas,
        arquivo_alveolares or pecas_alveolares,
    ]

    if not TEMPLATE_XLSX_PATH.exists():
        erro = (
            "Template Excel nao encontrado em "
            f"'{TEMPLATE_XLSX_PATH}'."
        )
        if _request_prefere_json(request):
            return _json_resultado_processamento(
                sucesso=False,
                erro=erro,
                nome_arquivo=None,
                total_arquivos=0,
                total_registros=0,
                linhas_inseridas=0,
                celulas_escritas=0,
                total_erros_escrita=0,
                status_code=400,
            )
        return _render_template(
            request,
            "index.html",
            {
                "erro": erro,
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
            erro = "\n".join(resultado.erros)
            if _request_prefere_json(request):
                return _json_resultado_processamento(
                    sucesso=False,
                    erro=erro,
                    nome_arquivo=None,
                    total_arquivos=0,
                    total_registros=0,
                    linhas_inseridas=0,
                    celulas_escritas=0,
                    total_erros_escrita=0,
                    status_code=400,
                )
            return _render_template(
                request,
                "result.html",
                {
                    "sucesso": False,
                    "erro": erro,
                    "nome_arquivo": None,
                    "total_arquivos": 0,
                    "total_registros": 0,
                    "linhas_inseridas": 0,
                    "celulas_escritas": 0,
                    "total_erros_escrita": 0,
                },
                status_code=400,
            )

        if _request_prefere_json(request):
            return _json_resultado_processamento(
                sucesso=True,
                erro=None,
                nome_arquivo=resultado.nome_arquivo_gerado,
                total_arquivos=resultado.resumo["total_arquivos"],
                total_registros=resultado.resumo["total_registros"],
                linhas_inseridas=resultado.resumo["linhas_inseridas"],
                celulas_escritas=resultado.resumo["celulas_escritas"],
                total_erros_escrita=resultado.resumo["total_erros_escrita"],
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
        erro = "Erro inesperado durante o processamento. Verifique os arquivos e tente novamente."
        if _request_prefere_json(request):
            return _json_resultado_processamento(
                sucesso=False,
                erro=erro,
                nome_arquivo=None,
                total_arquivos=0,
                total_registros=0,
                linhas_inseridas=0,
                celulas_escritas=0,
                total_erros_escrita=1,
                status_code=500,
            )
        return _render_template(
            request,
            "result.html",
            {
                "sucesso": False,
                "erro": erro,
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


@app.post("/processar-async", response_model=None)
async def processar_importacao_async(
    request: Request,
    arquivo_geral: UploadFile | None = File(default=None),
    arquivo_auxiliares: UploadFile | None = File(default=None),
    arquivo_genericas: UploadFile | None = File(default=None),
    arquivo_alveolares: UploadFile | None = File(default=None),
    geral_pecas: UploadFile | None = File(default=None),
    pecas_auxiliares: UploadFile | None = File(default=None),
    pecas_genericas: UploadFile | None = File(default=None),
    pecas_alveolares: UploadFile | None = File(default=None),
) -> JSONResponse:
    """Cria job assíncrono para processamento com progresso real por polling."""
    uploads = [
        arquivo_geral or geral_pecas,
        arquivo_auxiliares or pecas_auxiliares,
        arquivo_genericas or pecas_genericas,
        arquivo_alveolares or pecas_alveolares,
    ]

    if not TEMPLATE_XLSX_PATH.exists():
        return JSONResponse(
            status_code=400,
            content={"erro": f"Template Excel nao encontrado em '{TEMPLATE_XLSX_PATH}'."},
        )

    caminhos_temporarios: list[Path] = []
    try:
        for upload in uploads:
            if upload and upload.filename:
                caminhos_temporarios.append(
                    salvar_upload_temporario(upload=upload, pasta_temp="data/temp")
                )
    except Exception as exc:
        limpar_arquivos_temporarios(caminhos_temporarios)
        return JSONResponse(
            status_code=400,
            content={"erro": f"Nao foi possivel preparar os arquivos enviados. Detalhe tecnico: {exc}"},
        )
    finally:
        for upload in uploads:
            if not upload:
                continue
            try:
                await upload.close()
            except Exception:
                pass

    job = progress_service.create_job()
    progress_service.update(
        job.job_id,
        status="queued",
        phase="fila",
        progress=0,
        message="Job criado. Aguardando processamento.",
        log_tone="info",
    )
    Thread(
        target=_executar_job_processamento,
        kwargs={
            "job_id": job.job_id,
            "caminhos_txt": caminhos_temporarios,
            "caminho_template_excel": TEMPLATE_XLSX_PATH,
        },
        daemon=True,
    ).start()
    return JSONResponse(status_code=202, content={"job_id": job.job_id})


@app.get("/processar-status/{job_id}", response_model=None)
async def consultar_status_processamento(job_id: str) -> JSONResponse:
    """Retorna status atual do job para polling do frontend."""
    payload = progress_service.as_payload(job_id)
    if not payload:
        return JSONResponse(status_code=404, content={"erro": "Job nao encontrado."})
    return JSONResponse(status_code=200, content=payload)


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
