# Infrastructure & Deployment Guide

Personal Finance Tracker - Docker & Kubernetes Infrastructure Documentation

## Overview

This document describes the complete infrastructure setup for the Personal Finance Tracker, including Docker configurations, deployment options, and operational procedures.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Directory Structure](#directory-structure)
3. [Development Environment](#development-environment)
4. [Production Deployment](#production-deployment)
5. [Services](#services)
6. [Database & Backups](#database--backups)
7. [Nginx Configuration](#nginx-configuration)
8. [Makefile Commands](#makefile-commands)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### One-Command Setup

```bash
# Run the development setup script
bash scripts/dev-setup.sh

# Or use Make
make setup
```

This will:
- Verify all prerequisites (Docker, Python, Node.js)
- Create `.env` file from `.env.example`
- Initialize secrets directory
- Start PostgreSQL and Redis
- Install backend dependencies
- Install frontend dependencies (if exists)
- Run database migrations
- Start all services

### Verify Services

```bash
# Check service health
make health-check

# View logs
docker-compose logs -f
```

Visit:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

---

## Directory Structure

```
personal-finance-tracking/
├── backend/                      # FastAPI Python application
│   ├── Dockerfile               # Backend Docker image
│   ├── app/                     # Application code
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test suite
│   ├── pyproject.toml          # Poetry dependencies
│   └── .env.example            # Backend env template
│
├── frontend/                     # React TypeScript application
│   ├── Dockerfile              # Frontend Docker image (to be created)
│   ├── src/                    # Source code
│   ├── package.json           # Node dependencies
│   └── .env.example           # Frontend env template
│
├── nginx/                        # Reverse proxy
│   ├── Dockerfile              # Nginx Docker image
│   ├── nginx.conf              # Nginx configuration
│   └── ssl/                    # SSL certificates (production)
│
├── scripts/                      # Utility scripts
│   ├── dev-setup.sh           # One-command dev setup
│   ├── backup.sh              # Database backup script
│   ├── restore.sh             # Database restore script
│   └── backups/               # Backup storage directory
│
├── secrets/                      # Sensitive files (not in git)
│   ├── credentials.json       # Gmail API credentials
│   └── token.json             # Gmail API token
│
├── docker-compose.yml           # Development environment
├── docker-compose.prod.yml      # Production overrides
├── .env.example                # Root environment template
├── .gitignore                  # Git ignore rules
├── Makefile                    # Development commands
└── INFRASTRUCTURE.md           # This file
```

---

## Development Environment

### docker-compose.yml

The main development configuration includes:

**Services:**
- **postgres** (postgres:16-alpine)
  - Port: 5432
  - Volume: `postgres_data`
  - Healthcheck: Every 10 seconds
  - Default user: `finance_user`

- **redis** (redis:7-alpine)
  - Port: 6379
  - Volume: `redis_data`
  - Authentication: Enabled (password in .env)
  - Healthcheck: Every 10 seconds

- **backend** (FastAPI)
  - Port: 8000
  - Build: From `./backend/Dockerfile`
  - Depends on: postgres, redis
  - Volume mounts:
    - `./backend` (source code)
    - `./secrets` (read-only)
    - `backend_logs`

- **frontend** (React)
  - Port: 3000
  - Build: From `./frontend/Dockerfile`
  - Depends on: backend
  - Volume mounts:
    - `./frontend` (source code)
    - `/app/node_modules` (named volume)

**Volumes:**
- `postgres_data`: PostgreSQL data persistence
- `redis_data`: Redis data persistence
- `backend_logs`: Backend application logs

**Network:**
- `finance-network`: Bridge network connecting all services

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Application
APP_ENV=dev
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production

# Database
POSTGRES_USER=finance_user
POSTGRES_PASSWORD=finance_password
POSTGRES_DB=finance_db

# Redis
REDIS_PASSWORD=redis_password

# Frontend
REACT_APP_API_BASE_URL=http://localhost:8000

# Gmail Integration
ENABLE_EMAIL_SYNC=true
EMAIL_SYNC_INTERVAL_MINUTES=15
```

### Common Development Tasks

```bash
# Start all services
make dev

# View logs in real-time
make logs

# Run backend tests
make test-backend

# Run frontend tests
make test-frontend

# Run database migrations
make migrate

# Format code (black, ruff, prettier)
make format

# Stop services
make stop
```

---

## Production Deployment

### docker-compose.prod.yml

Production configuration with:

**Changes from Development:**
- Nginx reverse proxy (ports 80, 443)
- Resource limits on all services
- No exposed database/redis ports
- SSL/TLS enabled (commented, configure with real certs)
- Database backup service
- Service replicas for backend

**Resource Limits:**
- **backend**: 2 CPU cores, 1.5GB RAM, 2 replicas
- **postgres**: 2 CPU cores, 2GB RAM
- **redis**: 1 CPU core, 512MB RAM
- **nginx**: 1 CPU core, 512MB RAM
- **backup**: 1 CPU core, 512MB RAM

### Nginx Configuration

The `nginx/nginx.conf` provides:

**Features:**
- Reverse proxy routing
  - `/` → frontend (port 3000)
  - `/api/` → backend (port 8000)
  - `/health` → backend health endpoint
- Gzip compression
- Security headers
  - HSTS (1 year)
  - X-Frame-Options: SAMEORIGIN
  - X-Content-Type-Options: nosniff
  - CSP headers
- Rate limiting
  - API: 10 req/s
  - General: 30 req/s
- Caching for static assets (60 minutes)
- SSL/TLS configuration (template)
- Logging and access control

### SSL/TLS Setup

1. Generate or obtain certificates:

```bash
# Self-signed (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem

# Let's Encrypt (production)
certbot certonly --standalone -d yourdomain.com
```

2. Uncomment SSL section in `nginx/nginx.conf`

3. Deploy with:

```bash
make prod-up
```

### Production Checklist

- [ ] Update `.env` with production secrets
- [ ] Configure database credentials
- [ ] Generate or obtain SSL certificates
- [ ] Update `nginx.conf` with your domain
- [ ] Configure backup encryption key
- [ ] Set up monitoring and alerting
- [ ] Configure backup storage location
- [ ] Test database restore procedure
- [ ] Set up CI/CD pipeline
- [ ] Configure log aggregation

---

## Services

### PostgreSQL Database

**Purpose:** Primary data store for transactions, users, categories, and rules

**Configuration:**
```yaml
Image: postgres:16-alpine
Port: 5432
User: finance_user (from .env)
Database: finance_db (from .env)
Volume: postgres_data (persistent)
```

**Healthcheck:**
```bash
pg_isready -U finance_user
```

**Useful Commands:**

```bash
# Connect to database
docker-compose exec postgres psql -U finance_user -d finance_db

# Backup
docker-compose exec postgres pg_dump -U finance_user finance_db > backup.sql

# Restore
docker-compose exec -T postgres psql -U finance_user finance_db < backup.sql
```

### Redis Cache

**Purpose:** Session storage, caching, and async task queue

**Configuration:**
```yaml
Image: redis:7-alpine
Port: 6379
Password: (from .env REDIS_PASSWORD)
Volume: redis_data (persistent)
```

**Healthcheck:**
```bash
redis-cli -a password ping
```

**Useful Commands:**

```bash
# Connect to Redis
docker-compose exec redis redis-cli -a password

# Check stats
docker-compose exec redis redis-cli -a password INFO

# Flush cache
docker-compose exec redis redis-cli -a password FLUSHALL
```

### Backend (FastAPI)

**Purpose:** REST API for finance tracking operations

**Technology Stack:**
- FastAPI 0.104.1
- SQLAlchemy with AsyncPG
- Celery + Redis for async tasks
- APScheduler for scheduled jobs
- Google API for email parsing

**Port:** 8000

**Health Endpoint:** `GET /health/ping`

**API Documentation:** `GET /docs` (Swagger UI)

**Environment:** See `.env.example` in backend/

**Development:**

```bash
# Run locally
cd backend
poetry run uvicorn app.main:app --reload

# Run tests
poetry run pytest -v

# Format code
poetry run ruff check --fix app
```

### Frontend (React)

**Purpose:** User interface for finance tracking

**Technology Stack:**
- React 18
- TypeScript
- Vite or Create React App
- TailwindCSS (assumed)

**Port:** 3000

**Environment:** See `.env.example` in frontend/

**Development:**

```bash
# Run locally
cd frontend
npm start

# Run tests
npm test

# Build
npm run build
```

### Nginx Reverse Proxy

**Purpose:** HTTP/HTTPS termination, routing, and security

**Port:** 80 (HTTP), 443 (HTTPS)

**Routing:**
- `/` → Frontend (3000)
- `/api/*` → Backend (8000)
- `/health` → Backend health check

**Security Features:**
- HTTPS/TLS 1.2+
- Security headers
- Rate limiting
- DDoS protection
- Static file caching

---

## Database & Backups

### Backup Script (`scripts/backup.sh`)

**Purpose:** Create compressed, encrypted PostgreSQL backups

**Features:**
- Automatic compression (gzip level 9)
- Optional GPG encryption (AES256)
- Backup rotation (30-day retention)
- Metadata files with checksums
- Comprehensive logging
- Monitoring-friendly exit codes

**Usage:**

```bash
# Create backup
bash scripts/backup.sh

# Using Make
make backup

# With encryption
BACKUP_ENCRYPTION_KEY=mykey bash scripts/backup.sh

# List backups
make backup-list
```

**Output:**
- Backup file: `backups/backup_YYYYMMDD_HHMMSS.sql.gz[.gpg]`
- Metadata file: `backups/backup_YYYYMMDD_HHMMSS.meta`
- Log file: `backups/backup.log`

**Exit Codes:**
- 0: Success
- 1: General error
- 2: Rotation failed (but backup succeeded)
- 3: Encryption failed
- 4: Directory error

### Restore Script (`scripts/restore.sh`)

**Purpose:** Restore PostgreSQL from backups

**Features:**
- Automatic backup detection
- Backup validation
- GPG decryption support
- Pre-restore backup creation
- Dry-run mode
- Interactive confirmation

**Usage:**

```bash
# List available backups
bash scripts/restore.sh --list

# Restore from latest
bash scripts/restore.sh --latest

# Restore specific backup
bash scripts/restore.sh --file backup_20240315_120000.sql.gz

# Validate backup only
bash scripts/restore.sh --file backup_20240315_120000.sql.gz --validate-only

# Dry run
bash scripts/restore.sh --latest --dry-run

# Using Make
make restore
make restore-file file=backup_20240315_120000.sql.gz
```

**Exit Codes:**
- 0: Success
- 1: General error
- 2: Validation error
- 3: Decryption error
- 4: Backup not found
- 5: Restore error

### Backup Strategy

**Recommended Schedule:**
- Daily: Automated backups at off-peak hours
- Weekly: Archive for longer-term retention
- Manual: Before major updates or migrations

**Encryption:**
```bash
# Set encryption key in .env
BACKUP_ENCRYPTION_KEY=your-strong-random-key

# Backups will be encrypted automatically
```

**Storage:**
- Local: `./scripts/backups/`
- Remote: Upload to S3, GCS, or backup service
- Retention: 30 days daily, 12 weeks archived

**Verification:**
```bash
# Test restore procedure regularly
make restore-file file=backup_YYYYMMDD_HHMMSS.sql.gz

# Verify backup integrity
sha256sum backups/backup_*.sql.gz
```

---

## Nginx Configuration

### Location Blocks

**Root Path `/`**
- Routes to frontend (port 3000)
- Rate limit: 30 req/s
- Handles WebSocket upgrade
- Caches static assets (60 min)

**API Path `/api/`**
- Routes to backend (port 8000)
- Rate limit: 10 req/s
- Includes burst allowance
- Forwards headers (X-Real-IP, X-Forwarded-*)

**Health Path `/api/health`**
- Direct backend health endpoint
- No logging
- No rate limiting
- Used by monitoring

### Security Headers

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

### Performance

- Gzip compression (level 6) for text/JSON
- Proxy buffering (8KB buffers)
- Connection pooling
- Cache for static assets
- Worker processes: auto
- Worker connections: 1024

### SSL/TLS

Configure in production:

```nginx
listen 443 ssl http2;
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
```

---

## Makefile Commands

### Setup & Development

```bash
make setup              # One-command dev setup
make dev               # Start services (background)
make dev-foreground    # Start services (foreground)
make stop              # Stop services
make restart           # Restart services
```

### Viewing Logs

```bash
make logs              # All services
make logs-backend      # Backend only
make logs-frontend     # Frontend only
make logs-postgres     # PostgreSQL only
make logs-redis        # Redis only
```

### Building

```bash
make build             # Build all services
make build-backend     # Build backend only
make build-frontend    # Build frontend only
make rebuild           # Rebuild with no cache
```

### Testing

```bash
make test              # All tests
make test-backend      # Backend tests
make test-frontend     # Frontend tests
make test-quick        # Backend tests only, no coverage
```

### Code Quality

```bash
make lint              # All linters
make lint-backend      # Backend linter
make lint-frontend     # Frontend linter
make format            # Format all code
make format-backend    # Format backend
make format-frontend   # Format frontend
```

### Database

```bash
make migrate           # Run migrations
make migrate-create message="description"  # Create migration
make migrate-rollback  # Rollback last migration
make backup            # Create backup
make backup-list       # List backups
make restore           # Restore from latest
make restore-file file=backup_file.sql.gz
```

### Cleanup

```bash
make clean             # Remove containers and volumes
make clean-docker      # Remove Finance Tracker images
make prune-docker      # Prune unused Docker resources
```

### Production

```bash
make prod-build        # Build production images
make prod-up           # Start production
make prod-down         # Stop production
make prod-logs         # View production logs
```

### Utilities

```bash
make health-check      # Check service health
make .env              # Create .env from example
make secrets           # Create secrets directory
make version           # Show version info
make validate          # Validate Docker Compose files
make ps                # Show running containers
```

---

## Troubleshooting

### Services Won't Start

**PostgreSQL connection refused:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
make logs-postgres

# Restart PostgreSQL
docker-compose restart postgres

# Wait for healthcheck
docker-compose exec postgres pg_isready -U finance_user
```

**Backend can't connect to database:**
```bash
# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Test connection manually
docker-compose exec backend python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql+asyncpg://...')
print('Connected!')
"
```

### Port Conflicts

**Port 3000 or 8000 already in use:**
```bash
# Find what's using the port
lsof -i :3000
lsof -i :8000

# Change port in docker-compose.yml
# Or kill the process
kill -9 <PID>
```

### Database Issues

**Migrations failed:**
```bash
# Check migration status
docker-compose exec backend alembic current

# Reset database (development only!)
docker-compose down -v
make dev
```

**Can't connect to database:**
```bash
# Check credentials in .env
grep POSTGRES_ .env

# Test connection
docker-compose exec postgres psql -U finance_user -d finance_db

# Check network connectivity
docker-compose exec backend ping postgres
```

### Backup/Restore Issues

**Backup file corrupted:**
```bash
# Validate backup
bash scripts/restore.sh --file backup.sql.gz --validate-only

# Check file size
ls -lh backups/backup_*.sql.gz

# Check metadata
cat backups/backup_*.meta
```

**Can't decrypt backup:**
```bash
# Verify encryption key
echo $BACKUP_ENCRYPTION_KEY

# Try restore with correct key
BACKUP_ENCRYPTION_KEY=correct-key bash scripts/restore.sh --latest
```

### Performance Issues

**Slow database queries:**
```bash
# Enable slow query log
docker-compose exec postgres \
  psql -U finance_user -d finance_db \
  -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"

# View logs
docker-compose logs postgres
```

**High memory usage:**
```bash
# Check resource usage
docker stats

# View limits
docker-compose config | grep -A 10 "resources:"

# Reduce cache size in redis.conf if needed
```

### Log Issues

**Can't see logs:**
```bash
# All logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Since specific time
docker-compose logs --since 2024-03-15T12:00:00
```

### Docker Issues

**Containers not updating after code changes:**
```bash
# Rebuild without cache
make rebuild

# Or manually
docker-compose build --no-cache

# Then restart
docker-compose restart
```

**Out of disk space:**
```bash
# Clean up Docker
make prune-docker

# Remove unused volumes
docker volume prune

# Check disk usage
docker system df
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Quick health check
make health-check

# Detailed backend check
curl http://localhost:8000/health/ping

# Database check
docker-compose exec postgres pg_isready -U finance_user

# Redis check
docker-compose exec redis redis-cli ping
```

### Regular Maintenance

**Daily:**
- Monitor application logs
- Check backup completion
- Verify API responsiveness

**Weekly:**
- Review error logs
- Test backup restoration
- Update dependencies (if configured)

**Monthly:**
- Performance analysis
- Security updates
- Database optimization

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

## Support & Contributions

For issues or questions:
1. Check this documentation
2. Review service logs: `make logs`
3. Check healthchecks: `make health-check`
4. Review backend README: `./backend/README.md`
5. Check implementation checklist: `./IMPLEMENTATION_CHECKLIST.md`

---

**Last Updated:** March 2024
**Version:** 1.0
