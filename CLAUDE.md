# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal finance tracking system with a React/Vite frontend and FastAPI backend. Supports Gmail-based transaction parsing (Vietnamese banks), categorization, split bills, budgets, goals, debts, and subscriptions.

## Development Commands

### Recommended: Makefile (runs everything via Docker Compose)

```bash
make dev              # Start all services (postgres, redis, backend, frontend)
make stop             # Stop all services
make logs             # Tail logs for all services
make test             # Run all tests (frontend + backend)
make test-backend     # Backend tests only
make test-frontend    # Frontend tests only
make lint             # Lint both frontend and backend
make format           # Format both
make migrate          # Run Alembic migrations
make backup / make restore  # Database backup/restore
```

### Frontend (standalone)

```bash
cd frontend
npm run dev           # Vite dev server on port 5173
npm run build         # TypeScript check + Vite build
npm run lint          # ESLint
npm run format        # Prettier
npm test              # Vitest
npm run test:ui       # Vitest with browser UI
```

### Backend (standalone)

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload   # Dev server on port 8000
poetry run pytest                          # Tests with coverage
poetry run ruff check --fix               # Lint + autofix
poetry run mypy app                        # Type check (strict)
poetry run alembic upgrade head            # Apply migrations
poetry run alembic revision --autogenerate -m "description"  # New migration
```

## Architecture

### Frontend (`frontend/src/`)

- **Framework**: React 18 + TypeScript + Vite; React Router DOM v6 for routing
- **State**: Zustand stores (`store/`) for UI/app state; TanStack Query v5 for server state (5min stale, 10min cache)
- **HTTP**: Axios client in `api/client.ts` with interceptors; `api/transactions.ts` and similar files for domain endpoints
- **Styling**: Tailwind CSS 4 with custom palette (primary/success/danger/warning)
- **Charts**: Recharts
- **Path alias**: `@/` → `src/`; API proxy: `/api` → `localhost:8000`
- **Routing** (all wrapped in `<Layout>`): `/`, `/transactions`, `/split-bills`, `/budget`, `/goals`, `/debts`, `/subscriptions`, `/reports`, `/settings`

### Backend (`backend/app/`)

- **Framework**: FastAPI with async SQLAlchemy (PostgreSQL) + Alembic migrations
- **Caching**: Redis 7
- **Task scheduling**: Celery + APScheduler for email sync
- **Email parsing**: Gmail API → BeautifulSoup4 parsing → `parsers/` plugin system
- **Validation**: Pydantic v2 throughout; settings in `config.py`
- **Key layers**: `api/` (routes) → `services/` (business logic) → `models/` (ORM) + `schemas/` (Pydantic)

### Parser Plugin System

Bank email parsers live in `backend/app/parsers/banks/`. Each extends `BaseBankParser` from `parsers/base.py`. The registry in `parsers/registry.py` auto-discovers parsers. Currently supports Cake/VPBank Vietnamese bank emails.

### Database Models (15 total, 4 files)

- `models/transaction.py`: `Account`, `Category`, `Transaction`, `CategorizationRule`
- `models/social.py`: `Contact`, `SplitGroup`, `SplitBill`, `SplitParticipant`
- `models/planning.py`: `Budget`, `Goal`, `Debt`, `Subscription`
- `models/system.py`: `User`, `EmailSyncLog`, `ParserRegistry`, `UserSetting`, error tracking

All records use UUID PKs and are isolated by `user_id` (multi-tenant).

### Infrastructure

- **Dev**: Docker Compose — PostgreSQL 16 (5432), Redis 7 (6379), backend (8000), frontend (5173)
- **Prod**: `docker-compose.prod.yml` adds Nginx reverse proxy
- Environment templates: `.env.example` (root), `frontend/.env.example`, `backend/.env.example`

## Key Conventions

- **Python**: 3.12, strict mypy, ruff for lint/format, async/await everywhere for DB operations
- **TypeScript**: strict mode, path alias `@/`
- **All list endpoints** are paginated
- **Dependency injection** via FastAPI `Depends()` for DB sessions, current user, etc.
