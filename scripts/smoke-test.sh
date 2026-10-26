#!/usr/bin/env bash
# Checks the tools import jobs rely on are present in the image.
set -euo pipefail

pg_restore --version
psql --version
aws --version
aws-rds-token -h >/dev/null
mongorestore --version
mongosh --version
zip -v >/dev/null
test -f "$PGSSLROOTCERT"
