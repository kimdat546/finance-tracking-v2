# Personal Finance Tracking System — System Design Document

> **Author:** Nguyễn Kim Đạt
> **Created:** 2026-03-14
> **Status:** Draft — High Level Design
> **Language:** Vietnamese + English (technical terms)

---

## 1. Tổng quan hệ thống (System Overview)

### 1.1 Mục tiêu

Xây dựng hệ thống quản lý tài chính cá nhân toàn diện, **tự động hóa tối đa** việc thu thập và phân loại dữ liệu, giúp đưa ra quyết định tài chính dựa trên data thực tế.

### 1.2 Nguyên tắc thiết kế

- **Zero manual input** — Tối thiểu việc nhập liệu thủ công. Data chủ yếu từ email ngân hàng tự động.
- **Data ownership** — Toàn bộ data nằm trên máy cá nhân, không gửi lên third-party.
- **Plugin architecture** — Mỗi ngân hàng là một parser plugin, dễ mở rộng.
- **Self-evolving parsers** — Hệ thống tự phát hiện email format mới và gợi ý tạo/cập nhật parser.
- **Smart defaults, manual override** — Hệ thống tự phân loại nhưng cho phép người dùng chỉnh sửa.
- **Long-term data** — Thiết kế schema cho phân tích xu hướng dài hạn (năm).
- **Multi-tenant ready** — Thiết kế cho single user trước nhưng schema sẵn sàng mở rộng multi-user.

### 1.3 User Profile

- Software engineer tại Việt Nam
- Dùng nhiều ngân hàng VN (Cake/VPBank, VCB, TCB, MB, ACB, BIDV, TPBank...)
- Thanh toán chủ yếu bằng chuyển khoản + credit card
- Nhiều subscription (SaaS, dev tools, streaming...)
- Thường xuyên ăn trưa chung với đồng nghiệp → cần split bill
- Có nhu cầu theo dõi vay nợ, tiết kiệm, mục tiêu tài chính

---

## 2. Kiến trúc hệ thống (System Architecture)

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  DATA INGESTION LAYER (Hybrid)                  │
│                                                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────┐│
│  │ A: Gmail API │ │ B: Client-   │ │ C: Apps    │ │D: CSV/   ││
│  │ (server-side)│ │ Side Parse   │ │ Script     │ │Manual    ││
│  │ [self-hosted]│ │ [recommended]│ │ [auto+priv]│ │[fallback]││
│  └──────┬──────┘ └──────┬───────┘ └─────┬──────┘ └────┬─────┘│
│         │                │                      │               │
│         ▼                ▼                      ▼               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              EMAIL PARSER ENGINE (Plugin-based)             ││
│  │                                                             ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      ││
│  │  │  Cake/   │ │   VCB    │ │   TCB    │ │ Dynamic  │ ...  ││
│  │  │  VPBank  │ │  Parser  │ │  Parser  │ │ (JSON)   │      ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      ││
│  │                                                             ││
│  │  ┌─────────────────────────────────────────────────────┐   ││
│  │  │  Parser Auto-Discovery Engine                       │   ││
│  │  │  → Fingerprint → Similarity Match → Suggest/Create  │   ││
│  │  └─────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PROCESSING LAYER                            │
│                                                                 │
│  ┌───────────────────┐  ┌───────────────────┐                  │
│  │  Auto Categorizer │  │  Duplicate         │                  │
│  │  (rule-based +    │  │  Detector          │                  │
│  │   learning)       │  │                    │                  │
│  └───────────────────┘  └───────────────────┘                  │
│  ┌───────────────────┐  ┌───────────────────┐                  │
│  │  Subscription     │  │  Split Bill        │                  │
│  │  Detector         │  │  Auto-Matcher      │                  │
│  └───────────────────┘  └───────────────────┘                  │
│  ┌───────────────────┐                                          │
│  │  Pending Review   │ ← Giao dịch chưa phân loại được         │
│  │  Queue            │                                          │
│  └───────────────────┘                                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA STORAGE LAYER                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    PostgreSQL Database                      ││
│  │                                                             ││
│  │  Core: transactions, accounts, categories, rules            ││
│  │  Social: split_groups, split_bills, settlements             ││
│  │  Planning: goals, budgets, debts, subscriptions             ││
│  │  System: email_sync_log, parser_errors, user_settings       ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                          │
│                                                                 │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐│
│  │     FastAPI Backend          │  │    React Frontend        ││
│  │                              │  │                          ││
│  │  - REST API                  │  │  - Dashboard             ││
│  │  - WebSocket (realtime)      │  │  - Transaction list      ││
│  │  - Scheduler (email sync)    │  │  - Split bill UI         ││
│  │  - Report generator          │  │  - Goals & Budget        ││
│  └──────────────────────────────┘  │  - Reports & Charts      ││
│                                     └──────────────────────────┘│
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      NOTIFICATION LAYER                         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐│
│  │ Weekly Digest │  │ Budget Alert │  │  Pending Review Nudge  ││
│  │ (Email)       │  │ (Email/Web)  │  │  (Web notification)    ││
│  └──────────────┘  └──────────────┘  └────────────────────────┘│
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ Subscription │  │ Debt Due     │                            │
│  │ Renewal Alert│  │ Reminder     │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Tech Stack Decision

| Layer | Technology | Lý do chọn |
|-------|-----------|-------------|
| **Backend** | Python 3.12 + FastAPI | Ecosystem mạnh cho data processing, email parsing. FastAPI có async support, auto-generated API docs. |
| **Frontend** | React 18 + TypeScript + Vite | Component-based, TypeScript cho type safety khi project lớn dần. Vite cho DX tốt. |
| **Database** | PostgreSQL 16 | JSON column cho raw email data, window functions cho time-series analysis, full-text search. |
| **ORM** | SQLAlchemy 2.0 + Alembic | Type-safe queries, migration management. |
| **Scheduler** | APScheduler (ban đầu) → Celery + Redis (khi scale) | APScheduler đơn giản cho single-server. Migrate lên Celery nếu cần. |
| **Email** | google-api-python-client | Official Gmail API client. Read-only OAuth2 scope. |
| **HTML Parser** | BeautifulSoup4 + lxml | Parse email HTML content. Robust, well-tested. |
| **Charts** | Recharts (frontend) | React-native charting, declarative API. |
| **Containerization** | Docker + Docker Compose | Reproducible environment, dễ deploy. |

---

## 3. Email Parser Engine — Thiết kế chi tiết

### 3.1 Plugin Architecture

```
email_parsers/
├── base.py              # Abstract base class cho mọi parser
├── registry.py          # Auto-discovery & registration
├── cake_vpbank.py       # Cake by VPBank parser
├── vietcombank.py       # Vietcombank parser
├── techcombank.py       # Techcombank parser (credit card)
├── mbbank.py            # MB Bank parser
├── acb.py               # ACB parser
├── bidv.py              # BIDV parser
├── tpbank.py            # TPBank parser
└── generic.py           # Fallback parser dùng AI/heuristics
```

### 3.2 Base Parser Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class TransactionDirection(Enum):
    INCOMING = "incoming"   # Tiền vào
    OUTGOING = "outgoing"   # Tiền ra
    INTERNAL = "internal"   # Chuyển nội bộ


class TransactionType(Enum):
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH_DEPOSIT = "cash_deposit"
    CASH_WITHDRAWAL = "cash_withdrawal"
    INTEREST = "interest"
    FEE = "fee"
    REFUND = "refund"
    SUBSCRIPTION = "subscription"
    OTHER = "other"


@dataclass
class ParsedTransaction:
    """Kết quả parse từ email — schema chuẩn cho mọi ngân hàng"""

    # --- Required fields ---
    bank_name: str                          # "cake_vpbank", "vietcombank", ...
    transaction_date: datetime              # Ngày giờ giao dịch
    amount: Decimal                         # Số tiền (luôn dương)
    currency: str                           # "VND", "USD"
    direction: TransactionDirection         # incoming/outgoing

    # --- Strongly expected fields ---
    account_number: Optional[str] = None    # Số tài khoản
    transaction_id: Optional[str] = None    # Mã giao dịch từ ngân hàng
    transaction_type: TransactionType = TransactionType.BANK_TRANSFER
    description: Optional[str] = None       # Nội dung giao dịch
    fee: Decimal = Decimal("0")             # Phí giao dịch

    # --- Optional fields (tuỳ ngân hàng cung cấp) ---
    counterparty_name: Optional[str] = None     # Tên người chuyển/nhận
    counterparty_account: Optional[str] = None  # Số TK người chuyển/nhận
    counterparty_bank: Optional[str] = None     # Ngân hàng người chuyển/nhận
    balance_after: Optional[Decimal] = None     # Số dư sau giao dịch
    card_number: Optional[str] = None           # 4 số cuối thẻ (nếu credit card)
    merchant_name: Optional[str] = None         # Tên merchant (credit card)

    # --- Metadata ---
    raw_email_id: Optional[str] = None      # Gmail message ID
    raw_email_subject: Optional[str] = None
    raw_email_date: Optional[datetime] = None
    confidence_score: float = 1.0           # 0.0-1.0, parser tự đánh giá độ tin cậy


class BaseBankParser(ABC):
    """Base class cho mọi bank email parser"""

    @property
    @abstractmethod
    def bank_name(self) -> str:
        """Tên định danh ngân hàng, ví dụ: 'cake_vpbank'"""
        pass

    @property
    @abstractmethod
    def sender_patterns(self) -> list[str]:
        """Danh sách email sender patterns để filter.
        Ví dụ: ['noreply@cake.vn', '*@vpbank.com.vn']
        """
        pass

    @property
    @abstractmethod
    def subject_patterns(self) -> list[str]:
        """Regex patterns cho email subject.
        Ví dụ: ['Thông báo giao dịch', 'Transaction notification']
        """
        pass

    @abstractmethod
    def can_parse(self, email_subject: str, email_from: str, email_body: str) -> bool:
        """Kiểm tra xem parser này có xử lý được email này không.
        Dùng để resolve khi nhiều parser cùng match.
        """
        pass

    @abstractmethod
    def parse(self, email_subject: str, email_body_html: str, email_metadata: dict) -> ParsedTransaction:
        """Parse email HTML thành ParsedTransaction.
        Raise ParserError nếu không parse được.
        """
        pass

    def validate(self, txn: ParsedTransaction) -> list[str]:
        """Validate kết quả parse. Trả về list warnings (empty = OK)."""
        warnings = []
        if txn.amount <= 0:
            warnings.append("Amount should be positive")
        if txn.transaction_date > datetime.now():
            warnings.append("Transaction date is in the future")
        if not txn.transaction_id:
            warnings.append("Missing transaction_id — duplicate detection may be unreliable")
        return warnings
