# NIB Backend — Claude Context

## Project Overview

**NIB = "Ndi Igbo Basingstoke"** — a members-only app to digitize the activities of a Nigerian community association in Basingstoke, UK. Invite-only registration, not open to the public.

**Solo developer:** Richard Nduka (GitHub: `koolrich`)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Mobile | Flutter (Android first, iOS later) |
| Auth | AWS Cognito (phone number as username) |
| API | AWS API Gateway + Lambda (Python 3.13) |
| Database | RDS PostgreSQL (psycopg3) |
| File storage | S3 (PDFs, meeting minutes) |
| SMS | SNS (current) — decision pending on switching to Twilio via fan-out pattern |
| Notifications | AWS SNS + SES + Firebase Cloud Messaging (future) |
| Secrets | AWS SSM Parameter Store |
| Tracing | AWS X-Ray via Lambda Powertools |
| IaC | Terraform (eu-west-2 / London) |
| CI/CD | GitHub Actions (OIDC — no stored AWS credentials) |

---

## Repository Structure

```
nib-backend/                  — this repo (application code + infra)
  src/
    functions/send_invite/    — only Lambda function built so far
    shared/                   — shared layer (db, models, services, instrumentation)
  infra/
    environments/dev/         — dev Terraform (applies on push to main)
    environments/prod/        — prod Terraform (manual trigger only)
    modules/                  — vpc, db, lambda, cognito, vpc_interface_endpoint
  migrations/                 — Flyway SQL migrations
  test/                       — pytest tests
  .github/workflows/          — deploy-dev, deploy-prod, destroy-dev

nib-db-access-infra/          — separate repo, provisions EC2 bastion + SSM endpoints
```

---

## CI/CD Pipeline (deploy-dev.yml)

Triggers on push to `main`:
1. Runs pytest
2. Packages Lambda functions → uploads to S3
3. Packages shared layer → uploads to S3
4. Packages migrations → uploads to S3 (but does NOT run them — manual step still required)
5. Runs `terraform apply` for dev environment

**Gap:** migrations are uploaded but never applied automatically. Requires manual EC2 bastion step.

---

## DB Access / Migrations

A separate project (`nib-db-access-infra`) provisions:
- EC2 `t3.micro` bastion in the private subnet
- SSM VPC endpoints (ssm, ssmmessages, ec2messages) — connect via Session Manager, no SSH
- IAM role with SSM + S3 read access

Scripts baked into AMI at `/usr/local/bin/`:
- `connect-db` — retrieves DB params from SSM, connects via psql
- Migration script — downloads `migrations.zip` from S3, runs Flyway

**Future improvement:** automate migration step in GitHub Actions using SSM port forwarding through the bastion (start instance → tunnel → run Flyway → stop instance). Not a blocker for now.

---

## Architecture Decisions & Context

### VPC Layout
- Private subnets only — no NAT Gateway (cost decision)
- Lambda is in a private subnet, can only reach AWS services via VPC endpoints
- RDS is in a private subnet, not publicly accessible
- SNS VPC interface endpoint exists for Lambda → SNS communication
- SSM VPC endpoints exist but scoped to the bastion's security group — Lambda's security group needs to be added as an ingress source to reach SSM

### SMS — Decision Pending
- Current: SNS SMS direct from Lambda
- Problem: UK alphanumeric Sender ID registration is expensive; SNS spending limit requires Support ticket
- Considered: Twilio — better DX but Lambda can't reach it (no NAT, no VPC endpoint)
- Leading option: **Fan-out pattern** — Lambda publishes to SNS topic (via existing VPC endpoint), a second Lambda outside VPC calls Twilio. ~£3/month extra (Twilio UK number + per-message cost). No new AWS infrastructure needed.
- Alternative: SNS SMS with numeric sender only (no registration needed). One-time Support ticket for spending limit increase.
- **Decision not yet made.**

### Cognito
- User pool provisioned in Terraform
- Phone number as username
- Email optional
- Not yet integrated with Lambda (no JWT validation in any Lambda function)

### Cost (~£22/month current, if fully deployed)
| Component | Cost |
|---|---|
| RDS db.t4g.micro + 20GB gp2 | ~£10 |
| SNS VPC interface endpoint | ~£6 |
| SSM VPC endpoints (bastion) | ~£6 |
| Lambda, API GW, Cognito, S3 | ~£0 |

---

## Current Build Status

