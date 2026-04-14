# NIB Events & Pledges — Data Model and API Spec

---

## Data Model

### `events`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| title | TEXT | |
| date | DATE | |
| type | ENUM | `pledge`, `contribution`, `general` |
| status | ENUM | `upcoming`, `completed` |
| description | TEXT | Optional |
| created_by | UUID FK → members.id | Exec only |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `event_items` (pledge events only)
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| event_id | UUID FK → events.id | |
| name | TEXT | e.g. Crates of Coke |
| quantity_needed | DECIMAL | |
| unit | TEXT | e.g. crates, litres, pots |
| created_at | TIMESTAMP | |

### `pledges`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| event_id | UUID FK → events.id | |
| member_id | UUID FK → members.id | |
| event_item_id | UUID FK → event_items.id | Always populated — every pledge is against a specific item |
| quantity | DECIMAL | |
| status | ENUM | `pledged`, `cancelled` |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `event_contributions`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| event_id | UUID FK → events.id | |
| member_id | UUID FK → members.id | Nullable — null means anonymous |
| pledge_id | UUID FK → pledges.id | Nullable — populated when cash is recorded against a specific pledge |
| amount | DECIMAL | |
| recorded_by | UUID FK → members.id | The exec who recorded it |
| received_at | TIMESTAMP | |
| note | TEXT | Optional |
| created_at | TIMESTAMP | |

---

## Key Business Rules

- Events are created by execs only
- An event is either `pledge` or `contribution` type — not both
- `event_items` only exist for `pledge` events
- Every pledge is always tied to a specific item via `event_item_id` — there is no such thing as a free cash pledge. Cash paid toward an item is recorded as an `event_contribution` with `pledge_id` populated
- Pure cash contributions (not linked to any item) are recorded in `event_contributions` with `pledge_id = null`
- `member_id = null` on `event_contributions` means the contribution is anonymous — shown as "Anonymous" to all members including execs
- A member can pledge the same item more than once but each item has only one pledge record per member — subsequent pledges update the existing record's quantity
- When calculating quantity remaining for an item, exclude the calling member's existing pledge to avoid double counting
- Once an item's total pledged quantity equals `quantity_needed`, it is no longer available for pledging
- A pledge that has a contribution recorded against it cannot be cancelled
- A completed event cannot be edited, have pledges added or cancelled, or have contributions recorded
- Event `type` can only be changed if no `event_items` or `pledges` exist against the event yet

---

## Calculated Fields (derived at query time, not stored)

- `quantity_pledged` = SUM of `quantity` on `pledges` WHERE `status = pledged` for a given `event_item_id`
- `quantity_remaining` = `quantity_needed` - `quantity_pledged`
- `is_available` = `quantity_remaining > 0`
- `total_contributions` = SUM of `amount` on `event_contributions` for a given `event_id`
- `total_pledges` = COUNT of `pledges` WHERE `status = pledged` for a given `event_id`

---

## API Endpoints

---

### 1. `POST /events`
Create a new event. Exec only.

**Request body:**
```json
{
  "title": "August General Meeting",
  "date": "2026-08-12",
  "type": "pledge",
  "description": "Please bring items or contribute cash toward the event"
}
```

**Logic:**
- Verify JWT
- Verify `role = executive` → `403` if not
- Insert into `events` with `status = upcoming`, `created_by` = caller's member_id

**Response:** `201`
```json
{
  "id": "uuid",
  "title": "August General Meeting",
  "date": "2026-08-12",
  "type": "pledge",
  "status": "upcoming",
  "description": "Please bring items or contribute cash toward the event",
  "created_by": "uuid",
  "created_at": "2026-04-04T10:00:00Z"
}
```

**Errors:**
- `401` — not authenticated
- `403` — not an executive
- `422` — missing required fields or invalid event type

---

### 2. `GET /events`
List all upcoming events.

**Logic:**
- Verify JWT
- Return all events WHERE `status = upcoming` ordered by `date` ascending
- Include calculated fields `total_contributions` and `total_pledges` per event

