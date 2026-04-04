#!/usr/bin/env bash
# bootstrap_admin_cognito.sh
# Creates the admin Cognito user.
# Run this LOCALLY after terraform apply and V2 migration.
#
# Usage: ./scripts/bootstrap_admin_cognito.sh
#
# Prerequisites:
#   - AWS CLI configured with credentials (or assume_role.sh sourced)
#   - jq installed

set -euo pipefail

AWS_REGION="eu-west-2"
SSM_USER_POOL_ID="/nib/cognito/user_pool_id"
SSM_APP_CLIENT_ID="/nib/cognito/app_client_id"

read -rp "Admin phone number (e.g. +447123456789): " PHONE
read -rsp "Admin password: " PASSWORD
echo

echo "Fetching Cognito config from SSM..."
USER_POOL_ID=$(MSYS_NO_PATHCONV=1 aws ssm get-parameter --name "$SSM_USER_POOL_ID" --region "$AWS_REGION" --query "Parameter.Value" --output text)
APP_CLIENT_ID=$(MSYS_NO_PATHCONV=1 aws ssm get-parameter --name "$SSM_APP_CLIENT_ID" --region "$AWS_REGION" --query "Parameter.Value" --output text)

echo "Creating Cognito user..."
USERNAME=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || python -c "import uuid; print(uuid.uuid4())" 2>/dev/null || powershell -Command "[guid]::NewGuid().ToString()" 2>/dev/null)

SIGNUP_RESPONSE=$(aws cognito-idp sign-up \
  --client-id "$APP_CLIENT_ID" \
  --username "$USERNAME" \
  --password "$PASSWORD" \
  --user-attributes Name=phone_number,Value="$PHONE" \
  --region "$AWS_REGION")

COGNITO_SUB=$(echo "$SIGNUP_RESPONSE" | jq -r '.UserSub')

echo "Confirming Cognito user..."
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id "$USER_POOL_ID" \
  --username "$USERNAME" \
  --region "$AWS_REGION"

echo ""
echo "Cognito user created and confirmed."
echo ""
echo "Now run the following on the EC2 instance:"
echo ""
echo "  bash /path/to/scripts/bootstrap_admin_db.sh \"$COGNITO_SUB\" \"$PHONE\""
echo ""
echo "cognito_sub: $COGNITO_SUB"