### What Works
- `send_invite` Lambda — creates invite in DB, sends SMS via SNS
- Terraform provisions full infra (VPC, RDS, Cognito, Lambda, SNS endpoint)
- GitHub Actions CI/CD pipeline with OIDC auth
- pytest test suite with mocked DB and SNS

### Known Bugs
1. **`get_connection()` outside try block** in `send_invite.py` — if DB connection fails, `finally` block throws `NameError` masking the real error
2. **Silent SMS failure** — `publish_invite_sms` never raises; if SNS returns non-200, invite is committed to DB but SMS never delivered
3. **Hardcoded `invited_by` UUID** in `invite_service.py:28` — placeholder until authenticated invite flow is built. Do not fix in isolation — only meaningful once JWT auth is in place.

### Minor Issues
- SNS client created per invocation in `invite_service.py` — should be module-level singleton like SSM client
- `relationship` field not validated against allowed values (`spouse`, `other`) — could use `Literal['spouse', 'other']`
- Tracer uses broad `except Exception` to detect non-Lambda env — fragile; use `POWERTOOLS_TRACE_DISABLED=true` env var instead
- SNS mock in `conftest.py` missing `ResponseMetadata` — causes spurious error log in tests
- Test event in `utils.py` has no `authorizer` claims — will need updating when JWT auth is added

### What's Missing (in build order)
1. `terraform plan` — verify true deployed state vs Terraform code (possible drift)
2. Fix bugs 1 and 2 above
3. **DB schema V2 migration** — many fields missing vs spec (see schema section below)
4. **API Gateway** — no routes defined in Terraform; Lambda has no HTTP trigger
5. **Registration flow** — validate invite code → Cognito signUp → create member in DB
6. **Login** — authenticate via Cognito, return JWT
7. **Replace hardcoded `invited_by`** — read `sub` from JWT, look up member UUID in DB
8. Events, pledges, contributions, payments endpoints
9. Scheduled jobs (EventBridge) — auto-create membership periods, send reminders

### MVP2 backlog
- Rate limiting on sensitive endpoints (`POST /invites/validate`, `POST /auth/forgot-password`) — API Gateway route-level throttling in Terraform
- iOS build via Codemagic

---

## Target DB Schema (from spec)

### Current schema gaps
The `members` table is missing: `birthday_day`, `birthday_month`, `state_of_origin`, `lga`, `profession`, `relationship_status`, `spouse_name`, `emergency_contact_name`, `emergency_contact_phone`, `status`

Missing tables entirely: `membership_groups`, `events`, `pledges`, `contributions`, `payments`, `invoices`, `reminders`

### Key relationships
```
users (members)
  └── membership_group_id → membership_groups.id

membership_groups
  ├── membership_type: family / single / student
  └── primary_user_id → users.id

membership_periods
  └── membership_group_id → membership_groups.id (one per billing year)

invoices
  └── membership_period_id → membership_periods.id (one annual invoice per period)

payments
  └── invoice_id → invoices.id (multiple partial payments toward annual invoice)

invites
  ├── invited_by → users.id (from JWT — currently hardcoded)
  └── user_id → users.id (filled when invite is used)

events
  └── type: pledge / contribution

pledges / contributions
  └── event_id → events.id
```

### Billing model
- Annual invoice raised per membership group
- Members can pay monthly toward it (partial payments)
- `membership_periods` auto-created by scheduled EventBridge job when billing cycle rolls over

### Member status values
`pending` → `active` → `inactive` / `rejected`

### Invite status values
`pending` → `sent` → `used` / `expired` / `cancelled`

---

## User Roles
| Role | Permissions |
|---|---|
| Member | Send invites, view profile, see events/pledges, view own payments |
| Executive | Everything above + create events, record/reconcile payments, upload docs |

Role stored as field on `members` table. Enforced via JWT claims in Lambda.

---

## iOS Build (future)
No Mac available. Plan: use **Codemagic** (free tier, Flutter-native) for iOS builds. Apple Developer account (£99/year) required when ready. Android ships first.

---

## Working Conventions

- **No Co-Authored-By in commits** — omit the `Co-Authored-By: Claude...` trailer from all commit messages.
- **Terraform routes** — whenever a new endpoint is implemented, add the API Gateway route to `infra/environments/dev/main.tf` in the same commit. Missing routes cause 404s from the gateway even when the Lambda code is correct. Pattern:
  ```hcl
  "METHOD /v1/path/{param}" = {
    lambda_invoke_arn = module.lambda_function_<name>.invoke_arn
    lambda_arn        = module.lambda_function_<name>.function_arn
    requires_auth     = true
  }
  ```
