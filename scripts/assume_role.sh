#!/usr/bin/env bash
# assume_role.sh
# Assumes TerraformUserRole and exports credentials into the current shell.
# Usage: source ./scripts/assume_role.sh

ROLE_ARN="arn:aws:iam::021891595998:role/TerraformUserRole"
SESSION_NAME="local-terraform-session"

echo "Assuming role: $ROLE_ARN..."

CREDS=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --role-session-name "$SESSION_NAME" \
  --query "Credentials" \
  --output json)

export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.SessionToken')

echo "Done. Assumed identity:"
aws sts get-caller-identity
