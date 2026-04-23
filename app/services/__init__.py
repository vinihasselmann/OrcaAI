"""Modulo de servicos da aplicacao."""

from app.services.excel_reader import (
    abrir_workbook_existente,
    buscar_linhas_por_identificador,
    detectar_formula,
    ler_linha_inteira,
    ler_valor_celula,
    listar_abas,
    localizar_cabecalhos,
)
from app.services.excel_writer import (
    ResultadoEscrita,
    aplicar_mapeamentos_excel,
    copiar_planilha_base_para_output,
    criar_backup_planilha,
    escrever_dados_mapeados,
    localizar_proxima_linha_disponivel,
)
from app.services.field_mapper import (
    gerar_identificador_registro,
    gerar_proxima_linha_disponivel,
    mapear_documento_para_excel,
    mapear_registro_para_excel,
    obter_regras_mapeamento,
    transformar_registro_em_colunas_alvo,
)
from app.services.file_service import (
    FileServiceError,
    gerar_nome_unico_seguro,
    limpar_arquivos_temporarios,
    salvar_upload_temporario,
    validar_arquivo_txt,
)
from app.services.import_service import ImportServiceResult, processar_uploads_web
from app.services.txt_parser import (
    carregar_arquivo_txt,
    converter_linha_em_dict,
    detectar_tipo_arquivo,
    extrair_cabecalhos,
    normalizar_valor,
    parsear_documento,
    parsear_registros,
)
from app.services.validator import (
    validar_documento_importado,
    validar_lista_mapeamentos,
    validar_mapeamento,
    validar_registro,
)

__all__ = [
    "abrir_workbook_existente",
    "listar_abas",
    "ler_linha_inteira",
    "localizar_cabecalhos",
    "ler_valor_celula",
    "detectar_formula",
    "buscar_linhas_por_identificador",
    "criar_backup_planilha",
    "copiar_planilha_base_para_output",
    "localizar_proxima_linha_disponivel",
    "escrever_dados_mapeados",
    "aplicar_mapeamentos_excel",
    "ResultadoEscrita",
    "gerar_identificador_registro",
    "transformar_registro_em_colunas_alvo",
    "gerar_proxima_linha_disponivel",
    "FileServiceError",
    "validar_arquivo_txt",
    "gerar_nome_unico_seguro",
    "salvar_upload_temporario",
    "limpar_arquivos_temporarios",
    "ImportServiceResult",
    "processar_uploads_web",
    "obter_regras_mapeamento",
    "mapear_registro_para_excel",
    "mapear_documento_para_excel",
    "validar_documento_importado",
    "validar_registro",
    "validar_mapeamento",
    "validar_lista_mapeamentos",
    "carregar_arquivo_txt",
    "detectar_tipo_arquivo",
    "extrair_cabecalhos",
    "normalizar_valor",
    "converter_linha_em_dict",
    "parsear_registros",
    "parsear_documento",
]
