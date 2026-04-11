# NIB Membership Payments — API Spec

---

## Data Model

### `membership_periods`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| membership_id | UUID FK → membership.id | Billing at group level |
| period_start | DATE | |
| period_end | DATE | |
| status | ENUM | `active`, `expired` |
| created_at | TIMESTAMP | |

### `invoices`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| membership_period_id | UUID FK → membership_periods.id | |
| invoice_number | TEXT UNIQUE | System generated |
| issue_date | DATE | Set to today at creation |
| due_date | DATE | Calculated as `issue_date` + `due_days` from `membership_fees` table |
| amount_due | DECIMAL(10,2) | Looked up from `membership_fees` table at creation — not editable |
| status | ENUM | `unpaid`, `partial`, `paid` — auto-managed by payment logic |
| created_at | TIMESTAMP | |

### `payments`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| invoice_id | UUID FK → invoices.id | |
| amount | DECIMAL(10,2) | |
| method | TEXT | `bank_transfer`, `cash`, `cheque`, `other` |
| reference | TEXT | Optional |
| received_by | UUID FK → members.id | The exec who recorded it |
| received_at | TIMESTAMP | |
| note | TEXT | Optional |
| created_at | TIMESTAMP | |

---

## Key Business Rules

- `membership_periods` are auto-created on registration for non-legacy members — `POST /members/:id/membership-periods` is restricted to legacy members only
- When a membership period is created for a legacy member, an invoice is automatically created against it — no separate invoice creation endpoint needed
- `amount_due` is looked up from `membership_fees` table based on membership type (`single` or `family`) — not manually set
- `issue_date` is set to today at invoice creation
- `due_date` is calculated as `issue_date` + `due_days` from `membership_fees` table
- Invoice status is auto-managed when payments are recorded:
  - total paid = `amount_due` → `status = paid`
  - total paid < `amount_due` → `status = partial`
- A payment cannot exceed the outstanding balance
- A payment cannot be recorded against a fully paid invoice
- Member statement shows current active membership period only — previous years deferred to MVP2
- If a legacy member has no active membership period, statement returns `period: null`, `invoice: null`, `payments: []`
- If a membership period exists but no invoice yet, statement returns `period` with `invoice: null`, `payments: []`
- A member can view their own statement — execs can view any member's statement

---

## API Endpoints

---

### 1. `POST /members/:id/membership-periods`
Create a membership period for a legacy member. Auto-creates an invoice. Exec only.

**Logic:**
- Verify JWT
- Verify `role IN ('admin', 'executive')` → `403` if not
- Verify member exists → `404` if not
- Verify member `is_legacy = true` → `422` with message "Membership periods are auto-created for non-legacy members"
- Verify member has a `membership_id` → `422` if not
- Insert into `membership_periods` with `status = active`
- Look up `amount_due` and `due_days` from `membership_fees` table based on membership type
- Set `issue_date` = today
- Calculate `due_date` = `issue_date` + `due_days`
- Generate unique `invoice_number`
- Insert into `invoices` with `status = unpaid`

**Request body:**
```json
{
  "period_start": "2024-01-01",
  "period_end": "2024-12-31"
}
```

**Response:** `201`
```json
{
  "membership_period": {
    "id": "uuid",
    "membership_id": "uuid",
    "period_start": "2024-01-01",
    "period_end": "2024-12-31",
    "status": "active",
    "created_at": "2026-04-04T10:00:00Z"
  },
  "invoice": {
    "id": "uuid",
    "invoice_number": "INV-2024-001",
    "issue_date": "2026-04-04",
    "due_date": "2026-05-04",
    "amount_due": 50.00,
    "status": "unpaid",
    "created_at": "2026-04-04T10:00:00Z"
  }
}
```

**Errors:**
- `401` — not authenticated
- `403` — not an admin or executive
- `404` — member not found
- `422` — member is not legacy, member has no membership record

---

### 2. `PATCH /membership-periods/:id`
Update a membership period. Exec only.

**Logic:**
- Verify JWT
- Verify `role IN ('admin', 'executive')` → `403` if not
- Verify membership period exists → `404` if not
- Update only fields provided in request body — all fields optional

