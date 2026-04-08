#!/usr/bin/env bash
# bootstrap_admin_db.sh
# Prints SQL to create the admin member record in the DB.
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

echo "Connect to the DB first: /usr/local/bin/connect-db"
echo ""
echo "Then paste the following SQL:"
echo ""
echo "------------------------------------------------------------"
cat <<SQL
DO \$\$
DECLARE
    v_membership_id UUID;
    v_member_id     UUID;
    v_period_id     UUID;
BEGIN
    INSERT INTO memberships (membership_type)
    VALUES ('individual')
    RETURNING id INTO v_membership_id;

    INSERT INTO members (
        cognito_user_id,
        mobile,
        email,
        first_name,
        last_name,
        member_role,
        membership_id,
        status,
        is_legacy,
        date_joined
    ) VALUES (
        '${COGNITO_SUB}',
        '${PHONE}',
        'koolrich@gmail.com',
        'Richard',
        'Nduka',
        'admin',
        v_membership_id,
        'active',
        false,
        CURRENT_DATE
    )
    RETURNING id INTO v_member_id;

    UPDATE memberships
    SET primary_member_id = v_member_id
    WHERE id = v_membership_id;

    INSERT INTO membership_periods (membership_id, start_date, end_date, status)
    VALUES (v_membership_id, DATE_TRUNC('year', CURRENT_DATE), DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '1 year' - INTERVAL '1 day', 'active')
    RETURNING id INTO v_period_id;

    INSERT INTO invoices (membership_period_id, amount_due, status)
    VALUES (v_period_id, 60.00, 'unpaid');
END \$\$;
SQL
echo "------------------------------------------------------------"
echo ""
echo "If successful, 'DO' will be printed."
