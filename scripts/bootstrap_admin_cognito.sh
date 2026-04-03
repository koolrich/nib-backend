#!/usr/bin/env bash
# bootstrap_admin_cognito.sh
# Creates the admin Cognito user and links it to the existing DB record.
# Run this LOCALLY after terraform apply.
#
# Usage: ./scripts/bootstrap_admin_cognito.sh
#
# Prerequisites:
#   - AWS CLI configured with credentials
#   - jq installed

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
AWS_REGION="eu-west-2"
SSM_USER_POOL_ID="/nib/cognito/user_pool_id"
SSM_APP_CLIENT_ID="/nib/cognito/app_client_id"

# ── Prompt ────────────────────────────────────────────────────────────────────
read -rp "Admin phone number (e.g. +447123456789): " PHONE
read -rsp "Admin password: " PASSWORD
echo

# ── Fetch Cognito config from SSM ─────────────────────────────────────────────
echo "Fetching Cognito config from SSM..."
USER_POOL_ID=$(aws ssm get-parameter --name "$SSM_USER_POOL_ID" --region "$AWS_REGION" --query "Parameter.Value" --output text)
APP_CLIENT_ID=$(aws ssm get-parameter --name "$SSM_APP_CLIENT_ID" --region "$AWS_REGION" --query "Parameter.Value" --output text)

echo "User Pool ID: $USER_POOL_ID"
echo "App Client ID: $APP_CLIENT_ID"

# ── Create Cognito user ────────────────────────────────────────────────────────
echo "Creating Cognito user..."
USERNAME=$(uuidgen | tr '[:upper:]' '[:lower:]')

SIGNUP_RESPONSE=$(aws cognito-idp sign-up \
  --client-id "$APP_CLIENT_ID" \
  --username "$USERNAME" \
  --password "$PASSWORD" \
  --user-attributes Name=phone_number,Value="$PHONE" \
  --region "$AWS_REGION")

COGNITO_SUB=$(echo "$SIGNUP_RESPONSE" | jq -r '.UserSub')
echo "Cognito user created. Sub: $COGNITO_SUB"

# ── Confirm Cognito user ───────────────────────────────────────────────────────
echo "Confirming Cognito user..."
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id "$USER_POOL_ID" \
  --username "$USERNAME" \
  --region "$AWS_REGION"

echo ""
echo "✓ Cognito user created and confirmed."
echo ""
echo "Now run the following on the EC2 instance to link the Cognito sub to the DB:"
echo ""
echo "  ./scripts/bootstrap_admin_db.sh $COGNITO_SUB"
echo ""
echo "cognito_sub: $COGNITO_SUB"
