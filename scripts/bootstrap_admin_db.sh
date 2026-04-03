#!/usr/bin/env bash
# bootstrap_admin_db.sh
# Links the admin Cognito sub to the existing admin member record in the DB.
# Run this ON THE EC2 INSTANCE after running bootstrap_admin_cognito.sh locally.
#
# Usage: ./scripts/bootstrap_admin_db.sh <cognito_sub>
#
# Prerequisites:
#   - psql available on the EC2 instance
#   - connect-db script available at /usr/local/bin/connect-db

set -euo pipefail

COGNITO_SUB="${1:-}"

if [[ -z "$COGNITO_SUB" ]]; then
  echo "Usage: $0 <cognito_sub>"
  exit 1
fi

ADMIN_MEMBER_ID="093c5291-5f10-4dff-8424-affdfbe7776a"

echo "Run the following SQL in your psql session:"
echo ""
echo "------------------------------------------------------------"
echo "UPDATE members"
echo "SET cognito_user_id = '${COGNITO_SUB}'"
echo "WHERE id = '${ADMIN_MEMBER_ID}';"
echo ""
echo "SELECT id, cognito_user_id, member_role, status"
echo "FROM members"
echo "WHERE id = '${ADMIN_MEMBER_ID}';"
echo "------------------------------------------------------------"
echo ""
echo "Then run: /usr/local/bin/connect-db"
