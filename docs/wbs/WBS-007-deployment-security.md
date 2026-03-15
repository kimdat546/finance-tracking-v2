# WBS-007: Deployment & Security

**Feature**: Production Deployment and Security Hardening
**Status**: NOT STARTED
**Priority**: P0 (Critical)
**Total Effort**: 80-100 hours (7 tasks)
**Dependencies**: All other WBS
**Created**: 2026-03-15

---

## Overview

Prepare system for production: SSL/TLS, authentication, backups, monitoring, security hardening.

---

## WBS-007-01: Setup SSL/TLS with Let's Encrypt (Certbot + Nginx)

**Effort**: 12 hours | **Dependencies**: Infrastructure setup

Configure Nginx reverse proxy with SSL/TLS certificates. Auto-renewal with certbot.

**Acceptance Criteria**:
- Nginx reverse proxy configuration
- Let's Encrypt SSL certificate
- HTTP → HTTPS redirect (all traffic)
- HSTS header (enforce HTTPS)
- TLS 1.2+ only
- Certificate auto-renewal (certbot)
- Certificate renewal alerts (email)
- HTTP/2 support
- Gzip compression enabled
- Security headers (X-Frame-Options, etc.)

**Files**:
- `/nginx/nginx.conf` - Enhanced
- `/scripts/setup-ssl.sh` - Certbot setup
- `/docker-compose.prod.yml` - Production config
- `/docs/SSL_SETUP.md` - Instructions

**Technical Notes**:
```nginx
# Nginx config
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json;

    # Proxy to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Serve frontend
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

**Certbot Setup Script**:
```bash
#!/bin/bash
# setup-ssl.sh

DOMAIN=${1:-yourdomain.com}
EMAIL=${2:-admin@yourdomain.com}

# Install certbot
apt-get install -y certbot python3-certbot-nginx

# Get certificate
certbot certonly \
    --standalone \
    -d $DOMAIN \
    -m $EMAIL \
    -n \
    --agree-tos

# Setup auto-renewal
certbot renew --dry-run
```

---

## WBS-007-02: Implement Authentication (JWT, Login, Token Refresh)

**Effort**: 16 hours | **Dependencies**: Infrastructure

JWT-based authentication. Login endpoint, token generation, refresh tokens, password reset.

**Acceptance Criteria**:
- User login endpoint (email/password)
- JWT token generation (with expiry)
- Token refresh endpoint
- Logout (token blacklist)
- Password hashing (bcrypt)
- Password reset flow (email link)
- Email verification (optional)
- Rate limiting on login
- Secure cookie storage (httpOnly, secure)
- Session management (max 5 devices)

**Files**:
- `/backend/app/auth/` - New auth module
  - `__init__.py`
  - `jwt_handler.py`
  - `password_utils.py`
  - `oauth_providers.py` - OAuth2 (Google, GitHub, optional)
- `/backend/app/models/auth.py` - User model enhancement
- `/backend/app/api/auth.py` - Auth endpoints
- `/backend/app/schemas/auth.py` - Auth schemas
- `/backend/tests/test_auth/` - Auth tests

**Technical Notes**:
```python
# JWT handler
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext

class JWTHandler:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.pwd_context = CryptContext(schemes=["bcrypt"])

    def create_access_token(self, user_id: str, expires_in: int = 3600):
        """Create access token (1 hour default)."""
        payload = {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str):
        """Create refresh token (30 days)."""
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> str | None:
        """Verify and decode token, return user_id."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload.get("sub")
        except JWTError:
            return None

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, password: str, hash: str) -> bool:
        return self.pwd_context.verify(password, hash)

# Endpoints
@router.post("/login")
async def login(
    email: str,
    password: str,
    session: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    # Find user
    user = await get_user_by_email(session, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    jwt_handler = JWTHandler(settings.secret_key)
    if not jwt_handler.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create tokens
    access_token = jwt_handler.create_access_token(user.id)
    refresh_token = jwt_handler.create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": UserSchema.from_orm(user),
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token."""
    jwt_handler = JWTHandler(settings.secret_key)
    user_id = jwt_handler.verify_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access = jwt_handler.create_access_token(user_id)
    return {"access_token": new_access}
