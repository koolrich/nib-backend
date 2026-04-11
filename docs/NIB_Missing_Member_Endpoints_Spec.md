# NIB — Missing Member Endpoints Spec

---

## `GET /members`
List all active members. Supports search and filtering.

**Auth:** JWT required — all authenticated users

**Query parameters:**
| Parameter | Type | Required | Notes |
|---|---|---|---|
| search | string | No | Filter by first or last name, case insensitive |
| needs_setup | boolean | No | If true, return only legacy members with no active membership period. Exec/admin only — return 403 if a regular member attempts this filter |

**Logic:**
- Verify JWT
- Return only members WHERE `status = active`
- Apply `search` filter if provided — match against `first_name` or `last_name`
- Apply `needs_setup` filter if provided:
  - Verify caller has `role IN ('admin', 'executive')` → `403` if not
  - Return only members WHERE `is_legacy = true` AND no `membership_period` exists with `status = active`
- Include `payment_status` in response for exec/admin callers — derived from the member's current active invoice status, null if no active period
- Exclude `payment_status` from response for regular member callers

**Response:** `200`
```json
{
  "members": [
    {
      "id": "uuid",
      "first_name": "Obi",
      "last_name": "Chukwu",
      "membership_type": "single",
      "role": "member",
      "date_joined": "2026-01-01",
      "payment_status": "partial"
    },
    {
      "id": "uuid",
      "first_name": "Ada",
      "last_name": "Nwosu",
      "membership_type": "family",
      "role": "executive",
      "date_joined": "2025-06-01",
      "payment_status": "paid"
    }
  ]
}
```

Note — `payment_status` values are `paid`, `partial`, `unpaid`, or `null` (no active period).

**Errors:**
- `401` — not authenticated
- `403` — regular member attempted `needs_setup` filter

---

## `GET /members/:id`
Get a single member's full profile.

**Auth:** JWT required
- A member can only fetch their own profile
- Exec/admin can fetch any member's profile

**Logic:**
- Verify JWT
- Verify caller is the member themselves OR has `role IN ('admin', 'executive')` → `403` if not
- Verify member exists → `404` if not
- Return full profile

**Response:** `200`
```json
{
  "id": "uuid",
  "first_name": "Obi",
  "last_name": "Chukwu",
  "mobile": "+447911123456",
  "email": "obi@example.com",
  "address_line1": "12 Church Street",
  "address_line2": null,
  "town": "Basingstoke",
  "post_code": "RG21 1AA",
  "member_role": "member",
  "membership_id": "uuid",
  "membership_type": "single",
  "date_joined": "2026-01-01",
  "is_legacy": false,
  "birthday_day": 14,
  "birthday_month": 3,
  "relationship_status": "married",
  "state_of_origin": "Anambra",
  "lga": "Onitsha North",
  "emergency_contact_name": "Ada Chukwu",
  "emergency_contact_phone": "+447922334455",
  "status": "active",
  "created_at": "2026-01-01T10:00:00Z",
  "updated_at": "2026-01-01T10:00:00Z"
}
```

**Errors:**
- `401` — not authenticated
- `403` — member attempting to fetch another member's profile
- `404` — member not found
