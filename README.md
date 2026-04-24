# OrcAI

Aplicacao web em Python para importar arquivos `.txt` de pecas pre-moldadas e preencher uma planilha Excel de orcamento automaticamente.

## O que o app faz

O sistema recebe arquivos `.txt` tecnicos exportados do revit, interpreta o tipo de cada arquivo, transforma os dados em registros estruturados e grava essas informacoes em uma planilha `.xlsx` base.

Hoje o fluxo cobre estes arquivos:

- `Geral Pecas`
- `Geral Pecas Auxiliares`
- `Geral Pecas Genericas`
- `Geral Pecas Alveolares`

Durante o processamento, o app:

1. recebe os arquivos `.txt` pela interface web;
2. detecta o tipo de cada arquivo;
3. faz o parse das linhas e ignora linhas de total/resumo;
4. aplica regras de negocio e mapeamento para colunas especificas da planilha;
5. gera uma copia da planilha base preenchida;
6. disponibiliza o arquivo final para download no navegador.

## Estrutura principal

```text
Cassol_OrçAI/
├── app/
│   ├── agents/
│   ├── models/
│   ├── services/
│   ├── static/
│   ├── templates/
│   ├── config.py
│   ├── main.py
│   └── web.py
├── data/
│   ├── output/
│   └── templates/
├── tests/
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.11 ou superior
- `pip` atualizado

## Como instalar

### 1. Criar o ambiente virtual

No diretório do projeto:

```bash
python -m venv .venv
```

### 2. Ativar o ambiente virtual

No Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

No Linux/macOS:

```bash
source .venv/bin/activate
```

### 3. Instalar as dependencias

```bash
pip install -r requirements.txt
```

As principais dependencias do projeto sao:

- `fastapi`
- `uvicorn`
- `openpyxl`
- `pydantic`
- `jinja2`
- `python-multipart`

## Como rodar no navegador com Uvicorn

Com o ambiente virtual ativado, execute:

```bash
uvicorn app.web:app --reload
```

O Uvicorn deve iniciar um servidor local. Depois disso:

1. abra o navegador;
2. acesse `http://127.0.0.1:8000`;
3. envie um ou mais arquivos `.txt`;
4. processe a importacao;
5. baixe a planilha gerada.

## Passo a passo de uso

### 1. Garantir que a planilha base exista

O app usa uma planilha modelo em:

```text
data/templates/orcamento_base.xlsx
```

Sem esse arquivo, a importacao nao sera concluida.

### 2. Iniciar a interface web

```bash
uvicorn app.web:app --reload
```

### 3. Abrir a interface

No navegador:

```text
http://127.0.0.1:8000
```

### 4. Selecionar os arquivos `.txt`

Voce pode enviar os arquivos tecnicos suportados pela tela:

- `Geral Pecas`
- `Geral Pecas Auxiliares`
- `Geral Pecas Genericas`
- `Geral Pecas Alveolares`

### 5. Processar

Clique em `Processar orcamento`.

O backend vai:

- salvar os uploads temporariamente;
- interpretar os dados;
- validar os registros;
- preencher a planilha;
- gerar um arquivo final em `data/output/`.

### 6. Baixar o resultado

Ao final, a tela exibe um link para download da planilha atualizada.

## Como rodar testes

Com o ambiente virtual ativado:

```bash
pytest
```

## Observacoes

- O app foi construido para trabalhar com uma planilha existente, sem recriar a estrutura do Excel do zero.
- Parte das regras de preenchimento depende do tipo do arquivo importado.
- Algumas colunas da planilha recebem valores padrao conforme as regras de negocio implementadas no backend.