**Response:** `200`
```json
{
  "events": [
    {
      "id": "uuid",
      "title": "August General Meeting",
      "date": "2026-08-12",
      "type": "pledge",
      "status": "upcoming",
      "description": "Please bring items toward the event",
      "created_by": "uuid",
      "created_at": "2026-04-04T10:00:00Z",
      "total_contributions": 250.00,
      "total_pledges": 4
    }
  ]
}
```

**Errors:**
- `401` — not authenticated

---

### 3. `GET /events/:id`
Get full event details including items, pledges and contributions.

**Logic:**
- Verify JWT
- Fetch event — return `404` if not found
- Return full event details
- `items` array only included for `type = pledge` events
- Each item includes `quantity_pledged`, `quantity_remaining`, `is_available`
- `member_name` on contributions returns "Anonymous" where `member_id = null`

**Response:** `200`
```json
{
  "id": "uuid",
  "title": "August General Meeting",
  "date": "2026-08-12",
  "type": "pledge",
  "status": "upcoming",
  "description": "Please bring items toward the event",
  "created_by": "uuid",
  "created_at": "2026-04-04T10:00:00Z",
  "total_contributions": 250.00,
  "total_pledges": 4,
  "items": [
    {
      "id": "uuid",
      "name": "Crates of Coke",
      "unit": "crates",
      "quantity_needed": 10,
      "quantity_pledged": 7,
      "quantity_remaining": 3,
      "is_available": true
    }
  ],
  "pledges": [
    {
      "id": "uuid",
      "member_id": "uuid",
      "member_name": "Obi Chukwu",
      "event_item_id": "uuid",
      "item_name": "Crates of Coke",
      "quantity": 5,
      "status": "pledged",
      "created_at": "2026-04-04T10:00:00Z"
    }
  ],
  "contributions": [
    {
      "id": "uuid",
      "member_id": "uuid",
      "member_name": "Ada Obi",
      "pledge_id": null,
      "amount": 50.00,
      "received_at": "2026-04-04T10:00:00Z"
    },
    {
      "id": "uuid",
      "member_id": null,
      "member_name": "Anonymous",
      "pledge_id": null,
      "amount": 200.00,
      "received_at": "2026-04-04T10:00:00Z"
    }
  ]
}
```

**Errors:**
- `401` — not authenticated
- `404` — event not found

---

### 4. `PATCH /events/:id`
Edit event details or mark as completed. Exec only.

**Logic:**
- Verify JWT
- Verify `role = executive` → `403` if not
- Verify event exists → `404` if not
- Verify event `status = upcoming` → `422` if already completed
- All fields optional — only update fields provided in request body
- If `type` is being changed, verify no `event_items` or `pledges` exist against the event → `422` if they do with message "Cannot change event type after items or pledges have been added"

**Request body** (all fields optional):
```json
{
  "title": "August General Meeting Updated",
  "date": "2026-08-15",
  "description": "Updated description",
  "type": "contribution",
  "status": "completed"
}
```

**Response:** `200`
```json
{
  "id": "uuid",
  "title": "August General Meeting Updated",
  "date": "2026-08-15",
  "type": "contribution",
  "status": "completed",
  "description": "Updated description",
  "updated_at": "2026-04-04T11:00:00Z"
}
```

**Errors:**
- `401` — not authenticated
- `403` — not an executive
- `404` — event not found
- `422` — event already completed, or type change not allowed

---

### 5. `POST /events/:id/items`
Add items to a pledge event. Exec only.

**Logic:**
- Verify JWT
- Verify `role = executive` → `403` if not
- Verify event exists → `404` if not
- Verify event `type = pledge` → `422` if not
- Verify event `status = upcoming` → `422` if completed
- Insert all items into `event_items`

**Request body:**
```json
{
  "items": [
    {
      "name": "Crates of Coke",
      "quantity_needed": 10,
      "unit": "crates"
    },
    {
      "name": "Egusi Soup",
      "quantity_needed": 1,
      "unit": "pot"
    }
  ]
}
```

**Response:** `201`
```json
{
  "items": [
    {
      "id": "uuid",
      "event_id": "uuid",
      "name": "Crates of Coke",
      "quantity_needed": 10,
      "unit": "crates",
      "created_at": "2026-04-04T10:00:00Z"
    },
    {
      "id": "uuid",
      "event_id": "uuid",
      "name": "Egusi Soup",
      "quantity_needed": 1,
      "unit": "pot",
      "created_at": "2026-04-04T10:00:00Z"
    }
  ]
}
```

