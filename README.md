# orcamento-ai

Estrutura inicial de um projeto Python para automação de orçamentos técnicos de obras.

## Objetivo

Ler um arquivo `.txt` com dados de orçamento técnico e preencher uma planilha `.xlsx` existente, alterando apenas os campos necessários e preservando o restante da planilha.

## Requisitos

- Python 3.11+
- Pip atualizado

## Estrutura do projeto

```text
orcamento-ai/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── agents/
│   ├── services/
│   ├── models/
│   ├── utils/
│   └── prompts/
├── data/
│   ├── input/
│   ├── templates/
│   └── output/
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Instalação

1. Criar e ativar ambiente virtual:

```bash
python -m venv .venv
```

Windows (PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

2. Instalar dependências:

```bash
pip install -r requirements.txt
```

3. Criar arquivo de ambiente:

```bash
cp .env.example .env
```

No Windows PowerShell, se `cp` não funcionar:

```bash
Copy-Item .env.example .env
```

## Execução inicial

```bash
python -m app.main
```

## Testes

```bash
pytest
```

## Próximos passos sugeridos

- Implementar parser do arquivo `.txt` em `app/services/`.
- Definir modelos de dados do orçamento em `app/models/`.
- Implementar integração com Excel (`openpyxl`) para atualização seletiva da planilha.