```

### 3.3 Cake by VPBank Parser — Phân tích từ email mẫu

```python
"""
=== PHÂN TÍCH CẤU TRÚC EMAIL CAKE BY VPBANK ===

Email format: HTML table-based layout
Sender: noreply@cake.vn (hoặc tương tự, cần verify thêm)
Nhận diện: Logo Cake, text "Cake xin thông báo tài khoản của bạn"

Cấu trúc email gồm 2 bảng chính:

1. BẢNG "Thông tin tài khoản":
   ┌─────────────────────┬────────────────────────────────────┐
   │ Tài khoản nhận      │ 0396616164 - Tài khoản thanh toán  │
   │ Tài khoản chuyển    │ n/a                                │
   │ Tên người chuyển    │ n/a                                │
   └─────────────────────┴────────────────────────────────────┘

2. BẢNG "Thông tin giao dịch":
   ┌─────────────────────┬────────────────────────────────────┐
   │ Loại giao dịch      │ Chuyển tiền từ VPBank              │
   │ Mã giao dịch        │ 402297749                          │
   │ Ngày giờ giao dịch  │ 14/03/2026, 22:28:37               │
   │ Số tiền             │ +10.000 đ (color: #188126 = green) │
   │ Phí giao dịch       │ 0 đ                                │
   │ Nội dung giao dịch  │ NGUYEN KIM DAT transfer            │
   └─────────────────────┴────────────────────────────────────┘

=== CÁC TRƯỜNG HỢP CẦN XỬ LÝ ===

1. Direction detection:
   - Số tiền có prefix "+" và color #188126 (green) → INCOMING
   - Số tiền có prefix "-" và color #dc3545 (red, cần verify) → OUTGOING
   - Cần verify thêm email giao dịch chuyển đi để xác nhận format

2. Amount parsing:
   - Format: "+10.000 đ" hoặc "-10.000 đ"
   - Dấu chấm (.) là thousand separator (VN format)
   - Có thể có dấu phẩy cho decimal? (cần verify)
   - Currency: "đ" hoặc "VND"

3. Date parsing:
   - Format: "DD/MM/YYYY, HH:MM:SS"
   - Timezone: GMT+7 (Vietnam)

4. Counterparty detection:
   - "Tên người chuyển" có thể là "n/a" khi không có info
   - "Tài khoản chuyển" cũng có thể "n/a"
   - Nội dung giao dịch thường chứa tên người chuyển

5. Transaction type detection:
   - "Chuyển tiền từ VPBank" → internal transfer
   - "Chuyển tiền từ [Ngân hàng khác]" → incoming interbank
   - Cần collect thêm mẫu: credit card, thanh toán bill, etc.

=== CÂU HỎI CẦN LÀM RÕ (cần thêm email mẫu) ===

Q1: Email giao dịch CHI (chuyển tiền đi) có format giống không?
    → Cần mẫu email khi bạn chuyển tiền cho người khác

Q2: Email credit card transaction có cùng format không?
    → Cake có credit card không? Hay credit card là VPBank riêng?

Q3: Các loại giao dịch khác:
    - Thanh toán QR / VNPay?
    - Nạp tiền điện thoại?
    - Thanh toán hóa đơn (điện, nước, internet)?
    - Nhận lãi tiết kiệm?

Q4: Email sender chính xác? (noreply@cake.vn? notification@cake.vn?)

Q5: Khi "Tên người chuyển" là "n/a", có phải vì đây là
    chuyển khoản từ chính mình (VPBank → Cake)?
"""

# === IMPLEMENTATION SKETCH ===

class CakeVPBankParser(BaseBankParser):
    bank_name = "cake_vpbank"
    sender_patterns = ["*@cake.vn", "*@be.com.vn"]  # Cake dùng domain be.com.vn cho email
    subject_patterns = [r"Thông báo giao dịch", r"Biến động số dư"]

    # Parsing strategy:
    # 1. Dùng BeautifulSoup parse HTML
    # 2. Tìm section "Thông tin tài khoản" và "Thông tin giao dịch"
    # 3. Mỗi section là một <table>, iterate qua <tr> để lấy key-value pairs
    # 4. Key nằm ở <td> thứ 2 (index 1), Value ở <td> thứ 6 (index 5)
    #    (do HTML table có nhiều td spacer)
    # 5. Parse amount: detect color style cho direction, parse số tiền
    # 6. Parse date: strptime với format "DD/MM/YYYY, HH:MM:SS"
```

### 3.4 Gmail API — Smart Filtering Strategy

#### 3.4.1 Vấn đề: Không cần đọc tất cả email

Mỗi ngày có thể có hàng trăm đến hàng ngàn email. Gmail API hỗ trợ **server-side filtering**
qua tham số `q` (query) — Google lọc trên server, chỉ trả về email match.
App **không bao giờ** phải tải tất cả email rồi tự lọc.

#### 3.4.2 Chiến lược filter: Gmail Label + historyId (Đề xuất)

**Bước 1 — Setup (một lần):** User tạo Gmail filter rule trong Gmail Settings:

```
Matches: from:(noreply@cake.vn OR alert@vietcombank.com.vn OR ...)
Do this: Apply label "Finance", Never send it to Spam
```

**Bước 2 — Sync lần đầu (full sync):**

```python
# Chỉ lấy email có label "Finance"
messages = gmail.users().messages().list(
    userId='me',
    q='label:Finance',
    maxResults=500
).execute()

# Lưu historyId cuối cùng
save_last_history_id(messages['historyId'])
```

**Bước 3 — Sync incremental (lần 2+):**

```python
# Chỉ lấy email MỚI kể từ lần sync trước
# Gmail trả về ONLY changes, không scan lại từ đầu
changes = gmail.users().history().list(
    userId='me',
    startHistoryId=last_saved_history_id,
    labelId='Finance_Label_ID'
).execute()
# → Cực nhanh, chỉ trả về 0-5 emails mới
```

**Kết quả:** Thay vì scan hàng ngàn email, mỗi lần sync chỉ xử lý ~0-5 email mới.
API quota gần như không bao giờ chạm limit (free tier: 250 units/giây).

#### 3.4.3 Gmail Label Management

```
Gmail Labels cho hệ thống:

📂 Finance/                     ← User tạo filter rule auto-apply label này
   📂 Finance/Processed         ← Hệ thống gắn sau khi parse thành công
   📂 Finance/NeedsReview       ← Parse có warning hoặc chưa categorize
   📂 Finance/ParseFailed       ← Parse thất bại, cần kiểm tra

Flow:
1. Email mới từ ngân hàng → Gmail auto-apply "Finance" label
2. Hệ thống sync → đọc email có "Finance" nhưng KHÔNG có "Finance/Processed"
3. Parse thành công → gắn "Finance/Processed"
4. Parse fail → gắn "Finance/ParseFailed"
5. Lần sync sau → bỏ qua email đã có "Finance/Processed"
```

#### 3.4.4 Integration Flow (Updated)

```
┌──────────────┐     ┌─────────────┐     ┌──────────────────────────┐
│   Scheduler  │────▶│  Gmail API  │────▶│ Query:                   │
│ (mỗi 15min)  │     │  (read-only)│     │ label:Finance            │
└──────────────┘     └─────────────┘     │ -label:Finance/Processed │
                                          │ historyId > last_sync    │
                                          └────────────┬─────────────┘
                                                       │
                                            Chỉ 0-5 email mới/lần
                                                       │
                                                       ▼
                                                ┌──────────────┐
                                                │Parser Registry│
                                                │              │
                                                │ Match email  │
                                                │ → parser     │
                                                └──────┬───────┘
                                                       │
                              ┌─────────────────────────┼──────────────────┐
                              ▼                         ▼                  ▼
                        ┌───────────┐          ┌────────────┐      ┌────────────┐
                        │ Parsed OK │          │ Parse      │      │ No parser  │
                        │           │          │ Warning    │      │ matched    │
                        └─────┬─────┘          └─────┬──────┘      └─────┬──────┘
                              │                      │                   │
                              ▼                      ▼                   ▼
                        ┌───────────┐          ┌────────────┐      ┌────────────┐
                        │ Save txn  │          │ Save txn + │      │ Fingerprint│
                        │ to DB     │          │ add to     │      │ → Auto     │
                        │           │          │ review     │      │ Discovery  │
                        │ Label:    │          │ queue      │      │ Engine     │
                        │ Finance/  │          │            │      │            │
                        │ Processed │          │ Label:     │      │ Label:     │
                        │           │          │ Finance/   │      │ Finance/   │
                        └───────────┘          │ NeedsReview│      │ ParseFailed│
                                               └────────────┘      └────────────┘
```

### 3.5 Duplicate Detection Strategy

Email ngân hàng có thể bị fetch nhiều lần. Chiến lược chống trùng:

1. **Primary key:** `(bank_name, transaction_id)` — Mã giao dịch ngân hàng là unique
2. **Fallback (nếu không có transaction_id):** `(bank_name, account_number, amount, date, description)` — composite unique
3. **Gmail message ID:** Lưu `raw_email_id` để biết email nào đã xử lý
4. **Gmail label:** Gắn label "finance-processed" lên email đã parse xong → filter bỏ khi sync lần sau

### 3.6 Parser Auto-Discovery Engine (Self-Evolving System)

Đây là tính năng giúp hệ thống **tự phát triển** — tự phát hiện email format mới từ ngân hàng
và gợi ý tạo parser mới hoặc cập nhật parser cũ.

#### 3.6.1 Tổng quan flow

```
Email mới vào (không parser nào match)
       │
       ▼
┌──────────────────────────────────────┐
│  STEP 1: Email Fingerprinting        │
│                                      │
│  Trích xuất "fingerprint" của email: │
│  - sender domain                     │
│  - subject keywords                  │
│  - HTML structure signature          │
│  - Key text patterns                 │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│  STEP 2: Similarity Matching         │
│                                      │
│  So sánh fingerprint với các parser  │
│  đã có trong hệ thống               │
│                                      │
│  Similarity score:                   │
│  - sender domain match     (40%)     │
│  - HTML structure similar  (30%)     │
│  - keyword overlap         (20%)     │
│  - amount/date pattern     (10%)     │
└───────────────┬──────────────────────┘
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
  Score > 0.7   0.3-0.7   < 0.3
       │        │         │
       ▼        ▼         ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│ CASE A:  │ │ CASE B:  │ │ CASE C:      │
