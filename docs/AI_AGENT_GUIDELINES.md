# Quy Tắc Làm Việc của AI Agent - Personal Finance Tracker

**Phiên bản**: 1.0
**Cập nhật lần cuối**: 2026-03-15

---

## I. QUY TẮC CHUNG

### 1. Bắt đầu task

**LUÔN LUÔN** thực hiện theo trình tự này trước khi bắt đầu bất kỳ task nào:

1. **Đọc `SYSTEM_DESIGN.md`** - Hiểu kiến trúc toàn bộ hệ thống
2. **Đọc file WBS tương ứng** - Xem chi tiết task, acceptance criteria
3. **Kiểm tra dependencies** - Đảm bảo các task phụ thuộc đã xong
4. **Đọc code hiện tại** - Hiểu coding conventions trước khi viết code

### 2. Scope của task

- **Chỉ** sửa file được liệt kê trong "Files to modify"
- **Nếu cần** thêm file mới, đó phải nằm trong "Files to create"
- **Không bao giờ** sửa file ngoài scope (ví dụ: sửa code khác không liên quan)
- **Báo cáo trước** nếu cần thêm file ngoài dự kiến

### 3. Commit message format

```
<type>(<module>): <description>

<detailed explanation if needed>
```

**Types**: `feat` | `fix` | `refactor` | `test` | `docs` | `chore`

**Modules**: `backend` | `frontend` | `parser` | `ui` | `api` | `database`

**Ví dụ**:
```
feat(parser): add Gmail API integration for email sync

- Implement OAuth2 token management
- Add incremental sync using historyId
- Handle rate limiting

Closes WBS-001-01
```

### 4. Testing

- **Mọi logic mới** phải có test
- **Không bao giờ** merge code không có test
- **Test coverage** không được giảm
- **Run tests trước khi commit**: `poetry run pytest` (backend) hoặc `npm test` (frontend)

### 5. Code review

- Đảm bảo code tuân theo conventions
- Kiểm tra type hints, docstrings
- Xác nhận test đã viết
- Kiểm tra error handling

---

## II. BACKEND CONVENTIONS

### Chung

- **Python version**: 3.12+
- **Type hints**: **BẮT BUỘC** cho tất cả functions, methods
- **Async/await**: **BẮT BUỘC** cho tất cả database operations
- **Linting**: `ruff check` (line-length 100)
- **Formatting**: `ruff format`

### Cấu trúc code

```
backend/
├── app/
│   ├── models/          # SQLAlchemy models (chỉ class definitions)
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic, không logic trong models
│   ├── api/             # FastAPI routes
│   ├── parsers/         # Email parsers (kế thừa BaseBankParser)
│   └── utils/           # Utilities (vn_currency, helpers)
├── tests/
│   ├── conftest.py      # Fixtures, factories
│   ├── test_parsers/
│   └── test_utils/
└── alembic/             # Database migrations
```

### Models (app/models/)

**Quy tắc**:
- **Chỉ** chứa class definitions và relationships
- **Không** logic trong model
- **UUID primary keys** (import từ `sqlalchemy import Uuid`)
- **Timestamps**: `created_at`, `updated_at` (timezone-aware)
- **User isolation**: `user_id: Mapped[str]` ở tất cả user-specific models

**Ví dụ**:
```python
from datetime import datetime, timezone
from sqlalchemy import Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Transaction(Base):
    """Transaction model."""
    __tablename__ = "transactions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[str] = mapped_column(Uuid, ForeignKey("accounts.id"))
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
```

### Services (app/services/)

**Quy tắc**:
- **Tất cả business logic** đi vào services
- **Async methods** cho database operations
- **Dependency injection** qua constructor hoặc `Depends()`
- **Type hints** cho tất cả parameters và return types

**Ví dụ**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Transaction
from sqlalchemy import select