**Request body** (all fields optional):
```json
{
  "period_start": "2024-01-01",
  "period_end": "2024-12-31",
  "status": "expired"
}
```

**Response:** `200`
```json
{
  "id": "uuid",
  "membership_id": "uuid",
  "period_start": "2024-01-01",
  "period_end": "2024-12-31",
  "status": "expired"
}
```

**Errors:**
- `401` — not authenticated
- `403` — not an admin or executive
- `404` — membership period not found
- `422` — invalid status value

---

### 3. `POST /invoices/:id/payments`
Record a payment against an invoice. Exec only.

**Logic:**
- Verify JWT
- Verify `role IN ('admin', 'executive')` → `403` if not
- Verify invoice exists → `404` if not
- Verify invoice `status != paid` → `422` with message "Cannot record a payment against a fully paid invoice"
- Calculate total payments already recorded against this invoice
- Verify new payment does not exceed outstanding balance → `422` with message "Payment amount exceeds outstanding balance of X"
- Insert into `payments` with `received_by` = caller's member_id
- Recalculate total paid:
  - total paid = `amount_due` → update invoice `status = paid`
  - total paid < `amount_due` → update invoice `status = partial`

**Request body:**
```json
{
  "amount": 25.00,
  "method": "bank_transfer",
  "reference": "REF123456",
  "received_at": "2026-04-04T10:00:00Z",
  "note": "Monthly instalment"
}
```

**Response:** `201`
```json
{
  "id": "uuid",
  "invoice_id": "uuid",
  "amount": 25.00,
  "method": "bank_transfer",
  "reference": "REF123456",
  "received_by": "uuid",
  "received_at": "2026-04-04T10:00:00Z",
  "note": "Monthly instalment",
  "created_at": "2026-04-04T10:00:00Z",
  "invoice": {
    "status": "partial",
    "amount_due": 50.00,
    "total_paid": 25.00,
    "outstanding": 25.00
  }
}
```

**Errors:**
- `401` — not authenticated
- `403` — not an admin or executive
- `404` — invoice not found
- `422` — invoice fully paid, payment exceeds outstanding balance, missing required fields

---

### 4. `GET /members/:id/statement`
View a member's current year statement.

**Logic:**
- Verify JWT
- Verify caller is either the member themselves or has `role IN ('admin', 'executive')` → `403` if not
- Verify member exists → `404` if not
- Fetch current active `membership_period` WHERE `status = active` for the member's `membership_id`
- If no active period → return response with `period: null`, `invoice: null`, `payments: []`
- If active period exists but no invoice → return period with `invoice: null`, `payments: []`
- If invoice exists, fetch all payments against it
- Calculate `total_paid` = SUM of all payments
- Calculate `outstanding` = `amount_due` - `total_paid`

**Response:** `200`
```json
{
  "member_id": "uuid",
  "membership_type": "single",
  "period": {
    "id": "uuid",
    "period_start": "2026-01-01",
    "period_end": "2026-12-31",
    "status": "active"
  },
  "invoice": {
    "id": "uuid",
    "invoice_number": "INV-2026-001",
    "issue_date": "2026-01-01",
    "due_date": "2026-02-01",
    "amount_due": 50.00,
    "status": "partial",
    "total_paid": 25.00,
    "outstanding": 25.00
  },
  "payments": [
    {
      "id": "uuid",
      "amount": 25.00,
      "method": "bank_transfer",
      "reference": "REF123456",
      "received_at": "2026-02-01T10:00:00Z",
      "note": "Monthly instalment"
    }
  ]
}
```

**No active period response:**
```json
{
  "member_id": "uuid",
  "membership_type": "single",
  "period": null,
  "invoice": null,
  "payments": []
}
```

**Period exists but no invoice response:**
```json
{
  "member_id": "uuid",
  "membership_type": "single",
  "period": {
    "id": "uuid",
    "period_start": "2026-01-01",
    "period_end": "2026-12-31",
    "status": "active"
  },
  "invoice": null,
  "payments": []
}
```

**Errors:**
- `401` — not authenticated
- `403` — not the member or an admin/executive
- `404` — member not found
