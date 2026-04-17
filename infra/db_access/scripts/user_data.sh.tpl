#!/bin/bash
set -e

# ── Install dependencies ───────────────────────────────────────────────────────
dnf update -y
dnf install -y postgresql15 java-21-amazon-corretto-headless unzip

# ── Install Flyway from S3 ─────────────────────────────────────────────────────
aws s3 cp s3://${s3_bucket}/tools/flyway.tar.gz /tmp/flyway.tar.gz
tar -xzf /tmp/flyway.tar.gz -C /opt/
chmod -R +x /opt/flyway/
FLYWAY_BIN=$(find /opt -name "flyway" -type f | head -1)
ln -sf "$FLYWAY_BIN" /usr/local/bin/flyway

mkdir -p /var/log/flyway

# ── Write connect-db script ────────────────────────────────────────────────────
cat > /usr/local/bin/connect-db << 'SCRIPT'
#!/bin/bash
if [ "$USER" != "ec2-user" ]; then
    exec sudo -u ec2-user "$0" "$@"
    exit
fi

export PGPASSWORD="$(aws ssm get-parameter --name /nib/${env}/db/password --with-decryption --query 'Parameter.Value' --output text)"

psql \
  -h "$(aws ssm get-parameter --name /nib/${env}/db/host --query 'Parameter.Value' --output text)" \
  -U "$(aws ssm get-parameter --name /nib/${env}/db/username --query 'Parameter.Value' --output text)" \
  -d "$(aws ssm get-parameter --name /nib/${env}/db/name --query 'Parameter.Value' --output text)"
SCRIPT
chmod +x /usr/local/bin/connect-db

# ── Write migrate script ───────────────────────────────────────────────────────
cat > /usr/local/bin/migrate << 'SCRIPT'
#!/bin/bash
if [ "$USER" != "ec2-user" ]; then
    exec sudo -u ec2-user "$0" "$@"
    exit
fi

set -e
exec > >(tee -i /var/log/flyway/migration.log) 2>&1

echo "Starting Flyway migration: $(date)"

DB_USER=$(aws ssm get-parameter --name "/nib/${env}/db/username" --query "Parameter.Value" --output text)
DB_PASS=$(aws ssm get-parameter --name "/nib/${env}/db/password" --with-decryption --query "Parameter.Value" --output text)
DB_HOST=$(aws ssm get-parameter --name "/nib/${env}/db/host" --query "Parameter.Value" --output text)
DB_NAME=$(aws ssm get-parameter --name "/nib/${env}/db/name" --query "Parameter.Value" --output text)

mkdir -p /opt/flyway/sql
cd /opt/flyway/sql
aws s3 cp s3://${s3_bucket}/${env}/db-migrations/migrations.zip .
unzip -o migrations.zip

flyway -url="jdbc:postgresql://$DB_HOST:5432/$DB_NAME" \
       -user="$DB_USER" \
       -password="$DB_PASS" \
       -locations="filesystem:/opt/flyway/sql/migrations" \
       migrate

echo "Migration completed: $(date)"
SCRIPT
chmod +x /usr/local/bin/migrate