class TransactionService:
    """Handle transaction business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_transactions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 10
    ) -> list[Transaction]:
        """Get paginated transactions for user."""
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### API Routes (app/api/)

**Quy tắc**:
- **Validate input** với Pydantic schemas
- **Return appropriate HTTP status** (200, 201, 400, 404, 500)
- **Use dependency injection** cho services
- **Add docstrings** cho endpoints
- **Error handling** với try/except và proper logging

**Ví dụ**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.schemas import TransactionSchema
from app.services import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("/{id}")
async def get_transaction(
    id: str,
    session: AsyncSession = Depends(get_db)
) -> TransactionSchema:
    """Get single transaction by ID."""
    service = TransactionService(session)
    transaction = await service.get_by_id(id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionSchema.from_orm(transaction)
```

### Parsers (app/parsers/)

**Quy tắc**:
- **Tất cả parsers** kế thừa `BaseBankParser`
- **Implement `parse()` method** - nhận email body, trả về `ParsedTransaction | None`
- **Register trong `ParserRegistry`** - auto-discovery từ `app/parsers/banks/` directory
- **Priority**: parsers có priority cao được chọn trước
- **Logging**: đăng ký parse successes/failures

**Cấu trúc mới**:
```
app/parsers/
├── base.py              # BaseBankParser abstract class
├── registry.py          # ParserRegistry singleton
└── banks/
    ├── cake_vpbank.py   # Cake/VPBank parser
    ├── techcombank.py   # New parser
    └── vietinbank.py    # Another parser
```

**Ví dụ parser mới**:
```python
from app.parsers.base import BaseBankParser, ParsedTransaction, TransactionDirection

class TechcombankParser(BaseBankParser):
    """Parser for Techcombank transaction emails."""

    name = "techcombank"
    priority = 100  # Higher priority = checked first
    pattern = r"techcombank|transfering from techcombank"

    async def parse(self, email_body: str) -> ParsedTransaction | None:
        """Parse Techcombank transaction email."""
        # Implementation
        # Return ParsedTransaction or None
        pass
```

**Đăng ký parser**: Auto-discover khi file đặt trong `app/parsers/banks/`

### Schemas (app/schemas/)

**Quy tắc**:
- **Pydantic models** cho request/response validation
- **Separate schemas** cho input (create/update) và output (response)
- **Type hints** bắt buộc
- **Field validation** với `Field()` validators

**Ví dụ**:
```python
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class TransactionCreateSchema(BaseModel):
    """Schema for creating transaction."""
    account_id: str
    amount: Decimal = Field(gt=0)
    description: str
    category_id: str | None = None

class TransactionSchema(TransactionCreateSchema):
    """Schema for transaction response."""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### Database Migrations (alembic/)

**Quy tắc**:
- **Tất cả schema changes** phải có migration
- **Async migration** vì backend là async
- **Backward compatible** nếu có thể
- **Naming**: `YYYYMMDD_HH_description.py`

**Tạo migration**:
```bash
cd backend
poetry run alembic revision --autogenerate -m "Add field to transactions"
poetry run alembic upgrade head  # Run migration
```

### Testing (tests/)

**Quy tắc**:
- **pytest** + `async` fixtures
- **In-memory SQLite** hoặc PostgreSQL test database
- **Factory pattern** cho test data
- **100% coverage** cho business logic (services, parsers)
- **Mocking** cho external APIs (Gmail, etc.)

**Ví dụ**:
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def transaction_factory(session: AsyncSession):
    """Factory for creating test transactions."""
    async def _create(**kwargs):
        transaction = Transaction(**kwargs)
        session.add(transaction)
        await session.commit()
        return transaction
    return _create

@pytest.mark.asyncio
async def test_get_transactions(session: AsyncSession, transaction_factory):
    """Test fetching transactions."""
    await transaction_factory(amount=100, description="Test")

    service = TransactionService(session)
    transactions = await service.get_user_transactions("user_123")

    assert len(transactions) == 1
    assert transactions[0].amount == 100
```

### Logging

**Quy tắc**:
- Sử dụng `logging` module
- **INFO** cho business events
- **DEBUG** cho detailed information
- **ERROR** cho errors, **WARNING** cho warnings

```python
import logging

logger = logging.getLogger(__name__)

async def parse_email(email_body: str):
    logger.debug(f"Parsing email: {email_body[:50]}...")
    try:
        transaction = await parser.parse(email_body)
        logger.info(f"Successfully parsed transaction: {transaction.id}")
        return transaction
    except Exception as e:
        logger.error(f"Failed to parse email: {e}")
        raise
```

---

## III. FRONTEND CONVENTIONS

### Chung

- **TypeScript**: Strict mode (`"strict": true` trong tsconfig.json)
- **React 18+**: Functional components + hooks only
- **Node.js**: 16+
- **Package manager**: npm
- **Linting**: `npm run lint` (eslint)
- **Formatting**: `npm run format` (prettier)

### Cấu trúc code

```
frontend/src/
├── components/
│   ├── common/           # Reusable components
│   ├── ui/              # UI components (Button, Card, etc.)
│   ├── layout/          # Layout components (Header, Sidebar)
│   ├── pages/           # Page components
│   └── features/        # Feature-specific components
├── hooks/               # Custom React hooks
├── services/            # API services (useQuery, useMutation)
├── store/               # Zustand global state
├── types/               # TypeScript types
├── utils/               # Utility functions
├── styles/              # Global styles (Tailwind config)
└── pages/               # Route pages
```

### Components (src/components/)

**Quy tắc**:
- **Functional components** chỉ, không class components
- **Hooks only** - useState, useEffect, custom hooks
- **Props**: TypeScript interface
- **Styling**: Tailwind CSS classes only, không inline styles, không CSS modules
- **Vietnamese text**: Tất cả user-facing text phải tiếng Việt
- **Docstrings**: JSDoc cho components phức tạp

**Ví dụ**:
```typescript
import React from 'react';
import { Button } from '@/components/ui/Button';
import { clsx } from 'clsx';

interface TransactionCardProps {
  id: string;
  amount: number;
  description: string;
  category: string;
  onEdit: (id: string) => void;
}

/**
 * Display a single transaction with edit capability.
 * @param props Component props
 */
export const TransactionCard: React.FC<TransactionCardProps> = ({
  id,
  amount,
  description,
  category,
  onEdit,
}) => {
  return (
    <div className={clsx(
      'p-4 border rounded-lg',
      'hover:bg-gray-50 transition-colors',
      'cursor-pointer'
    )}>
      <div className="flex justify-between items-center">
        <div>
          <p className="font-medium text-gray-900">{description}</p>
          <p className="text-sm text-gray-600">{category}</p>
        </div>
        <div className="text-right">
          <p className="font-semibold text-gray-900">
            {new Intl.NumberFormat('vi-VN', {
              style: 'currency',
              currency: 'VND',
            }).format(amount)}
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(id)}
          >
            Sửa
          </Button>
        </div>
      </div>
    </div>
  );
};
```

### Hooks (src/hooks/)

**Quy tắc**:
- **Custom hooks** cho logic tái sử dụng được
- **React Query hooks** cho server state (useQuery, useMutation)
- **Zustand hooks** cho global state
- **Type safe** - đầu vào và đầu ra đều typed

**Ví dụ**:
```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { transactionService } from '@/services/transactionService';

export const useTransactions = (userId: string) => {
  return useQuery({
    queryKey: ['transactions', userId],
    queryFn: () => transactionService.getTransactions(userId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useCreateTransaction = () => {
  return useMutation({
    mutationFn: transactionService.createTransaction,
    onSuccess: () => {
      // Invalidate cache
    },
  });
};
```

### API Services (src/services/)

**Quy tắc**:
- **Không gọi API trực tiếp** từ components
- **Tất cả API calls** đi qua services
- **Services return Promises** với properly typed responses
- **Error handling** với try/catch
- **Type safe** - TypeScript interfaces cho requests/responses

**Ví dụ**:
```typescript
import axios from 'axios';

export interface Transaction {
  id: string;
  amount: number;
  description: string;
  category_id: string;
  created_at: string;
}

export interface CreateTransactionRequest {
  account_id: string;
  amount: number;
  description: string;
  category_id?: string;
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

export const transactionService = {
  async getTransactions(userId: string): Promise<Transaction[]> {
    const response = await api.get<Transaction[]>(`/transactions`, {
      params: { user_id: userId },
    });
    return response.data;
  },

  async createTransaction(data: CreateTransactionRequest): Promise<Transaction> {
    const response = await api.post<Transaction>('/transactions', data);
    return response.data;
  },

  async updateTransaction(
    id: string,
    data: Partial<CreateTransactionRequest>
  ): Promise<Transaction> {
    const response = await api.put<Transaction>(`/transactions/${id}`, data);
    return response.data;
  },
};
```

### Global State (src/store/)

**Quy tắc**:
- **Zustand** cho global state (không Redux)
- **Separate stores** cho mỗi feature (auth, transactions, ui)
- **Type safe** với TypeScript
- **Không side effects** trong actions (keep actions pure)

**Ví dụ**:
```typescript
import { create } from 'zustand';

interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthStore {
  user: User | null;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isLoading: false,
  setUser: (user) => set({ user }),
  setLoading: (isLoading) => set({ isLoading }),
}));
```

### Styling (Tailwind)

**Quy tắc**:
- **Tailwind CSS classes** chỉ
- **Không inline styles** (`style={{ color: 'red' }}`)
- **Không CSS modules** (`.module.css`)
- **Không custom CSS** ngoài Tailwind config
- **Use `clsx`** hoặc `tailwind-merge` để conditional classes

**Ví dụ**:
```typescript
import { clsx } from 'clsx';

// GOOD
<div className={clsx(
  'p-4 rounded-lg border',
  isActive && 'bg-blue-500 text-white',
  isDisabled && 'opacity-50 cursor-not-allowed',
)}>
  Content
</div>

// BAD
<div style={{ padding: '16px', backgroundColor: 'blue' }}>
  Content
</div>
```

### TypeScript

**Quy tắc**:
- **Strict mode**: `"strict": true`
- **No `any` type**: Luôn typed
- **Interfaces** cho objects, props
- **Types** cho unions, primitives

**Ví dụ**:
```typescript
// GOOD - Explicit types
interface Props {
  id: string;
  amount: number;
  status: 'pending' | 'completed' | 'failed';
  onSubmit: (data: SubmitData) => Promise<void>;
}

// BAD - No types
function MyComponent(props) {
  // ...
}

// BAD - Using `any`
function handleData(data: any) {
  // ...
}
```

### Testing (Jest/Vitest)

**Quy tắc**:
- **Test files**: `*.test.ts` hoặc `*.test.tsx`
- **Test critical features**: components, hooks, services
- **Mock API calls** với `vi.mock()` hoặc `jest.mock()`
- **Render components** với React Testing Library

**Ví dụ**:
```typescript
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { TransactionCard } from '@/components/TransactionCard';

describe('TransactionCard', () => {
  it('should render transaction details', () => {
    const onEdit = vi.fn();
    render(
      <TransactionCard
        id="1"
        amount={100000}
        description="Groceries"
        category="Food"
        onEdit={onEdit}
      />
    );

    expect(screen.getByText('Groceries')).toBeInTheDocument();
    expect(screen.getByText('Food')).toBeInTheDocument();
  });

  it('should call onEdit when edit button clicked', async () => {
    const onEdit = vi.fn();
    const { user } = render(
      <TransactionCard
        id="1"
        amount={100000}
        description="Groceries"
        category="Food"
        onEdit={onEdit}
      />
    );

    await user.click(screen.getByText('Sửa'));
    expect(onEdit).toHaveBeenCalledWith('1');
  });
});
```

---

## IV. DATABASE CONVENTIONS

### Migrations (Alembic)

**Quy tắc**:
- **Tất cả schema changes** phải có migration
- **Không bao giờ** sửa trực tiếp database
- **Migrations phải reversible** (có downgrade)
- **Naming convention**: `YYYYMMDD_HH_description.py`

**Ví dụ migration**:
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Add payment_method column to transactions."""
    op.add_column(
        'transactions',
        sa.Column('payment_method', sa.String(50), nullable=True)
    )
    # Create index for faster queries
    op.create_index(
        'ix_transactions_payment_method',
        'transactions',
        ['payment_method']
    )