```

---

## WBS-007-03: Setup Automated Backups (Daily Cron, Weekly Offsite)

**Effort**: 14 hours | **Dependencies**: Infrastructure

Automated database backups: daily local, weekly to S3/cloud storage.

**Acceptance Criteria**:
- Daily database backup (pg_dump)
- 7-day retention (local)
- Weekly backup to S3
- 30-day retention (S3)
- Backup encryption (GPG or AWS KMS)
- Backup integrity checks (md5sum)
- Email notification (backup success/failure)
- Point-in-time recovery capability
- Disaster recovery runbook
- Test restore process monthly

**Files**:
- `/scripts/backup-database.sh` - Daily backup
- `/scripts/backup-to-s3.sh` - Weekly S3 backup
- `/scripts/restore-database.sh` - Restore script
- `/docker-compose.prod.yml` - Backup cron service
- `/docs/DISASTER_RECOVERY.md` - Recovery procedure

**Technical Notes**:
```bash
#!/bin/bash
# backup-database.sh

DB_HOST=${DB_HOST:-localhost}
DB_NAME=${DB_NAME:-personal_finance}
DB_USER=${DB_USER:-postgres}
BACKUP_DIR="/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump \
    -h $DB_HOST \
    -U $DB_USER \
    -d $DB_NAME \
    | gzip > $BACKUP_FILE

# Verify backup
if [ $? -eq 0 ]; then
    # Calculate md5
    md5sum $BACKUP_FILE > "$BACKUP_FILE.md5"

    # Keep only last 7 days
    find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

    # Notify success
    echo "Backup successful: $BACKUP_FILE" | mail -s "DB Backup Success" admin@example.com
else
    echo "Backup failed!" | mail -s "DB Backup FAILED" admin@example.com
    exit 1
fi

# Weekly backup to S3
if [ $(date +%u) -eq 0 ]; then  # Sunday
    aws s3 cp $BACKUP_FILE s3://your-bucket/backups/
fi
```

---

## WBS-007-04: Implement Backup Management UI

**Effort**: 12 hours | **Dependencies**: WBS-007-03

React UI for backup management in admin panel. View backup history, restore, download.

**Acceptance Criteria**:
- Backup list with: date, size, status
- Download backup (require password)
- Restore from backup (warning dialog)
- Backup retention policy
- Auto-backup toggle
- Backup schedule configuration
- Backup encryption status
- Test restore (non-prod)
- Monitor backup space usage
- Export backup list

**Files**:
- `/frontend/src/pages/Admin/Backups.tsx`
- `/frontend/src/components/features/Backups/`
  - `BackupList.tsx`
  - `RestoreModal.tsx`
  - `BackupSettings.tsx`
- `/backend/app/api/admin/backups.py`
- `/backend/tests/test_api/test_backups.py`

---

## WBS-007-05: Setup Monitoring (Health Checks, Error Tracking)

**Effort**: 16 hours | **Dependencies**: Infrastructure

Monitoring infrastructure: health checks, error tracking (Sentry), performance metrics.

**Acceptance Criteria**:
- Health check endpoint (`/health`)
- Database health check
- Disk space monitoring
- Error tracking (Sentry integration)
- Performance metrics (APM)
- Uptime monitoring (external)
- Alert thresholds (CPU, memory, disk)
- Logging aggregation (ELK, CloudWatch)
- Dashboard (Grafana, Datadog)
- Email alerts on critical issues

**Files**:
- `/backend/app/api/health.py` - Health endpoints
- `/backend/app/monitoring/` - Monitoring setup
  - `__init__.py`
  - `sentry_config.py`
  - `metrics.py`
  - `logging_config.py`
- `/docker-compose.prod.yml` - Monitoring services
- `/scripts/setup-monitoring.sh` - Setup script

**Technical Notes**:
```python
# Health check endpoint
@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    checks = {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': __version__,
        'database': 'unknown',
        'cache': 'unknown',
    }

    # Check database
    try:
        await session.execute(select(1))
        checks['database'] = 'healthy'
    except Exception as e:
        checks['database'] = f'unhealthy: {str(e)}'
        checks['status'] = 'unhealthy'

    # Check Redis
    try:
        redis_client.ping()
        checks['cache'] = 'healthy'
    except Exception as e:
        checks['cache'] = f'unhealthy: {str(e)}'

    status_code = 200 if checks['status'] == 'healthy' else 503
    return JSONResponse(checks, status_code=status_code)

# Sentry integration
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10% of transactions
    environment=settings.environment,
)

# Metrics collection
from prometheus_client import Counter, Histogram

transactions_ingested = Counter(
    'transactions_ingested_total',
    'Total transactions ingested',
    ['source'],
)

