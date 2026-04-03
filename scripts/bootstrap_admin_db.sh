#!/usr/bin/env bash
# bootstrap_admin_db.sh
# Inserts the admin member record into the DB.
# Run this ON THE EC2 INSTANCE after bootstrap_admin_cognito.sh.
#
# Usage: bash bootstrap_admin_db.sh <cognito_sub> <phone>

set -euo pipefail

COGNITO_SUB="${1:-}"
PHONE="${2:-}"

if [[ -z "$COGNITO_SUB" || -z "$PHONE" ]]; then
  echo "Usage: $0 <cognito_sub> <phone>"
  exit 1
fi

echo "Run the following SQL in your psql session to create the admin member:"
echo ""
echo "------------------------------------------------------------"
cat <<SQL
INSERT INTO memberships (membership_type)
VALUES ('individual')
RETURNING id;
SQL
echo ""
echo "-- Use the membership id returned above in place of <membership_id> below:"
echo ""
cat <<SQL
INSERT INTO members (
    cognito_user_id, mobile, email, first_name, last_name,
    member_role, membership_id, status, is_legacy, date_joined
) VALUES (
    '${COGNITO_SUB}',
    '${PHONE}',
    'admin@nib.org',
    'Admin',
    'User',
    'admin',
    '<membership_id>',
    'active',
    false,
    CURRENT_DATE
);
SQL
echo "------------------------------------------------------------"
echo ""
echo "Then run: /usr/local/bin/connect-db"
