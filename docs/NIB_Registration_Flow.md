# NIB Registration Flow — Implementation Spec

---

## Tables Involved

### `invites`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| token | VARCHAR UNIQUE | Unique code sent to invitee |
| status | ENUM | `pending`, `used`, `expired` |
| invited_by | UUID FK → users.id | The logged-in member sending the invite |
| invitee_phone | TEXT | Primary delivery method |
| invitee_email | TEXT | Optional |
| relationship_role | ENUM | `spouse`, `other` |
| user_id | UUID FK → users.id | Populated once invite is used |
| created_at | TIMESTAMP | |
| expires_at | TIMESTAMP | |

### `users`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| cognito_sub | TEXT UNIQUE | From Cognito — primary link between auth and DB |
| email | TEXT | |
| phone | TEXT | Used as Cognito username |
| first_name | TEXT | |
| last_name | TEXT | |
| address | TEXT | |
| postcode | TEXT | |
| state_of_origin | TEXT | Nigerian state |
| lga | TEXT | Dynamic based on state |
| profession | TEXT | |
| birthday_day | INT | Day only |
| birthday_month | INT | Month only |
| relationship_status | ENUM | `single`, `married`, `divorced`, `widowed` |
| spouse_name | TEXT | Optional |
| emergency_contact_name | TEXT | |
| emergency_contact_phone | TEXT | |
| role | ENUM | `member`, `executive` — access control only |
| membership_id | UUID FK → membership.id | |
| invite_id | UUID FK → invites.id | Tracks which invite brought this user in |
| status | ENUM | `pending`, `active`, `inactive` |
| created_at | TIMESTAMP | |

### `membership`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| membership_type | ENUM | `family`, `single`, `student` |
| primary_user_id | UUID FK → users.id | Identifies the primary member of the group |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

> A spouse is identified implicitly: if `users.id ≠ membership.primary_user_id` but they share the same `membership_id`, they are the spouse. No separate role field needed.

### `membership_periods`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| membership_id | UUID FK → membership.id | Billing is at group level, not individual |
| period_start | DATE | Date of registration |
| period_end | DATE | Exactly one year later |
| status | ENUM | `active`, `expired`, `pending` |
| payment_status | ENUM | `paid`, `unpaid`, `partial` |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `invoices`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| membership_period_id | UUID FK → membership_periods.id | |
| invoice_number | TEXT UNIQUE | |
| issue_date | DATE | |
| due_date | DATE | |
| amount_due | DECIMAL | |
| status | ENUM | `issued`, `paid`, `overdue` |

### `payments`
| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| invoice_id | UUID FK → invoices.id | |
| amount | DECIMAL | Partial or full payment |
| method | ENUM | `bank_transfer`, `cash`, `cheque`, `other` |
| reference | TEXT | Bank reference or note |
| received_by | UUID FK → users.id | The executive who recorded it |
| received_at | TIMESTAMP | |
| note | TEXT | Optional |
| created_at | TIMESTAMP | |

---

## Registration Flow — Step by Step

### Step 1 — Invite Creation
- A logged-in member or executive submits an invite via the app
- Required fields: `invitee_phone`, `relationship_role` (`spouse` or `other`)
- Optional fields: `invitee_email`, invitee name (for personalisation)
- Backend generates a unique token, creates a record in `invites` with `status = pending`
- SMS (and optionally email) is sent to the invitee containing the invite code
- Endpoint: `POST /invites` (protected — requires valid JWT)

#### Spouse invite validation
- If `relationship_role = spouse`, backend checks whether the inviter's `membership` already has a second user linked to it
- If yes → return error: *"A spouse is already registered under your membership"*
- If no → proceed

---

### Step 2 — Code Entry (Invitee)
- Invitee installs the app and taps **"Register with Invite Code"**
- Enters their invite code
- Endpoint: `POST /invites/validate` — checks token exists, status is `pending`, not expired
- If valid → return `relationship_role` and `invitee_phone` to pre-fill the registration form
- If invalid/expired → return appropriate error

---

### Step 3 — Profile Completion
- Invitee fills in their profile details and creates a password
- Fields: first name, last name, phone, email, address, postcode, state of origin, LGA, profession, birthday (day + month only), relationship status, spouse name (optional), emergency contact name, emergency contact phone
- Membership type is set based on context:
  - `relationship_role = spouse` → `family` (inherited from inviter's membership)
  - `relationship_role = other` → user selects `single` or `student` during registration

---

### Step 4 — Account Creation
Endpoint: `POST /auth/register`

Backend executes the following in order:

1. **Validate invite token** — confirm still `pending` and not expired
2. **Create Cognito user** — using phone as username, set password
3. **Create `users` record** — store `cognito_sub`, profile fields, `role = member`, `invite_id`, `status = active`
4. **Create or link `membership` record**:
   - If `relationship_role = other` → create new `membership` record, set `primary_user_id` to new user's id, set `membership_type` to selected type. Update `users.membership_id`
   - If `relationship_role = spouse` → fetch inviter's `membership_id`, assign it to the new user. Do NOT create a new membership record
5. **Create `membership_period`** (only if `relationship_role = other`):
   - `period_start` = today
   - `period_end` = today + 1 year
   - `status = pending`, `payment_status = unpaid`
6. **Create `invoice`** (only if `relationship_role = other`):
   - Linked to new `membership_period_id`
   - `status = issued`, `amount_due` = applicable annual fee
7. **Mark invite as used** — set `invites.status = used`, populate `invites.user_id`

---

### Step 5 — Login
- User logs in with phone number and password via Cognito
- On success, Cognito returns a JWT token
- Backend decodes token, extracts `cognito_sub`, fetches user profile and role from `users` table
- Role is stored in app state and used to conditionally render member vs executive UI
- Endpoint: `POST /auth/login`

---

### Forgot Password Flow

**`POST /auth/forgot-password`** — no auth required
- Body: `mobile`
- Verifies mobile is a registered member → 404 if not
- Generates a 6-digit numeric OTP, stores bcrypt hash in `password_reset_tokens` with 15-minute expiry
- Sends OTP via SNS → sms_dispatcher → Twilio
- Response: `200 {"message": "Reset code sent"}`

**`POST /auth/reset-password`** — no auth required
- Body: `mobile`, `code`, `new_password`
- Looks up latest unused, unexpired token for the mobile → 400 if none
- Verifies code matches stored hash → 400 if wrong (same error to avoid enumeration)
- Calls Cognito `AdminSetUserPassword` to update the password
- Marks token as used
- Response: `200 {"message": "Password updated"}`

---

### Change Password Flow

**`POST /auth/change-password`** — requires JWT (access token in Authorization header)
- Body: `current_password`, `new_password`
- Calls Cognito `ChangePassword` using the caller's access token — Cognito verifies current password
- Response: `200 {"message": "Password updated"}`
- Returns `401` if current password is wrong, `422` if new password fails Cognito requirements

---

## Key Business Rules

- One invite → one user. Once used, the invite cannot be reused
- A spouse shares the inviter's `membership`, `membership_period`, and `invoice` — no new billing record is created
- All billing is at the `membership` level, not the individual level
- Annual invoice raised on registration; members may pay monthly toward it — each payment is a separate row in `payments`
- The `payments` table tracks which exec recorded the payment and which invoice it is against — it does not track which member made the payment
- Scheduled job to auto-renew `membership_periods` and raise new `invoices` is deferred to a later phase. It will only run for users with `status = active`
- Executives are bootstrapped manually (seed script or AWS CLI) — the first exec account cannot be created via the invite flow