def downgrade():
    """Remove payment_method column."""
    op.drop_index('ix_transactions_payment_method')
    op.drop_column('transactions', 'payment_method')
```

### Naming Conventions

**Tables & Columns**: `snake_case`
```python
class Transaction(Base):
    __tablename__ = "transactions"
    user_id: Mapped[str]           # snake_case
    payment_method: Mapped[str]    # snake_case
    created_at: Mapped[datetime]
```

**Primary Keys**: UUID
```python
class Transaction(Base):
    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
```

**Timestamps**: Timezone-aware
```python
from datetime import datetime, timezone

created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc)
)
```

**Foreign Keys**: Explicit với `ForeignKey()`
```python
user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
```

**Indexes**: Cho frequently queried columns
```python
class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index('ix_transactions_user_account', 'user_id', 'account_id'),
        Index('ix_transactions_created', 'created_at'),
    )
```

---

## V. CÁCH NHẬN TASK

### Quy trình

1. **Đọc WBS file** tương ứng
   - Ví dụ: `WBS-001-01` đọc `docs/wbs/WBS-001-email-parser-engine.md`

2. **Xem chi tiết task**:
   - ID, Title, Description
   - Priority (P0-P3)
   - Estimated effort
   - Dependencies (check trước khi bắt đầu)
   - Files to create/modify
   - Acceptance criteria (testable)
   - Test requirements

3. **Kiểm tra dependencies**
   - Các task phụ thuộc đã xong chưa?
   - Các PR của dependencies đã merge chưa?

4. **Làm task**
   - Follow tất cả conventions
   - Viết test
   - Commit theo format

5. **Report kết quả**
   ```
   Task: WBS-001-01
   Status: COMPLETED

   Files created:
   - /backend/app/services/gmail_sync.py
   - /backend/tests/test_gmail_sync.py

   Files modified:
   - /backend/app/api/router.py

   Test results: All 15 tests passed

   Notes:
   - Implemented OAuth2 token management
   - Added retry logic for API failures
   ```

---

## VI. CODING STANDARDS CHECKLIST

### Backend

- [ ] Type hints trên tất cả functions
- [ ] Docstrings cho classes/public methods
- [ ] Async/await cho DB operations
- [ ] Error handling với logging
- [ ] Tests viết (pytest)
- [ ] `poetry run ruff check` pass
- [ ] `poetry run pytest` pass (all tests)
- [ ] Dependencies checked (không thêm dependencies không cần)
- [ ] Migrations created nếu schema change
- [ ] Commit message theo format

### Frontend

- [ ] TypeScript strict mode
- [ ] Props properly typed (interfaces)
- [ ] No `any` types
- [ ] Tailwind CSS only (no inline styles)
- [ ] Vietnamese text
- [ ] Tests viết (vitest/jest)
- [ ] `npm run lint` pass
- [ ] `npm run format` run
- [ ] `npm test` pass (all tests)
- [ ] Commit message theo format

---

## VII. TROUBLESHOOTING

### Backend

**Issue**: `ModuleNotFoundError: No module named 'app'`
- Solution: `cd backend && poetry install && poetry shell`

**Issue**: Database connection failed
- Check `.env` file, database URL correct?
- Run migrations: `poetry run alembic upgrade head`

**Issue**: Async error in tests
- Use `@pytest.mark.asyncio` decorator
- Check fixture is async (`async def`)

**Issue**: Linting errors
- Run: `poetry run ruff check --fix`
- Run: `poetry run ruff format`

### Frontend

**Issue**: `Module not found: Can't resolve '@/components/...'`
- Check `vite.config.ts` alias config
- Restart dev server: `npm run dev`

**Issue**: TypeScript errors
- Run: `npm run lint`
- Check types in `src/types/`

**Issue**: Tailwind classes not applied
- Clear cache: `rm -rf node_modules/.vite`
- Restart dev server

---

## VIII. THỜI GIAN PHẢN HỒI EXPECTED

AI agent nên:
- **Nhận task** → Báo cáo trong vòng 5 phút
- **Bắt đầu làm** → Báo cáo progress mỗi 30 phút
- **Xong task** → Báo cáo final result trong vòng 24 giờ (theo ước tính effort)

---

## IX. LIÊN HỆ & HỖ TRỢ

**Cần help?**
- Đọc `SYSTEM_DESIGN.md` - giải đáp hầu hết câu hỏi
- Check hiện tại code - học từ ví dụ
- Xem test files - hiểu cách test code
- Báo cáo blocker ngay - không chờ

---

**Happy coding! 🚀**