**Errors:**
- `401` — not authenticated
- `403` — not an executive
- `404` — event not found
- `422` — event is not a pledge event, event is completed, or missing required fields

---

### 6. `PATCH /events/:id/items/:itemId`
Edit an existing event item. Exec only.

**Logic:**
- Verify JWT
- Verify role IN (`admin`, `executive`) → `403` if not
- Verify event exists → `404` if not
- Verify event `status = upcoming` → `422` if completed
- Verify item exists and belongs to this event → `404` if not
- Verify no active pledges exist for this item → `422` with message "Cannot edit an item that has been pledged"
- Update only fields provided — all optional

**Request body** (all fields optional):
```json
{
  "name": "Crates of Pepsi",
  "quantity_needed": 12,
  "unit": "crates"
}
```

**Response:** `200` — updated item record
```json
{
  "id": "uuid",
  "event_id": "uuid",
  "name": "Crates of Pepsi",
  "quantity_needed": 12,
  "unit": "crates",
  "created_at": "2026-04-04T10:00:00Z"
}
```

**Errors:**
- `401` — not authenticated
- `403` — not an executive
- `404` — event or item not found
- `422` — event is completed, or item has active pledges

---

### 7. `DELETE /events/:id/items/:itemId`
Delete an event item. Exec only.

**Logic:**
- Verify JWT
- Verify role IN (`admin`, `executive`) → `403` if not
- Verify event exists → `404` if not
- Verify event `status = upcoming` → `422` if completed
- Verify item exists and belongs to this event → `404` if not
- Verify no active pledges exist for this item → `422` with message "Cannot remove an item that has been pledged"
- Delete item record

**Response:** `204` — no content

**Errors:**
- `401` — not authenticated
- `403` — not an executive
- `404` — event or item not found
- `422` — event is completed, or item has active pledges

---

### 8. `POST /events/:id/pledges`
Create a new pledge against an item.

**Logic:**
- Verify JWT
- Verify event exists → `404` if not
- Verify event `type = pledge` → `422` if not
- Verify event `status = upcoming` → `422` if completed
- Verify `event_item_id` exists and belongs to this event → `404` if not
- Check if a pledge already exists for this `member_id` + `event_item_id` → `409` if yes, with message "You have an existing pledge for this item, please edit it instead"
- Calculate `quantity_remaining` for the item (excluding any existing pledge by this member)
- Verify `quantity_remaining > 0` → `422` with message "This item has been fully pledged"
- Verify requested `quantity` does not exceed `quantity_remaining` → `422` with message "Only X units remaining"
- Insert into `pledges` with `status = pledged`

**Request body:**
```json
{
  "event_item_id": "uuid",
  "quantity": 5
}
```

**Response:** `201`
```json
{
  "id": "uuid",
  "event_id": "uuid",
  "member_id": "uuid",
  "event_item_id": "uuid",
  "item_name": "Crates of Coke",
  "quantity": 5,
  "status": "pledged",
  "created_at": "2026-04-04T10:00:00Z"
}
```

**Errors:**
- `401` — not authenticated
- `404` — event or item not found
- `409` — pledge already exists for this member and item
- `422` — event is completed, not a pledge event, item fully pledged, quantity exceeds remaining, missing required fields

---

### 9. `PATCH /events/:id/pledges/:pledgeId`
Edit an existing pledge quantity.

**Logic:**
- Verify JWT
- Verify event exists → `404` if not
- Verify event `status = upcoming` → `422` if completed
- Verify pledge exists and belongs to this event → `404` if not
- Verify pledge belongs to calling member → `403` if not
- Verify pledge `status = pledged` → `422` if cancelled
- Calculate `quantity_remaining` excluding the member's existing pledge to avoid double counting
- Verify new `quantity` does not exceed `quantity_remaining` → `422` with message "Only X units remaining"
- Update pledge record

**Request body:**
```json
{
  "quantity": 8
}
```

