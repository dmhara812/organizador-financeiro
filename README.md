# Organizador Financeiro e de Investimentos

Produto web fullstack para controle de patrimônio, registro de aportes e acompanhamento da evolução dos investimentos ao longo do tempo.

Este projeto está sendo desenvolvido de forma incremental, com documentação por etapa em `docs/`, servindo também como portfólio técnico de backend, frontend, arquitetura, autenticação, Docker e deploy.

---

## 1. Problema que o projeto resolve

Muitos investidores pessoa física acompanham patrimônio, aportes e evolução dos investimentos usando planilhas ou aplicativos pouco flexíveis.

Este sistema busca centralizar:

- cadastro de ativos;
- registro de aportes e movimentações;
- categorização dos investimentos;
- visão consolidada do patrimônio;
- gráficos de distribuição e evolução temporal;
- filtros por período, categoria, corretora e tipo de ativo.

A proposta é demonstrar uma solução web real, organizada e com valor de negócio claro.

---

## 2. Stack escolhida

### Backend

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT para autenticação
- Pytest para testes
- Ruff para lint e formatação

### Frontend

- React com Vite
- Recharts para gráficos
- Serviços de API separados
- Contexto/hooks para autenticação e estado global

### Infraestrutura

- Docker
- Docker Compose
- Deploy público do backend e frontend em etapas futuras

---

## 3. Decisões iniciais do projeto

### Modelagem de domínio

A modelagem escolhida foi a **orientada a movimentações como fonte da verdade**.

Isso significa que o patrimônio e as posições dos ativos serão calculados a partir das movimentações registradas, como aportes, compras, vendas, rendimentos, taxas e ajustes.

Essa abordagem é mais próxima de sistemas financeiros reais, porque mantém histórico auditável e permite recalcular posições com maior consistência.

### Frontend

O frontend escolhido foi **React com Vite**.

Essa escolha mantém o frontend desacoplado do backend FastAPI, reduz complexidade inicial e combina bem com uma API REST documentada via Swagger/OpenAPI.

---

## 4. Estrutura esperada do projeto

```text
organizador-financeiro/
  backend/
    app/
      api/
      core/
      models/
      schemas/
      repositories/
      services/
      tests/
    alembic/
    Dockerfile
    .env.example
  frontend/
    src/
      pages/
      components/
      services/
      hooks/
      context/
    public/
    Dockerfile
    .env.example
  docs/
    etapa-01-planejamento.md
    etapa-02-backend-base.md
    etapa-03-models-migrations.md
  docker-compose.yml
  README.md
  .gitignore
```

O diretório `frontend/` será criado em uma etapa futura.

---

## 5. Estado atual do projeto

Etapas concluídas até agora:

- Etapa 1: Planejamento, modelagem de domínio e escolha do frontend.
- Etapa 2: Estrutura base do backend com FastAPI, PostgreSQL e Docker.
- Etapa 3: Models SQLAlchemy, Alembic e migration inicial.

Próxima etapa:

- Etapa 4: Schemas Pydantic e tratamento global de erros.

---

## 6. Como rodar o backend localmente

Na raiz do projeto:

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Depois acesse:

```text
http://localhost:8000/docs
http://localhost:8000/api/v1/health
http://localhost:8000/api/v1/health/db
```

---

## 7. Como aplicar as migrations

Com os containers rodando:

```bash
docker compose exec backend alembic upgrade head
```

Para verificar a migration atual:

```bash
docker compose exec backend alembic current
```

Para listar as tabelas no PostgreSQL:

```bash
docker compose exec db psql -U finance_user -d finance_app -c "\dt"
```

---

## 8. Lint e formatação

O projeto usa Ruff para lint e formatação do backend.

Para verificar problemas:

```bash
docker compose exec backend ruff check app alembic
```

Para formatar os arquivos:

```bash
docker compose exec backend ruff format app alembic
```

Quando houver testes implementados, eles serão executados com Pytest.

---

## 9. Versionamento com Git e GitHub

O repositório deve ser criado na raiz do projeto, não dentro de `backend/`.

Arquivos como `docker-compose.yml`, `README.md`, `.gitignore`, `docs/`, `backend/` e futuramente `frontend/` pertencem ao root do repositório.

### Primeiro commit recomendado

```bash
git status
git add .
git commit -m "chore: setup initial backend structure and documentation"
```

Crie um repositório vazio no GitHub, sem README, sem `.gitignore` e sem license, porque esses arquivos já existirão localmente.

Depois conecte o repositório remoto via SSH:

```bash
git branch -M main
git remote add origin git@github.com:SEU_USUARIO/organizador-financeiro.git
git push -u origin main
```

Ou via HTTPS:

```bash
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/organizador-financeiro.git
git push -u origin main
```

### Commits por etapa

A partir da Etapa 4, a recomendação é fazer pelo menos um commit por etapa:

```bash
git status
git add .
git commit -m "feat: add pydantic schemas and global error handling"
git push
```

---

## 10. Arquivos que não devem ir para o GitHub

O arquivo `.env` nunca deve ser versionado.

Use `.env.example` para documentar quais variáveis são necessárias.

Exemplo de itens que devem ficar no `.gitignore`:

```gitignore
.env
.venv/
venv/
__pycache__/
.pytest_cache/
.ruff_cache/
*.pyc
node_modules/
dist/
build/
.coverage
htmlcov/
.DS_Store
```

---

## 11. Documentação por etapa

Cada etapa do projeto deve gerar um arquivo Markdown dentro de `docs/`.

Exemplos:

```text
docs/etapa-01-planejamento.md
docs/etapa-02-backend-base.md
docs/etapa-03-models-migrations.md
docs/etapa-04-schemas-erros.md
```

As próximas etapas devem incluir, quando aplicável:

- conteúdo completo dos arquivos criados ou alterados;
- comandos para rodar, validar e testar;
- comandos de lint/formatação;
- seção de versionamento com Git/GitHub;
- mensagem de commit sugerida;
- checklist do que foi concluído;
- próxima etapa.

---

## 12. Próximos passos

Antes da Etapa 4:

1. criar ou revisar o `.gitignore` na raiz;
2. garantir que `ruff` esteja em `backend/requirements.txt`;
3. rodar lint e formatação;
4. validar migrations;
5. criar o repositório no GitHub;
6. fazer o primeiro commit e push.

Depois disso, seguir para:

```text
Etapa 4 — Schemas Pydantic + tratamento de erros global
```