│ Có thể   │ │ Có thể   │ │ Ngân hàng    │
│ là phiên │ │ là loại  │ │ hoàn toàn    │
│ bản mới  │ │ GD mới   │ │ mới          │
│ của      │ │ của cùng │ │              │
│ parser   │ │ ngân hàng│ │              │
│ hiện tại │ │          │ │              │
└─────┬────┘ └─────┬────┘ └──────┬───────┘
      │            │             │
      ▼            ▼             ▼
  Notify user  Notify user   Notify user
  "Parser X    "Ngân hàng Y  "Email từ
  có vẻ đã     có loại GD    domain Z
  thay đổi     mới chưa có   chưa có
  format.      parser.       parser nào.
  Cập nhật?"   Tạo mới?"    Tạo mới?"
```

#### 3.6.2 Email Fingerprinting — Chi tiết

```python
@dataclass
class EmailFingerprint:
    """Dấu vân tay của email — dùng để nhận diện và so sánh"""

    # === Sender info ===
    sender_email: str                    # "noreply@cake.vn"
    sender_domain: str                   # "cake.vn"
    sender_root_domain: str              # "cake.vn" (tách subdomain)

    # === Subject analysis ===
    subject: str                         # "Thông báo giao dịch"
    subject_keywords: list[str]          # ["thông báo", "giao dịch"]
    subject_language: str                # "vi" hoặc "en"

    # === HTML Structure Signature ===
    html_structure_hash: str             # Hash của DOM tree structure (bỏ content)
    # Ví dụ: DOM tree Cake VPBank luôn có pattern:
    # div > table > tr > td["Thông tin tài khoản"]
    # div > table > tr > td["Thông tin giao dịch"]
    # → Hash này sẽ giống nhau cho mọi email từ Cake

    table_count: int                     # Số lượng <table> trong email
    has_logo: bool                       # Có logo image không
    logo_src_domain: str | None          # Domain của logo image ("imgcdn.be.com.vn")

    # === Content Patterns ===
    detected_amounts: list[str]          # Regex match các pattern tiền: "+10.000 đ"
    detected_dates: list[str]            # Regex match date patterns: "14/03/2026"
    detected_account_numbers: list[str]  # Regex match số tài khoản
    key_vietnamese_labels: list[str]     # ["Số tiền", "Ngày giờ giao dịch", ...]
    key_english_labels: list[str]        # ["Amount", "Transaction date", ...]

    # === Metadata ===
    email_size_bytes: int
    has_attachments: bool
    content_type: str                    # "text/html" hoặc "text/plain"
```

#### 3.6.3 Similarity Matching Algorithm

```python
class ParserSimilarityMatcher:
    """So sánh email fingerprint với các parser đã có"""

    def calculate_similarity(
        self,
        fingerprint: EmailFingerprint,
        parser: BaseBankParser
    ) -> SimilarityResult:

        scores = {}

        # 1. Sender domain match (40% weight)
        # Exact domain match → 1.0
        # Root domain match → 0.7 (ví dụ: noreply@cake.vn vs info@cake.vn)
        # Same parent org → 0.4 (ví dụ: cake.vn vs vpbank.com.vn)
        scores['sender'] = self._match_sender(fingerprint, parser)

        # 2. HTML structure similarity (30% weight)
        # So sánh DOM tree structure (bỏ qua content, chỉ so cấu trúc)
        # Dùng tree edit distance hoặc structural hash comparison
        # Cao → cùng template email, có thể là version mới
        scores['structure'] = self._match_structure(fingerprint, parser)

        # 3. Keyword/label overlap (20% weight)
        # So sánh các label trong email với labels mà parser hiện tại expect
        # "Số tiền", "Mã giao dịch", "Ngày giờ giao dịch"
        scores['keywords'] = self._match_keywords(fingerprint, parser)

        # 4. Data pattern match (10% weight)
        # Email có chứa pattern giống transaction email không?
        # (amounts, dates, account numbers)
        scores['patterns'] = self._match_data_patterns(fingerprint)

        weighted_score = (
            scores['sender'] * 0.4 +
            scores['structure'] * 0.3 +
            scores['keywords'] * 0.2 +
            scores['patterns'] * 0.1
        )

        return SimilarityResult(
            total_score=weighted_score,
            detail_scores=scores,
            matched_parser=parser.bank_name if weighted_score > 0.3 else None,
            suggestion=self._make_suggestion(weighted_score, scores, parser)
        )

    def _make_suggestion(self, score, detail, parser) -> ParserSuggestion:
        if score > 0.7:
            # Case A: Rất giống parser hiện tại → có thể là format mới
            return ParserSuggestion(
                type="UPDATE_EXISTING",
                message=f"Email này rất giống format của {parser.bank_name} "
                        f"nhưng có thay đổi cấu trúc. "
                        f"Có thể ngân hàng đã cập nhật template email.",
                confidence=score,
                existing_parser=parser.bank_name
            )
        elif score > 0.3:
            # Case B: Giống một phần → có thể là loại GD mới của cùng ngân hàng
            return ParserSuggestion(
                type="NEW_VARIANT",
                message=f"Email này có vẻ từ {parser.bank_name} "
                        f"nhưng là loại giao dịch mới chưa có parser. "
                        f"Tạo parser variant mới?",
                confidence=score,
                existing_parser=parser.bank_name
            )
        else:
            # Case C: Không giống ai → ngân hàng hoàn toàn mới
            return ParserSuggestion(
                type="NEW_PARSER",
                message=f"Email từ {fingerprint.sender_domain} "
                        f"không khớp với parser nào trong hệ thống. "
                        f"Tạo parser mới?",
                confidence=score,
                existing_parser=None
            )
```

#### 3.6.4 Parser Template Generator

Khi user đồng ý tạo parser mới, hệ thống tự sinh parser template từ email mẫu:

```python
class ParserTemplateGenerator:
    """Tự sinh parser code template từ email mẫu"""

    def generate_template(
        self,
        fingerprint: EmailFingerprint,
        sample_email_html: str,
        user_annotations: dict | None = None
    ) -> GeneratedParser:
        """
        Input:
        - fingerprint: Phân tích email
        - sample_email_html: HTML gốc
        - user_annotations: User chỉ ra đâu là amount, date, etc.
                           (từ UI, user highlight/click vào các field)

        Output:
        - GeneratedParser: Code Python parser + test file

        Strategy:
        1. Phân tích HTML structure → xác định cách navigate đến data
        2. Detect key-value table pattern (như Cake VPBank)
        3. Tạo extraction rules cho mỗi field
        4. Generate Python code
        5. Generate test file với email mẫu
        """
        pass

    def _detect_table_pattern(self, html: str) -> TablePattern:
        """
        Nhiều ngân hàng VN dùng pattern tương tự:
        <table>
            <tr>
                <td>Label</td>    ← Key
                <td>Value</td>    ← Value cần extract
            </tr>
        </table>

        Detect pattern này và map labels → fields
        """
        # Common VN bank email labels mapping:
        LABEL_FIELD_MAP = {
            # Vietnamese labels
            "Số tiền": "amount",
            "Ngày giờ giao dịch": "transaction_date",
            "Ngày giao dịch": "transaction_date",
            "Mã giao dịch": "transaction_id",
            "Nội dung": "description",
            "Nội dung giao dịch": "description",
            "Loại giao dịch": "transaction_type",
            "Tài khoản": "account_number",
            "Tài khoản nhận": "account_number",
            "Tài khoản chuyển": "counterparty_account",
            "Tên người chuyển": "counterparty_name",
            "Tên người nhận": "counterparty_name",
            "Phí giao dịch": "fee",
            "Số dư": "balance_after",
            "Số dư khả dụng": "balance_after",
            "Số thẻ": "card_number",

            # English labels (some banks use English)
            "Amount": "amount",
            "Transaction Date": "transaction_date",
            "Reference": "transaction_id",
            "Description": "description",
        }
        pass
```

#### 3.6.5 User Interaction Flow (UI)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARSER MANAGEMENT PAGE                        │
│                    (Settings → Email Parsers)                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Active Parsers                                    [+ Add]   ││
│  │                                                             ││
│  │  ✅ Cake/VPBank    v1.0   Matched: 156 emails   Last: 2h   ││
│  │  ✅ Vietcombank    v1.0   Matched: 89 emails    Last: 3h   ││
│  │  ✅ Techcombank CC v1.0   Matched: 45 emails    Last: 1d   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ⚠️ Unrecognized Emails (3)                    [Review All] ││
│  │                                                             ││
│  │  📧 From: alerts@mbbank.com.vn                              ││
│  │     Subject: "Thông báo biến động số dư"                    ││
│  │     Detected: Có thể là ngân hàng mới (MB Bank)            ││
│  │     [Preview] [Create Parser] [Ignore] [Mark Not Finance]  ││
│  │                                                             ││
│  │  📧 From: noreply@cake.vn                                   ││
│  │     Subject: "Thông báo giao dịch thẻ tín dụng"            ││
│  │     Detected: Cake/VPBank — loại GD mới (credit card)      ││
│  │     Similarity: 78% với parser Cake/VPBank hiện tại        ││
│  │     [Preview] [Update Parser] [New Variant] [Ignore]       ││
│  │                                                             ││
│  │  📧 From: noreply@cake.vn                                   ││
│  │     Subject: "Thông báo giao dịch"                          ││
│  │     Detected: Cake/VPBank — format thay đổi                ││
│  │     Similarity: 92% nhưng parse failed                     ││
│  │     [Preview] [Update Parser] [Ignore]                     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Parser Health Monitor                                       ││
│  │                                                             ││
│  │  Cake/VPBank:  Success rate 98% ████████████████████░ (30d) ││
│  │  Vietcombank:  Success rate 95% ███████████████████░░ (30d) ││
│  │  Techcombank:  Success rate 87% █████████████████░░░░ (30d) ││
│  │                ↑ Declining — có thể format đã thay đổi      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

#### 3.6.6 Parser Versioning

```python
"""
Mỗi parser có version. Khi update parser:
- Giữ version cũ trong history
- Test version mới với các email cũ để đảm bảo backward compatible
- Rollback nếu version mới parse sai email cũ
"""

class ParserVersion:
    parser_name: str          # "cake_vpbank"
    version: str              # "1.0", "1.1", "2.0"
    created_at: datetime
    change_reason: str        # "Initial", "Bank updated email template", ...
    sample_email_ids: list    # Gmail IDs dùng để test parser
    success_count: int        # Số email đã parse thành công
    fail_count: int           # Số email parse fail