**Response:** `200`
```json
{
  "id": "uuid",
  "event_id": "uuid",
  "member_id": "uuid",
  "event_item_id": "uuid",
  "item_name": "Crates of Coke",
  "quantity": 8,
  "status": "pledged",
  "updated_at": "2026-04-04T11:00:00Z"
}
```

**Errors:**
- `401` — not authenticated
- `403` — pledge does not belong to calling member
- `404` — event or pledge not found
- `422` — event is completed, pledge is cancelled, quantity exceeds remaining

---

### 10. `DELETE /events/:id/pledges/:pledgeId`
Cancel a pledge.

**Logic:**
- Verify JWT
- Verify event exists → `404` if not
- Verify event `status = upcoming` → `422` if completed
- Verify pledge exists and belongs to this event → `404` if not
- Verify pledge belongs to calling member → `403` if not
- Verify pledge `status = pledged` → `422` if already cancelled
- Check if a contribution exists against this pledge via `event_contributions.pledge_id` → `422` if yes with message "Cannot cancel a pledge that has already been paid for"
- Update pledge `status = cancelled`

**Response:** `200`
```json
{
  "id": "uuid",
  "status": "cancelled",
  "updated_at": "2026-04-04T11:00:00Z"
}
```

**Errors:**
- `401` — not authenticated
- `403` — pledge does not belong to calling member
- `404` — event or pledge not found
- `422` — event is completed, pledge already cancelled, pledge has been paid for

---

### 11. `POST /events/:id/contributions`
Record a cash contribution against an event. Exec only.

**Logic:**
- Verify JWT
- Verify `role = executive` → `403` if not
- Verify event exists → `404` if not
- Verify event `status = upcoming` → `422` if completed
- If `pledge_id` provided:
  - Verify pledge exists and belongs to this event → `404` if not
  - Verify pledge `status = pledged` → `422` if cancelled
- If `member_id` provided:
  - Verify member exists → `404` if not
- Insert into `event_contributions` with `recorded_by` = caller's member_id

**Request body:**
```json
{
  "member_id": "uuid",
  "pledge_id": "uuid",
  "amount": 50.00,
  "received_at": "2026-04-04T10:00:00Z",
  "note": "Paid via bank transfer"
}
```

Note — `member_id` is null for anonymous contributions, `pledge_id` is null for pure cash contributions not linked to any pledge.

**Response:** `201`
```json
{
  "id": "uuid",
  "event_id": "uuid",
  "member_id": "uuid",
  "pledge_id": "uuid",
  "amount": 50.00,
  "recorded_by": "uuid",
  "received_at": "2026-04-04T10:00:00Z",
  "note": "Paid via bank transfer",
  "created_at": "2026-04-04T10:00:00Z"
}
```

**Errors:**
- `401` — not authenticated
- `403` — not an executive
- `404` — event, pledge or member not found
- `422` — event is completed, pledge is cancelled, missing required fields

---

### 12. `DELETE /event-contributions/:id`
Delete a contribution record. Exec only.

**Logic:**
- Verify JWT
- Verify role IN (`admin`, `executive`) → `403` if not
- Verify contribution exists → `404` if not
- Delete contribution record

**Response:** `204` — no content

**Errors:**
- `401` — not authenticated
- `403` — not an executive or admin
- `404` — contribution not found

---

### 13. `GET /members/me/pledges`
Get all active pledges for the logged in member across all upcoming events.

**Logic:**
- Verify JWT
- Extract `member_id` from JWT
- Fetch all pledges WHERE `member_id` matches AND `status = pledged`
- Only return pledges for events WHERE `status = upcoming`
- Include event and item details for context
- Include contribution details if a cash contribution has been recorded against the pledge

**Response:** `200`
```json
{
  "pledges": [
    {
      "id": "uuid",
      "event_id": "uuid",
      "event_title": "August General Meeting",
      "event_date": "2026-08-12",
      "item_name": "Crates of Coke",
      "unit": "crates",
      "quantity": 5,
      "status": "pledged",
      "contribution": {
        "amount": 50.00,
        "received_at": "2026-04-04T10:00:00Z"
      },
      "created_at": "2026-04-04T10:00:00Z"
    }
  ]
}
```

Note — `contribution` is null if no cash has been recorded against the pledge yet.

**Errors:**
- `401` — not authenticated