parse_duration = Histogram(
    'parser_duration_seconds',
    'Time to parse email',
    ['parser_name'],
)
```

---

## WBS-007-06: Implement Data Export

**Effort**: 12 hours | **Dependencies**: All data features

Export user data as CSV, JSON, PDF. GDPR compliance.

**Acceptance Criteria**:
- Export transactions (CSV, JSON)
- Export all personal data (JSON)
- Full backup export (all data)
- Scheduled exports (weekly/monthly)
- Email export link (secure, expires 7 days)
- Encrypt sensitive data in export
- Remove PII option (anonymize)
- Custom date ranges
- Format options (CSV, JSON, PDF)
- GDPR compliance documentation

**Files**:
- `/backend/app/services/export_service.py`
- `/backend/app/api/exports.py`
- `/backend/app/templates/export/transactions.csv`
- `/frontend/src/pages/Settings/DataExport.tsx`
- `/backend/tests/test_api/test_exports.py`

---

## WBS-007-07: Implement Data Deletion (GDPR-Style Account Deletion)

**Effort**: 14 hours | **Dependencies**: Authentication

GDPR right to be forgotten. Account deletion with data retention options.

**Acceptance Criteria**:
- Account deletion endpoint
- 30-day grace period (reversible)
- Option to keep anonymized data
- Cascade deletion (all related data)
- Data retention logs (audit trail)
- Confirmation email required
- Automatic deletion after grace period
- Gdpr documentation
- Data export before deletion
- Notify third-party integrations

**Files**:
- `/backend/app/services/account_deletion_service.py`
- `/backend/app/api/account.py` - Add deletion endpoint
- `/backend/app/jobs/account_deletion_job.py` - Auto-delete after grace
- `/frontend/src/pages/Settings/AccountDeletion.tsx`
- `/backend/tests/test_api/test_account_deletion.py`

**Technical Notes**:
```python
class AccountDeletionService:
    async def request_deletion(
        self,
        user_id: str,
        keep_anonymized: bool = False
    ) -> dict:
        """Request account deletion (30-day grace period)."""
        user = await get_user(user_id)

        # Create deletion request
        deletion_request = AccountDeletionRequest(
            user_id=user_id,
            requested_at=datetime.now(timezone.utc),
            deletion_date=datetime.now(timezone.utc) + timedelta(days=30),
            keep_anonymized=keep_anonymized,
            status='pending',
        )
        session.add(deletion_request)

        # Send confirmation email
        send_email(
            user.email,
            "Account Deletion Request",
            f"Your account will be deleted in 30 days. Click to cancel: {cancel_link}"
        )

        await session.commit()
        return {'deletion_date': deletion_request.deletion_date}

    async def cancel_deletion(self, user_id: str) -> dict:
        """Cancel pending deletion request."""
        request = await get_pending_deletion_request(user_id)
        if not request:
            raise HTTPException(status_code=404, detail="No deletion request")

        session.delete(request)
        await session.commit()

        send_email(user.email, "Account Deletion Cancelled", "...")
        return {'status': 'cancelled'}

    async def execute_deletion(self, deletion_request: AccountDeletionRequest):
        """Execute deletion when grace period ends."""
        user_id = deletion_request.user_id

        if deletion_request.keep_anonymized:
            # Anonymize instead of delete
            await anonymize_user_data(user_id)
        else:
            # Full deletion
            await cascade_delete_user_data(user_id)

        # Log deletion
        audit_log.info(f"User {user_id} deleted per GDPR request")
```

---

## Summary

**Total Effort**: 80-100 hours

**Critical Security Items**:
- [x] SSL/TLS encryption
- [x] Authentication & authorization
- [x] Data backups & recovery
- [x] Monitoring & alerting
- [x] Data export (user rights)
- [x] Data deletion (user rights)

**Implementation Sequence**:
1. WBS-007-01: SSL/TLS (infrastructure)
2. WBS-007-02: Authentication
3. WBS-007-03: Backups
4. WBS-007-04: Backup management UI
5. WBS-007-05: Monitoring
6. WBS-007-06: Data export
7. WBS-007-07: Data deletion

**Pre-Production Checklist**:
- [ ] All tests passing (100% on critical paths)
- [ ] Staging environment matches production
- [ ] SSL certificate valid
- [ ] Authentication tested
- [ ] First backup created successfully
- [ ] Monitoring configured
- [ ] Runbooks documented
- [ ] Performance benchmarks met
- [ ] Security audit passed
- [ ] Legal review (privacy policy, ToS)

---

*Secure, compliant, production-ready deployment.*