# Version strategy:
# - Patch (1.0 → 1.1): Sửa nhỏ, thêm edge case handling
# - Minor (1.1 → 1.2): Thêm field mới nhưng backward compatible
# - Major (1.x → 2.0): Format email thay đổi hoàn toàn
```

#### 3.6.7 Database Tables cho Parser Management

```sql
-- =============================================
-- PARSER MANAGEMENT: Quản lý parser tự động
-- =============================================

CREATE TABLE parser_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parser_name     VARCHAR(100) NOT NULL UNIQUE,   -- "cake_vpbank"
    bank_display    VARCHAR(200) NOT NULL,           -- "Cake by VPBank"
    version         VARCHAR(20) NOT NULL,             -- "1.0.0"
    status          VARCHAR(20) DEFAULT 'active',     -- "active", "deprecated", "draft"

    -- Matching criteria
    sender_patterns JSONB NOT NULL,                   -- ["*@cake.vn", "*@be.com.vn"]
    subject_patterns JSONB NOT NULL,                  -- ["Thông báo giao dịch"]

    -- Parser metadata
    supported_types JSONB DEFAULT '[]',               -- ["incoming_transfer", "outgoing_transfer", "credit_card"]
    html_structure_hash VARCHAR(64),                   -- Để detect format changes

    -- Statistics
    total_parsed    INTEGER DEFAULT 0,
    total_failed    INTEGER DEFAULT 0,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    success_rate_30d FLOAT,                           -- Tự tính mỗi ngày

    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE parser_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parser_id       UUID NOT NULL REFERENCES parser_registry(id),
    version         VARCHAR(20) NOT NULL,
    change_reason   TEXT,
    -- Lưu extraction rules dưới dạng JSON (cho dynamic parsers)
    extraction_rules JSONB,
    -- Test samples
    sample_email_ids JSONB DEFAULT '[]',               -- Gmail message IDs dùng để test
    test_results    JSONB,                             -- Kết quả test với samples

    is_current      BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE(parser_id, version)
);

CREATE TABLE unrecognized_emails (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id        VARCHAR(200) NOT NULL UNIQUE,      -- Gmail message ID
    email_from      VARCHAR(200),
    email_subject   VARCHAR(500),
    email_date      TIMESTAMPTZ,
    fingerprint     JSONB NOT NULL,                     -- EmailFingerprint as JSON

    -- Similarity analysis
    closest_parser  VARCHAR(100),                       -- parser_name gần nhất
    similarity_score FLOAT,
    suggestion_type VARCHAR(30),                        -- "UPDATE_EXISTING", "NEW_VARIANT", "NEW_PARSER"
    suggestion_message TEXT,

    -- User action
    user_action     VARCHAR(30),                        -- "create_parser", "update_parser", "ignore", "not_finance"
    resolved_at     TIMESTAMPTZ,

    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Alert khi parser success rate giảm
CREATE TABLE parser_health_alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parser_id       UUID NOT NULL REFERENCES parser_registry(id),
    alert_type      VARCHAR(30),                        -- "success_rate_drop", "new_format_detected", "no_emails_7d"
    message         TEXT,
    current_rate    FLOAT,
    previous_rate   FLOAT,
    is_acknowledged BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### 3.6.8 Dynamic Parser (Phase nâng cao)

Ngoài hardcoded Python parsers, hệ thống có thể hỗ trợ **dynamic parsers** — parser được
define bằng JSON rules thay vì Python code. Cho phép tạo parser mới từ UI mà không cần deploy lại.

```json
{
  "parser_name": "mbbank",
  "bank_display": "MB Bank",
  "version": "1.0.0",
  "sender_patterns": ["*@mbbank.com.vn"],
  "subject_patterns": ["Thông báo biến động"],
  "extraction_method": "table_key_value",
  "field_mappings": [
    {"label_pattern": "Số tiền", "field": "amount", "transform": "parse_vnd_amount"},
    {"label_pattern": "Ngày.*giao dịch", "field": "transaction_date", "transform": "parse_vn_datetime"},
    {"label_pattern": "Mã giao dịch", "field": "transaction_id"},
    {"label_pattern": "Nội dung", "field": "description"},
    {"label_pattern": "Số dư", "field": "balance_after", "transform": "parse_vnd_amount"}
  ],
  "direction_detection": {
    "method": "amount_sign_or_color",
    "incoming_indicators": ["+", "#188126", "#00a651", "green"],
    "outgoing_indicators": ["-", "#dc3545", "#ff0000", "red"]
  }
}
```

Lợi ích:
- User tạo parser mới từ UI mà không cần biết code
- Hệ thống auto-generate JSON rules từ email mẫu (Step 3.6.4)
- Fallback sang hardcoded parser khi JSON rules không đủ phức tạp

---

## 4. Database Schema

### 4.1 Core Tables

```sql
-- =============================================
-- CORE: Nền tảng dữ liệu
-- =============================================

CREATE TABLE accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_name       VARCHAR(50) NOT NULL,       -- "cake_vpbank", "vietcombank"
    bank_display    VARCHAR(100) NOT NULL,       -- "Cake by VPBank"
    account_number  VARCHAR(50),                 -- Số tài khoản
    account_type    VARCHAR(20) NOT NULL,        -- "checking", "savings", "credit_card"
    currency        VARCHAR(3) DEFAULT 'VND',
    nickname        VARCHAR(100),                -- Tên gọi tắt: "Thẻ Cake chính"
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,       -- "Ăn uống"
    name_en         VARCHAR(100),                -- "Food & Dining" (for reports)
    parent_id       UUID REFERENCES categories(id),  -- Hierarchical categories
    icon            VARCHAR(50),                 -- Emoji hoặc icon name
    color           VARCHAR(7),                  -- Hex color cho charts
    budget_default  DECIMAL(15,2),               -- Ngân sách mặc định/tháng
    sort_order      INTEGER DEFAULT 0,
    is_system       BOOLEAN DEFAULT false,       -- Category mặc định, không xóa được
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Ví dụ categories:
-- Ăn uống → Ăn trưa, Ăn tối, Cafe, Đi chợ
-- Đi lại → Grab, Xăng, Gửi xe
-- Mua sắm → Quần áo, Điện tử, Gia dụng
-- Giải trí → Phim, Game, Streaming
-- Hóa đơn → Điện, Nước, Internet, Điện thoại
-- Subscription → Dev Tools, Cloud, Streaming, Productivity
-- Sức khỏe → Bảo hiểm, Khám bệnh, Thuốc
-- Giáo dục → Khóa học, Sách
-- Thu nhập → Lương, Freelance, Thưởng, Lãi tiết kiệm
-- Chuyển khoản nội bộ (hệ thống tự detect)
-- Chưa phân loại (mặc định cho giao dịch mới)


CREATE TABLE transactions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id          UUID NOT NULL REFERENCES accounts(id),
    category_id         UUID REFERENCES categories(id),

    -- Transaction data
    amount              DECIMAL(15,2) NOT NULL,     -- Luôn dương
    direction           VARCHAR(10) NOT NULL,        -- "incoming", "outgoing"
    currency            VARCHAR(3) DEFAULT 'VND',
    transaction_date    TIMESTAMPTZ NOT NULL,
    transaction_type    VARCHAR(30) NOT NULL,         -- "bank_transfer", "credit_card", ...

    -- Bank-provided info
    bank_transaction_id VARCHAR(100),                -- Mã GD từ ngân hàng
    description         TEXT,                         -- Nội dung giao dịch
    merchant_name       VARCHAR(200),
    fee                 DECIMAL(15,2) DEFAULT 0,
    balance_after       DECIMAL(15,2),

    -- Counterparty info
    counterparty_name   VARCHAR(200),
    counterparty_account VARCHAR(50),
    counterparty_bank   VARCHAR(100),

    -- Categorization
    category_source     VARCHAR(20) DEFAULT 'pending',  -- "rule", "user", "ai", "pending"
    is_reviewed         BOOLEAN DEFAULT false,

    -- Tags (flexible labeling system)
    tags                TEXT[] DEFAULT '{}',           -- PostgreSQL array: ['team-lunch', 'Q1-2026']

    -- Split bill reference
    split_bill_id       UUID,                          -- FK to split_bills (nullable)

    -- Metadata
    notes               TEXT,
    raw_email_id        VARCHAR(200),                  -- Gmail message ID
    raw_email_data      JSONB,                         -- Full parsed email data for debugging
    confidence_score    FLOAT DEFAULT 1.0,

    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    -- Constraints
    UNIQUE(account_id, bank_transaction_id),           -- Prevent duplicates
    CHECK (direction IN ('incoming', 'outgoing')),
    CHECK (amount > 0),
    CHECK (category_source IN ('rule', 'user', 'ai', 'pending'))
);

-- Indexes for common queries
CREATE INDEX idx_transactions_date ON transactions(transaction_date DESC);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_pending ON transactions(is_reviewed) WHERE is_reviewed = false;
CREATE INDEX idx_transactions_tags ON transactions USING GIN(tags);
CREATE INDEX idx_transactions_email ON transactions(raw_email_id);


CREATE TABLE categorization_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern         VARCHAR(500) NOT NULL,       -- Regex pattern
    match_field     VARCHAR(30) NOT NULL,         -- "merchant_name", "description", "counterparty_name"
    category_id     UUID NOT NULL REFERENCES categories(id),
    auto_tags       TEXT[] DEFAULT '{}',          -- Tags tự động gắn khi rule match
    priority        INTEGER DEFAULT 0,            -- Higher = checked first
    is_active       BOOLEAN DEFAULT true,
    match_count     INTEGER DEFAULT 0,            -- Số lần rule đã match (analytics)
    created_at      TIMESTAMPTZ DEFAULT now(),
    created_by      VARCHAR(20) DEFAULT 'user',   -- "user", "system", "learned"

    UNIQUE(pattern, match_field)
);

-- Ví dụ rules:
-- pattern: "GRAB|Grab"    match_field: "description"  → category: "Đi lại"
-- pattern: "SHOPEE|Shopee" match_field: "description" → category: "Mua sắm"
-- pattern: "SPOTIFY"       match_field: "merchant"    → category: "Subscription"  tags: ["streaming"]
-- pattern: "NGUYEN VAN A"  match_field: "counterparty_name" → tags: ["colleague"]
```

### 4.2 Social Tables (Split Bill)

```sql
-- =============================================
-- SOCIAL: Chia tiền & nợ cá nhân
-- =============================================

CREATE TABLE contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,       -- "Nguyễn Văn A"
    nickname        VARCHAR(100),                -- "Hùng"
    bank_accounts   JSONB DEFAULT '[]',          -- [{bank: "VCB", account: "123...", name: "NGUYEN VAN A"}]
    -- bank_accounts dùng để auto-match khi nhận chuyển khoản
    phone           VARCHAR(20),
    email           VARCHAR(200),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE split_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,       -- "Team Backend", "Bạn đại học"
    member_ids      UUID[] NOT NULL,             -- Array of contact IDs
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE split_bills (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID REFERENCES transactions(id),  -- Giao dịch gốc (bạn trả)
    group_id        UUID REFERENCES split_groups(id),
    description     TEXT,                        -- "Ăn trưa 14/03"
    total_amount    DECIMAL(15,2) NOT NULL,
    paid_by         VARCHAR(10) DEFAULT 'me',    -- "me" hoặc contact_id
    split_method    VARCHAR(20) DEFAULT 'equal',  -- "equal", "exact", "percentage"
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE split_participants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    split_bill_id   UUID NOT NULL REFERENCES split_bills(id),
    contact_id      UUID REFERENCES contacts(id), -- NULL = bản thân mình
    amount_owed     DECIMAL(15,2) NOT NULL,       -- Số tiền phần người này
    amount_paid     DECIMAL(15,2) DEFAULT 0,      -- Số tiền đã trả
    status          VARCHAR(20) DEFAULT 'pending', -- "pending", "partial", "settled"

    -- Auto-settlement tracking
    settlement_transaction_id UUID REFERENCES transactions(id),  -- GD chuyển khoản trả tiền
    settled_at      TIMESTAMPTZ,
    notes           TEXT
);

-- VIEW: Tổng nợ theo người (net balance)
-- Ví dụ: Hùng nợ mình 100k, nhưng mình cũng nợ Hùng 30k → net: Hùng nợ mình 70k
CREATE VIEW contact_balances AS
SELECT
    c.id as contact_id,
    c.name,
    c.nickname,
    COALESCE(SUM(
        CASE
            WHEN sb.paid_by = 'me' THEN sp.amount_owed - sp.amount_paid
            ELSE -(sp.amount_owed - sp.amount_paid)
        END
    ), 0) as net_balance
    -- Positive = họ nợ mình, Negative = mình nợ họ
FROM contacts c
LEFT JOIN split_participants sp ON sp.contact_id = c.id AND sp.status != 'settled'
LEFT JOIN split_bills sb ON sp.split_bill_id = sb.id
GROUP BY c.id, c.name, c.nickname;
```

### 4.3 Planning Tables

```sql
-- =============================================
-- PLANNING: Budget, Goals, Debts, Subscriptions
-- =============================================

CREATE TABLE budgets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id     UUID NOT NULL REFERENCES categories(id),
    amount          DECIMAL(15,2) NOT NULL,      -- Ngân sách/tháng
    period          VARCHAR(10) DEFAULT 'monthly', -- "monthly", "weekly", "yearly"
    start_date      DATE NOT NULL,
    end_date        DATE,                         -- NULL = vô thời hạn
    alert_threshold FLOAT DEFAULT 0.8,            -- Alert khi đạt 80%
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE goals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,       -- "Mua MacBook Pro"
    target_amount   DECIMAL(15,2) NOT NULL,      -- 50,000,000
    current_amount  DECIMAL(15,2) DEFAULT 0,     -- Tự tính hoặc manual update
    currency        VARCHAR(3) DEFAULT 'VND',
    deadline        DATE,
    priority        INTEGER DEFAULT 0,           -- 1 = cao nhất
    status          VARCHAR(20) DEFAULT 'active', -- "active", "completed", "cancelled"
    category        VARCHAR(50),                  -- "emergency_fund", "purchase", "travel", "investment"
    notes           TEXT,
    -- Linked savings account (optional)
    linked_account_id UUID REFERENCES accounts(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE debts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,       -- "Trả góp iPhone", "Vay ngân hàng mua nhà"
    debt_type       VARCHAR(20) NOT NULL,        -- "bank_loan", "installment", "personal", "credit_card"
    creditor        VARCHAR(200),                -- "VPBank", "Nguyễn Văn A"
    original_amount DECIMAL(15,2) NOT NULL,
    remaining_amount DECIMAL(15,2) NOT NULL,
    interest_rate   FLOAT DEFAULT 0,             -- % năm
    currency        VARCHAR(3) DEFAULT 'VND',
    start_date      DATE NOT NULL,
    due_date        DATE,                        -- Ngày trả hết
    payment_day     INTEGER,                     -- Ngày trả hàng tháng (1-31)
    monthly_payment DECIMAL(15,2),               -- Số tiền trả/tháng
    status          VARCHAR(20) DEFAULT 'active', -- "active", "paid_off", "defaulted"
    notes           TEXT,
    -- Auto-link to transaction khi trả nợ
    linked_category_id UUID REFERENCES categories(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name    VARCHAR(200) NOT NULL,       -- "Netflix", "GitHub Copilot", "AWS"
    provider        VARCHAR(200),                -- "Netflix Inc.", "GitHub"
    amount          DECIMAL(15,2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'VND',
    billing_cycle   VARCHAR(20) NOT NULL,        -- "monthly", "yearly", "quarterly"
    next_due_date   DATE,
    category_id     UUID REFERENCES categories(id),
    payment_method  VARCHAR(50),                 -- "VCB Credit Card", "Cake VPBank"

    -- Detection info
    detected_from   VARCHAR(20),                 -- "email_pattern", "transaction_pattern", "manual"
    detection_pattern VARCHAR(500),              -- Pattern dùng để detect

    -- Status
    status          VARCHAR(20) DEFAULT 'active', -- "active", "cancelled", "paused", "trial"
    started_date    DATE,
    cancelled_date  DATE,
    notes           TEXT,

    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
```

### 4.4 System Tables

```sql
-- =============================================
-- SYSTEM: Sync logs, errors, settings
-- =============================================

CREATE TABLE email_sync_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sync_start      TIMESTAMPTZ NOT NULL,
    sync_end        TIMESTAMPTZ,
    status          VARCHAR(20),                 -- "success", "partial", "failed"
    emails_fetched  INTEGER DEFAULT 0,
    emails_parsed   INTEGER DEFAULT 0,
    emails_failed   INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE parser_errors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_id        VARCHAR(200),
    email_from      VARCHAR(200),
    email_subject   VARCHAR(500),
    error_type      VARCHAR(50),                 -- "no_parser", "parse_failed", "validation_failed"
    error_message   TEXT,
    email_body_preview TEXT,                      -- First 500 chars for debugging
    is_resolved     BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_settings (
    key             VARCHAR(100) PRIMARY KEY,
    value           JSONB NOT NULL,
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Ví dụ settings:
-- "email_sync_interval_minutes": 15
-- "weekly_digest_day": "monday"
-- "weekly_digest_time": "08:00"
-- "default_currency": "VND"
-- "timezone": "Asia/Ho_Chi_Minh"
-- "budget_alert_threshold": 0.8
-- "auto_categorize_confidence_threshold": 0.8
```

---

## 5. Module Design — Chi tiết nghiệp vụ

### 5.1 Module: Auto Categorization (Phân loại tự động)

```
Giao dịch mới vào
       │
       ▼
┌──────────────────┐
│ Rule Engine       │ ← Check categorization_rules theo priority
│ (exact match)     │
└───────┬──────────┘
        │
   Match?─── YES ──▶ Gắn category, category_source = "rule"
        │
        NO
        │
        ▼
┌──────────────────┐
│ Pattern Learning  │ ← Check các giao dịch cũ có cùng merchant/counterparty
│ (fuzzy match)     │    đã được user tag → gợi ý category
└───────┬──────────┘
        │
   Match?─── YES ──▶ Gắn category, category_source = "learned"
        │                confidence_score = similarity score
        NO
        │
        ▼
┌──────────────────┐
│ Pending Queue     │ ← category_source = "pending"
│                   │    is_reviewed = false
│ Hiện trên         │
│ dashboard:        │
│ "X giao dịch      │
│  cần review"      │
└──────────────────┘

Khi user review & tag:
→ Hệ thống hỏi: "Tạo rule tự động cho giao dịch tương tự?"
→ Nếu đồng ý → Tạo categorization_rule mới, created_by = "learned"
```

### 5.2 Module: Split Bill Auto-Settlement

```
Hệ thống detect chuyển khoản đến (incoming transaction)
       │
       ▼
┌──────────────────────┐
│ Check counterparty    │ ← So sánh counterparty_name với contacts.bank_accounts
│ against contacts      │
└───────┬──────────────┘
        │
   Match contact?─── NO ──▶ Normal transaction, continue
        │
       YES
        │
        ▼
┌──────────────────────┐
│ Check outstanding     │ ← Tìm split_participants WHERE contact_id = matched
│ debts for this contact│   AND status = 'pending'
└───────┬──────────────┘
        │
   Has pending debt?─── NO ──▶ Normal transaction from known contact
        │
       YES
        │
        ▼
┌──────────────────────────────┐
│ Amount matches?               │
│                               │
│ Exact match → Auto-settle     │
│ Partial → Mark partial paid   │
│ Different → Ask user          │
└──────────────────────────────┘

Ví dụ:
- Hùng nợ bạn 100k từ bữa ăn trưa
- Email Cake: "Nhận +100.000đ từ NGUYEN VAN HUNG"
- Hệ thống match "NGUYEN VAN HUNG" → contact "Hùng"
- Hùng có outstanding debt 100k → exact match
- Tự động settle + notification: "Hùng đã trả 100k tiền ăn trưa 14/03"
```

### 5.3 Module: Subscription Detection

```
Chiến lược 1: Email pattern detection
- Scan email từ known subscription services
- Detect invoice/receipt emails: "Your invoice", "Payment receipt", "Hóa đơn"
- Extract: service name, amount, billing date

Chiến lược 2: Transaction pattern detection (chạy weekly)
- Query: Tìm giao dịch recurring cùng merchant + ~cùng amount
- Rule: ≥ 2 lần trong 3 tháng, same merchant, amount ±10%
- Kết quả → Gợi ý: "Phát hiện subscription mới: SPOTIFY 59,000đ/tháng"

Chiến lược 3: Manual add
- User tự thêm subscription (cho các service trả bằng tiền mặt hoặc app khác)
```

### 5.4 Module: Smart Notification System

```
┌─────────────────────────────────────────────────────────┐
│ NOTIFICATION TYPES & TRIGGERS                           │
│                                                         │
│ 1. DAILY (nếu có)                                       │
│    - Giao dịch chưa phân loại: "5 giao dịch cần review"│
│    - Split bill nhắc nợ (sau 3 ngày chưa trả)          │
│                                                         │
│ 2. WEEKLY (Monday morning)                              │
│    - Weekly digest: tổng thu/chi, top categories        │
│    - So sánh với tuần trước                             │
│    - Budget warnings                                    │
│                                                         │
│ 3. EVENT-BASED                                          │
│    - Budget vượt ngưỡng (80%, 100%)                     │
│    - Subscription sắp renewal (3 ngày trước)            │
│    - Debt payment due (3 ngày trước)                    │
│    - Giao dịch bất thường (amount > 2x average)        │
│    - Split bill auto-settled                            │
│    - Goal milestone reached (25%, 50%, 75%, 100%)       │
│                                                         │
│ 4. MONTHLY                                              │
│    - Monthly report: full breakdown                     │
│    - Net worth update                                   │
│    - Subscription cost summary                          │
│    - Goal progress review                               │
└─────────────────────────────────────────────────────────┘
```

---

## 6. API Design (High-Level)

### 6.1 REST API Endpoints

```
# === Transactions ===
GET    /api/transactions              # List (with filters, pagination)
GET    /api/transactions/:id          # Detail
PUT    /api/transactions/:id          # Update (category, tags, notes)
GET    /api/transactions/pending      # Chưa phân loại
POST   /api/transactions/manual       # Nhập tay (tiền mặt)
POST   /api/transactions/:id/categorize  # Phân loại + optional tạo rule

# === Categories ===
GET    /api/categories                # List (tree structure)
POST   /api/categories                # Create
PUT    /api/categories/:id            # Update

# === Categorization Rules ===
GET    /api/rules                     # List
POST   /api/rules                     # Create
PUT    /api/rules/:id                 # Update
DELETE /api/rules/:id                 # Delete

# === Split Bills ===
GET    /api/splits                    # List
POST   /api/splits                    # Create new split
GET    /api/splits/:id                # Detail with participants
PUT    /api/splits/:id/settle         # Manual settle

# === Contacts ===
GET    /api/contacts                  # List
POST   /api/contacts                  # Create
GET    /api/contacts/:id/balance      # Net balance with this person

# === Subscriptions ===
GET    /api/subscriptions             # List (active, cancelled)
POST   /api/subscriptions             # Manual add
PUT    /api/subscriptions/:id         # Update status

# === Budgets ===
GET    /api/budgets                   # List with current spending
POST   /api/budgets                   # Create
PUT    /api/budgets/:id               # Update

# === Goals ===
GET    /api/goals                     # List with progress
POST   /api/goals                     # Create
PUT    /api/goals/:id                 # Update

# === Debts ===
GET    /api/debts                     # List (active, paid_off)
POST   /api/debts                     # Create
PUT    /api/debts/:id                 # Update / record payment

# === Reports ===
GET    /api/reports/summary           # Dashboard summary
GET    /api/reports/monthly/:year/:month   # Monthly report
GET    /api/reports/trends            # Spending trends
GET    /api/reports/net-worth         # Net worth over time
GET    /api/reports/category-breakdown # Spending by category

# === Accounts ===
GET    /api/accounts                  # List
POST   /api/accounts                  # Add account

# === Parser Management ===
GET    /api/parsers                   # List registered parsers + stats
GET    /api/parsers/:name/health      # Health metrics for a parser
GET    /api/parsers/unrecognized      # List unrecognized emails
POST   /api/parsers/unrecognized/:id/create   # Create new parser from sample
POST   /api/parsers/unrecognized/:id/update   # Update existing parser
POST   /api/parsers/unrecognized/:id/ignore   # Mark as ignored
POST   /api/parsers/dynamic           # Create/update dynamic (JSON) parser
GET    /api/parsers/:name/versions    # Version history
POST   /api/parsers/:name/test        # Test parser with sample email

# === System ===
POST   /api/sync/trigger              # Manual trigger email sync
GET    /api/sync/status               # Last sync info
GET    /api/settings                  # User settings
PUT    /api/settings                  # Update settings
```

---

## 7. Frontend Pages

```
┌─────────────────────────────────────────────────┐
│                    SIDEBAR                       │
│                                                  │
│  📊 Dashboard (tổng quan)                        │
│  💳 Transactions (danh sách giao dịch)           │
│     └─ ⚠️ Pending Review (badge count)          │
│  🍽️ Split Bills (chia tiền)                     │
│     └─ 👥 Contacts                              │
│  📱 Subscriptions                                │
│  💰 Budget                                       │
│  🎯 Goals                                        │
│  📉 Debts                                        │
│  📈 Reports                                      │
│     └─ Monthly                                   │
│     └─ Trends                                    │
│     └─ Net Worth                                 │
│  ⚙️ Settings                                    │
│     └─ Accounts                                  │
│     └─ Categories                                │
│     └─ Rules                                     │
│     └─ Email Parsers (+ ⚠️ unrecognized count)  │
│     └─ Email Sync                                │
│     └─ Backup & Security                         │
└─────────────────────────────────────────────────┘
```

---

## 8. Project Structure

```
personal-finance-tracking/
├── README.md
├── SYSTEM_DESIGN.md                    # This document
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── pyproject.toml                  # Python dependencies (Poetry/uv)
│   ├── alembic/                        # Database migrations
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app entry point
│   │   ├── config.py                   # Settings (env-based)
│   │   ├── database.py                 # DB connection & session
│   │   │
│   │   ├── models/                     # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── transaction.py
│   │   │   ├── account.py
│   │   │   ├── category.py
│   │   │   ├── rule.py
│   │   │   ├── split.py
│   │   │   ├── contact.py
│   │   │   ├── subscription.py
│   │   │   ├── budget.py
│   │   │   ├── goal.py
│   │   │   └── debt.py
│   │   │
│   │   ├── schemas/                    # Pydantic schemas (API request/response)
│   │   │   ├── __init__.py
│   │   │   ├── transaction.py
│   │   │   └── ...
│   │   │
│   │   ├── api/                        # API routes
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # Main router
│   │   │   ├── transactions.py
│   │   │   ├── splits.py
│   │   │   ├── subscriptions.py
│   │   │   ├── budgets.py
│   │   │   ├── goals.py
│   │   │   ├── debts.py
│   │   │   ├── reports.py
│   │   │   └── settings.py
│   │   │
│   │   ├── parsers/                    # Email parser engine
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # BaseBankParser ABC
│   │   │   ├── registry.py            # Parser registration & lookup
│   │   │   ├── fingerprint.py         # Email fingerprinting
│   │   │   ├── similarity.py          # Similarity matching engine
│   │   │   ├── auto_discovery.py      # Auto-discovery orchestrator
│   │   │   ├── template_generator.py  # Generate parser from samples
│   │   │   ├── dynamic_parser.py      # JSON-based dynamic parser runtime
│   │   │   ├── banks/                 # Hardcoded bank parsers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cake_vpbank.py
│   │   │   │   ├── vietcombank.py
│   │   │   │   ├── techcombank.py
│   │   │   │   └── ...
│   │   │   └── dynamic/               # JSON parser definitions (auto-generated)
│   │   │       └── *.json
│   │   │
│   │   ├── services/                   # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── gmail_service.py       # Gmail API wrapper
│   │   │   ├── sync_service.py        # Email sync orchestrator
│   │   │   ├── categorizer.py         # Auto-categorization engine
│   │   │   ├── split_service.py       # Split bill logic
│   │   │   ├── subscription_detector.py
│   │   │   ├── notification_service.py
│   │   │   └── report_service.py
│   │   │
│   │   ├── tasks/                      # Scheduled tasks
│   │   │   ├── __init__.py
│   │   │   ├── email_sync.py          # Periodic email sync
│   │   │   ├── subscription_check.py  # Weekly subscription detection
│   │   │   └── digest.py             # Weekly/monthly digest
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── vn_currency.py         # VND formatting helpers
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_parsers/
│       │   ├── test_cake_vpbank.py
│       │   ├── fixtures/              # Sample email HTML files
│       │   │   ├── cake_incoming.html
│       │   │   ├── cake_outgoing.html
│       │   │   └── ...
│       │   └── ...
│       ├── test_services/
│       └── test_api/
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                       # API client (axios/fetch)
│   │   ├── components/                # Shared components
│   │   │   ├── Layout/
│   │   │   ├── Charts/
│   │   │   └── Forms/
│   │   ├── pages/
│   │   │   ├── Dashboard/
│   │   │   ├── Transactions/
│   │   │   ├── SplitBills/
│   │   │   ├── Subscriptions/
│   │   │   ├── Budget/
│   │   │   ├── Goals/
│   │   │   ├── Debts/
│   │   │   ├── Reports/
│   │   │   └── Settings/
│   │   ├── parsers/                    # Client-side email parsers (TypeScript)
│   │   │   ├── base.ts               # Base parser interface
│   │   │   ├── registry.ts           # Parser registry
│   │   │   ├── dynamic-parser.ts     # JSON-based dynamic parser runtime
│   │   │   ├── banks/
│   │   │   │   ├── cake-vpbank.ts
│   │   │   │   └── ...
│   │   │   └── gmail-client.ts       # Client-side Gmail API wrapper
│   │   ├── hooks/                     # Custom React hooks
│   │   ├── store/                     # State management (Zustand/Context)
│   │   ├── types/                     # TypeScript types
│   │   └── utils/
│   └── public/
│
└── docs/
    ├── email-samples/                  # Mẫu email từ các ngân hàng
    │   ├── cake_vpbank/
    │   │   ├── incoming_transfer.html
    │   │   ├── outgoing_transfer.html
    │   │   └── README.md              # Format documentation
    │   ├── vietcombank/
    │   ├── techcombank/
    │   └── ...
    └── api.md                         # API documentation
```

---

## 9. Roadmap & Phasing

### Phase 1 — Foundation (Tuần 1-2)

**Mục tiêu:** Có thể sync email từ Cake/VPBank và hiển thị giao dịch trên web.

- [ ] Setup project structure (backend + frontend)
- [ ] Docker Compose (PostgreSQL + backend + frontend)
- [ ] Database schema & migrations (core tables only)
- [ ] Gmail API OAuth2 setup
- [ ] Cake/VPBank email parser (dựa trên email mẫu)
- [ ] Email sync service (manual trigger)
- [ ] Basic transaction list UI
- [ ] Basic categorization rules

### Phase 2 — Smart Categorization (Tuần 3)

- [ ] Rule engine với priority
- [ ] Pending review queue + UI
- [ ] "Learn from user" — tạo rule từ manual categorization
- [ ] Thêm parsers cho VCB, TCB (cần email mẫu)
- [ ] Scheduled email sync (APScheduler)

### Phase 3 — Split Bills (Tuần 4)

- [ ] Contacts management
- [ ] Split bill creation UI
- [ ] Auto-settlement detection
- [ ] Net balance calculation
- [ ] Split bill history

### Phase 4 — Planning (Tuần 5-6)

- [ ] Budget management (per category)
- [ ] Budget alerts
- [ ] Goals tracking
- [ ] Debt tracker
- [ ] Subscription detection & management

### Phase 5 — Insights (Tuần 7-8)

- [ ] Dashboard with charts
- [ ] Monthly reports
- [ ] Spending trends
- [ ] Weekly email digest
- [ ] Net worth tracker

### Phase 6 — Polish & Advanced (Ongoing)

- [ ] Mobile-responsive UI
- [ ] AI-powered categorization
- [ ] Cash flow forecasting
- [ ] Multi-currency support
- [ ] CSV import (fallback)
- [ ] Tag analytics
- [ ] Tax helper

---

## 10. Câu hỏi mở cần làm rõ trước khi build

### 10.1 Email Samples cần thu thập

Để viết parser chính xác, cần email mẫu cho các trường hợp sau:

**Cake by VPBank:**
- [x] Nhận chuyển khoản (incoming transfer) ← Đã có
- [ ] Chuyển khoản đi (outgoing transfer)
- [ ] Thanh toán QR
- [ ] Nạp tiền / rút tiền
- [ ] Nhận lãi tiết kiệm

**Các ngân hàng khác:**
- [ ] VCB — Email thông báo giao dịch credit card
- [ ] TCB — Email thông báo giao dịch credit card
- [ ] Bất kỳ ngân hàng nào bạn dùng cho credit card

### 10.2 Quyết định đã xác nhận

1. **Hosting:** ✅ Docker trên VPS (Docker Compose)
2. **Multi-user:** ✅ Thiết kế multi-tenant ready, nhưng ban đầu single user
3. **Mobile:** ✅ Responsive web only (không cần mobile app riêng)
4. **Backup strategy:** ✅ Cần backup tự động (xem Section 11)

---

## 11. Deployment & Infrastructure

### 11.1 Docker Compose Architecture

```yaml
# docker-compose.yml
services:
  # === Database ===
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups              # Mount backup directory
    environment:
      POSTGRES_DB: finance_tracker
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
    restart: unless-stopped

  # === Cache & Task Queue ===
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # === Backend API ===
  backend:
    build: ./backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres/finance_tracker
      REDIS_URL: redis://redis:6379
      GMAIL_CREDENTIALS: /app/secrets/gmail_credentials.json
    volumes:
      - ./secrets:/app/secrets:ro       # Gmail OAuth credentials
    ports:
      - "8000:8000"
    restart: unless-stopped

  # === Frontend ===
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  # === Reverse Proxy (production) ===
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro   # SSL certificates
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

  # === Backup Service ===
  backup:
    image: postgres:16-alpine
    depends_on:
      - postgres
    volumes:
      - ./backups:/backups
    entrypoint: /bin/sh
    command: -c "while true; do sleep 86400; done"
    # Backup chạy qua cron job trên host hoặc scheduled task
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 11.2 Multi-Tenant Architecture (Future-Ready)

Thiết kế ban đầu cho single user nhưng schema hỗ trợ multi-tenant:

```
Strategy: Schema-based isolation (mỗi user 1 schema trong cùng database)

Lý do chọn schema-based thay vì:
- Row-level (thêm user_id vào mọi table): Dễ leak data nếu quên WHERE
- Database-per-user: Quá nặng cho VPS nhỏ
- Schema-based: Isolation tốt, dễ backup/restore từng user,
  dễ migrate từ single-user

Hiện tại: Dùng schema "public" cho user duy nhất
Tương lai: Tạo schema mới cho mỗi user, ví dụ "user_abc123"
```

```sql
-- Thêm bảng users (tạo sẵn nhưng chưa enforce)
CREATE TABLE public.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(200) NOT NULL UNIQUE,
    display_name    VARCHAR(200),
    schema_name     VARCHAR(100) UNIQUE,             -- "public" cho user đầu tiên
    gmail_token     JSONB,                           -- Encrypted OAuth2 token
    settings        JSONB DEFAULT '{}',
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

-- Ban đầu: 1 record duy nhất
INSERT INTO public.users (email, display_name, schema_name)
VALUES ('hatnemiot@gmail.com', 'Nguyễn Kim Đạt', 'public');
```

### 11.3 Backup Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                     BACKUP STRATEGY                              │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Layer 1: Automated Daily Backup                           │  │
│  │                                                           │  │
│  │ Schedule: Mỗi ngày lúc 3:00 AM (traffic thấp)           │  │
│  │ Method: pg_dump --format=custom (compressed)              │  │
│  │ Retention: Giữ 30 ngày gần nhất                          │  │
│  │ Location: /backups/ trên VPS                              │  │
│  │                                                           │  │
│  │ Script:                                                   │  │
│  │ pg_dump -U $DB_USER -Fc finance_tracker \                │  │
│  │   > /backups/daily/finance_$(date +%Y%m%d).dump          │  │
│  │                                                           │  │
│  │ # Xóa backup cũ hơn 30 ngày                             │  │
│  │ find /backups/daily -name "*.dump" -mtime +30 -delete    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Layer 2: Weekly Offsite Backup                            │  │
│  │                                                           │  │
│  │ Schedule: Mỗi Chủ nhật lúc 4:00 AM                      │  │
│  │ Method: Upload backup lên cloud storage                   │  │
│  │ Options (chọn 1):                                         │  │
│  │   a) Google Drive (đã có Gmail, dùng luôn GDrive API)    │  │
│  │   b) S3-compatible (Backblaze B2 — rẻ: $5/TB/month)     │  │
│  │   c) rsync tới máy cá nhân                               │  │
│  │ Retention: Giữ 12 bản gần nhất (3 tháng)                │  │
│  │ Encryption: Encrypt bằng gpg trước khi upload            │  │
│  │                                                           │  │
│  │ gpg --symmetric --cipher-algo AES256 \                   │  │
│  │   finance_$(date +%Y%m%d).dump                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Layer 3: Pre-Migration Backup                             │  │
│  │                                                           │  │
│  │ Trigger: Tự động trước mỗi lần chạy database migration   │  │
│  │ Location: /backups/pre-migration/                         │  │
│  │ Retention: Giữ 10 bản gần nhất                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Layer 4: Email Data Preservation                          │  │
│  │                                                           │  │
│  │ Gmail emails là bản gốc → luôn có thể re-parse           │  │
│  │ Hệ thống lưu raw_email_data trong transactions           │  │
│  │ → Nếu mất DB, chỉ cần re-sync từ Gmail                  │  │
│  │ → Gmail là "source of truth" tự nhiên                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Recovery Plan:                                                  │
│  1. Restore từ daily backup:                                    │
│     pg_restore -U $DB_USER -d finance_tracker backup.dump       │
│  2. Nếu backup cũ: Restore + re-sync email từ ngày backup     │
│  3. Worst case (mất tất cả): Re-sync toàn bộ từ Gmail          │
└─────────────────────────────────────────────────────────────────┘
```

### 11.4 Security Considerations

```
┌─────────────────────────────────────────────────────────────────┐
│                     SECURITY LAYERS                              │
│                                                                  │
│  1. NETWORK                                                      │
│     - VPS firewall: chỉ mở port 80/443                         │
│     - Nginx reverse proxy + SSL (Let's Encrypt)                 │
│     - Không expose PostgreSQL/Redis port ra ngoài               │
│                                                                  │
│  2. AUTHENTICATION (ban đầu đơn giản, nâng cấp khi multi-user) │
│     - Phase 1: HTTP Basic Auth hoặc single JWT token            │
│     - Phase multi-user: OAuth2 (Google login — đã có Gmail)     │
│                                                                  │
│  3. DATA ENCRYPTION                                              │
│     - SSL/TLS cho mọi connection                                │
│     - Gmail OAuth tokens encrypted at rest (Fernet/AES)         │
│     - Backup files encrypted (GPG)                               │
│     - PostgreSQL: full-disk encryption trên VPS                 │
│                                                                  │
│  4. GMAIL API                                                    │
│     - Read-only scope: gmail.readonly                           │
│     - Token refresh tự động                                     │
│     - Token revocation UI trong Settings                         │
│                                                                  │
│  5. SECRETS MANAGEMENT                                           │
│     - .env file cho sensitive config (not committed)             │
│     - Docker secrets cho production                              │
│     - Gmail credentials mounted as read-only volume              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. Privacy & Multi-User Data Ingestion (Hybrid Approach)

### 12.1 Vấn đề cốt lõi

Gmail API scope `gmail.readonly` cho phép đọc **tất cả** email — dù app chỉ thực tế đọc
email finance. Với bản thân (self-hosted) thì không vấn đề, nhưng khi mở cho user khác:

- User thấy "App này muốn đọc tất cả email" → từ chối
- Gmail readonly là "sensitive scope" → Google yêu cầu security audit cho app >100 users
- Server lưu OAuth token → nếu bị hack, attacker có thể đọc toàn bộ email user

### 12.2 Giải pháp: Hybrid Data Ingestion — User tự chọn

Hệ thống cung cấp **4 phương thức** kết nối email, user tự chọn dựa trên mức trust:

```
┌─────────────────────────────────────────────────────────────────────┐
│           DATA INGESTION OPTIONS (User tự chọn khi onboard)        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Option A: Server-Side Gmail Sync                            │   │
│  │ Trust level: ████████░░ (High — user trust server)          │   │
│  │                                                             │   │
│  │ Cách hoạt động:                                             │   │
│  │ User ──OAuth──▶ Server gets gmail.readonly token            │   │
│  │                 Server sync email background mỗi 15min      │   │
│  │                                                             │   │
│  │ Ưu điểm: Auto sync background, không cần mở app            │   │
│  │ Nhược: User phải trust server với full email access         │   │
│  │ Dùng cho: Admin/Owner (bạn), hoặc self-hosted instances     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Option B: Client-Side Processing (Recommend cho multi-user) │   │
│  │ Trust level: ██████████ (Maximum privacy)                   │   │
│  │                                                             │   │
│  │ Cách hoạt động:                                             │   │
│  │ User ──OAuth──▶ Browser gets token (stays in browser)       │   │
│  │                 Browser calls Gmail API directly             │   │
│  │                 Browser parses email locally                 │   │
│  │                 Browser sends ONLY parsed transaction data   │   │
│  │                 ──POST {amount, date, merchant}──▶ Server   │   │
│  │                                                             │   │
│  │ Server NEVER sees:                                          │   │
│  │ ✗ Email content    ✗ OAuth token    ✗ Email metadata        │   │
│  │ Server ONLY sees:                                           │   │
│  │ ✓ Structured transaction data (amount, date, merchant, etc.)│   │
│  │                                                             │   │
│  │ Ưu điểm: Privacy tối đa, không cần Google security audit   │   │
│  │ Nhược: Phải mở web app để sync (không auto background)     │   │
│  │ Dùng cho: Multi-user production                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Option C: Google Apps Script (Self-hosted processing)       │   │
│  │ Trust level: █████████░ (Very high)                         │   │
│  │                                                             │   │
│  │ Cách hoạt động:                                             │   │
│  │ User cài Google Apps Script vào Gmail của họ                │   │
│  │ Script chạy trong Google account (không qua server)         │   │
│  │ Script filter + parse email → POST data về server           │   │
│  │                                                             │   │
│  │ Ưu điểm: Auto sync (script chạy trigger-based),            │   │
│  │          server không access Gmail, user có thể đọc script  │   │
│  │ Nhược: Setup phức tạp hơn, Apps Script có limits            │   │
│  │ Dùng cho: Technical users muốn auto sync + privacy          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Option D: Manual Import (Zero trust required)               │   │
│  │ Trust level: ██████████ (No email access at all)            │   │
│  │                                                             │   │
│  │ Cách hoạt động:                                             │   │
│  │ User tải sao kê CSV/Excel từ internet banking               │   │
│  │ Upload lên web app → hệ thống parse                         │   │
│  │                                                             │   │
│  │ Ưu điểm: Không kết nối email, đơn giản                     │   │
│  │ Nhược: Manual effort mỗi tháng                              │   │
│  │ Dùng cho: User không muốn kết nối email                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.3 Onboarding Flow cho User mới

```
User đăng ký (Google OAuth login)
    │
    ▼
Welcome screen: "Chọn cách kết nối dữ liệu tài chính"
    │
    ├─── "Kết nối Gmail (xử lý trên trình duyệt)" [Recommended]
    │     → OAuth consent (trong browser)
    │     → Hiển thị rõ: "Email được xử lý trên thiết bị của bạn.
    │       Server chỉ nhận: số tiền, ngày, tên merchant, ngân hàng.
    │       Server KHÔNG nhận nội dung email."
    │     → Hướng dẫn tạo Gmail label "Finance"
    │     → Test sync: hiện 5 giao dịch gần nhất để verify
    │
    ├─── "Dùng Gmail Script (tự động, privacy cao)"
    │     → Step-by-step wizard cài Google Apps Script
    │     → Cung cấp script code (user có thể đọc/audit)
    │     → Script tự push data về server
    │
    ├─── "Import sao kê ngân hàng"
    │     → Upload CSV/Excel
    │     → Hướng dẫn tải sao kê từ internet banking
    │
    └─── "Kết nối Gmail (server sync)" [Chỉ hiện cho self-hosted]
          → Full OAuth consent
          → Cảnh báo: "Server sẽ có quyền đọc email của bạn"
          → Chỉ khả dụng khi user tự host instance riêng
```

### 12.4 Client-Side Processing — Chi tiết kỹ thuật

```
┌─────────────────────────────────────────────────────────────────┐
│                    BROWSER (Client-side)                         │
│                                                                  │
│  ┌──────────────┐     ┌─────────────┐     ┌────────────────┐   │
│  │ OAuth Token  │────▶│ Gmail API   │────▶│ Email Content  │   │
│  │ (stored in   │     │ (direct     │     │ (stays in      │   │
│  │  browser     │     │  from       │     │  browser       │   │
│  │  localStorage│     │  browser)   │     │  memory)       │   │
│  │  encrypted)  │     └─────────────┘     └───────┬────────┘   │
│  └──────────────┘                                 │             │
│                                                   ▼             │
│                                            ┌──────────────┐    │
│                                            │ Parser Engine │    │
│                                            │ (TypeScript/  │    │
│                                            │  WASM)        │    │
│                                            └───────┬──────┘    │
│                                                    │            │
│                                   Chỉ structured   │            │
│                                   transaction data  │            │
│                                                    ▼            │
│  Data gửi lên server:                                           │
│  {                                                               │
│    "bank": "cake_vpbank",                                       │
│    "amount": 10000,                                              │
│    "direction": "incoming",                                      │
│    "date": "2026-03-14T22:28:37+07:00",                         │
│    "transaction_id": "402297749",                                │
│    "description": "NGUYEN KIM DAT transfer",                    │
│    "account_number": "039661****"  ← masked                     │
│  }                                                               │
│                                                                  │
│  KHÔNG gửi: email HTML, email subject, sender, attachments      │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   │  POST /api/transactions/ingest
                   │  (chỉ structured data)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SERVER                                        │
│                                                                  │
│  Nhận transaction data → lưu DB → categorize → done             │
│  Server KHÔNG CÓ: email content, OAuth token, raw email data    │
└─────────────────────────────────────────────────────────────────┘
```

**Parsers cho client-side:**

Vì parser hiện chạy trên Python (server), cần giải quyết cho client-side:

```
Approach 1: TypeScript parsers (Recommended)
- Viết parser bằng TypeScript, chạy trực tiếp trong browser
- Share parser logic giữa server (dùng cho Option A) và client (Option B)
  bằng cách maintain 2 bản: Python + TypeScript
- Dynamic parsers (JSON-based) chạy được trên cả 2 môi trường

Approach 2: Python → WASM (Pyodide)
- Dùng Pyodide để chạy Python parsers trong browser
- Ưu điểm: code 1 lần, chạy mọi nơi
- Nhược: Pyodide bundle nặng (~20MB), load chậm

→ Đề xuất: Approach 1 cho production. JSON-based dynamic parsers
  là bridge tự nhiên — cùng JSON spec chạy được trên Python lẫn TypeScript.
```

### 12.5 API endpoint cho Client-Side Ingestion

```
# Client-side processed data submission
POST /api/transactions/ingest
Content-Type: application/json
Authorization: Bearer <user_jwt>

Body:
{
  "transactions": [
    {
      "bank_name": "cake_vpbank",
      "amount": 10000,
      "direction": "incoming",
      "currency": "VND",
      "transaction_date": "2026-03-14T22:28:37+07:00",
      "transaction_id": "402297749",
      "transaction_type": "bank_transfer",
      "description": "NGUYEN KIM DAT transfer",
      "account_number": "039661****",
      "counterparty_name": null,
      "fee": 0
    }
  ],
  "sync_metadata": {
    "method": "client_side",         // "server_sync", "client_side", "apps_script", "csv_import"
    "client_parser_version": "1.2.0",
    "emails_processed": 3,
    "emails_skipped": 0,
    "sync_timestamp": "2026-03-15T10:00:00+07:00"
  }
}

Response:
{
  "imported": 3,
  "duplicates_skipped": 0,
  "needs_review": 1,              // Giao dịch chưa auto-categorize được
  "new_subscriptions_detected": 0
}
```

### 12.6 Privacy Transparency — Hiển thị cho user

Dashboard Settings hiển thị rõ ràng:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚙️ Data & Privacy                                              │
│                                                                  │
│  Connection method: Client-Side Processing ✅                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ What server stores:                                       │  │
│  │ ✓ Transaction amounts, dates, merchants                   │  │
│  │ ✓ Category assignments and tags                           │  │
│  │ ✓ Your budgets, goals, and settings                       │  │
│  │                                                           │  │
│  │ What server NEVER receives:                               │  │
│  │ ✗ Email content or metadata                               │  │
│  │ ✗ Gmail access token                                      │  │
│  │ ✗ Non-financial emails                                    │  │
│  │ ✗ Full account numbers (masked to last 4 digits)          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [Export My Data]  [Delete My Account]  [Change Connection]      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 13. Updated Roadmap (với Parser Auto-Discovery)

### Phase 1 — Foundation (Tuần 1-2)

**Mục tiêu:** Sync email Cake/VPBank, hiển thị giao dịch, Docker deployment.

- [ ] Setup project structure (backend + frontend)
- [ ] Docker Compose (PostgreSQL + Redis + backend + frontend + nginx)
- [ ] Database schema & migrations (core + parser management tables)
- [ ] Gmail API OAuth2 setup
- [ ] Email fingerprinting system
- [ ] Cake/VPBank parser (incoming transfer — từ email mẫu)
- [ ] Email sync service (manual trigger + scheduled)
- [ ] Basic transaction list UI
- [ ] Basic authentication (single user)

### Phase 2 — Smart Categorization + Parser Discovery (Tuần 3-4)

- [ ] Rule engine với priority
- [ ] Pending review queue + UI
- [ ] "Learn from user" — tạo rule từ manual categorization
- [ ] **Parser Auto-Discovery Engine:**
  - [ ] Email fingerprinting
  - [ ] Similarity matching
  - [ ] Unrecognized email queue + UI
  - [ ] Parser health monitoring
- [ ] **Parser Template Generator** (JSON-based dynamic parsers)
- [ ] Parser management UI (Settings page)
- [ ] Thêm parsers qua email mẫu bạn cung cấp thêm

### Phase 3 — Split Bills (Tuần 5)

- [ ] Contacts management
- [ ] Split bill creation UI
- [ ] Auto-settlement detection
- [ ] Net balance calculation
- [ ] Split bill reminders

### Phase 4 — Planning (Tuần 6-7)

- [ ] Budget management (per category)
- [ ] Budget alerts
- [ ] Goals tracking
- [ ] Debt tracker
- [ ] Subscription detection & management

### Phase 5 — Insights (Tuần 8-9)

- [ ] Dashboard with charts
- [ ] Monthly reports
- [ ] Spending trends
- [ ] Weekly email digest
- [ ] Net worth tracker

### Phase 6 — Production Hardening (Tuần 10)

- [ ] Backup automation (daily + weekly offsite)
- [ ] SSL/TLS setup (Let's Encrypt)
- [ ] Monitoring & alerting
- [ ] Error tracking
- [ ] Performance optimization

### Phase 7 — Advanced & Multi-User (Future)

- [ ] Multi-tenant support
- [ ] OAuth2 authentication (Google login)
- [ ] AI-powered categorization
- [ ] Cash flow forecasting
- [ ] Multi-currency support
- [ ] CSV import (fallback)
- [ ] Tax helper

---

> **Next steps:** Sau khi review document này, bạn confirm hướng đi và cung cấp thêm email mẫu (outgoing transfer, credit card), mình sẽ bắt đầu build Phase 1.
