# cdp-data-import

Docker image for CDP data import jobs run in CodeBuild.

## Included tools

- Postgres client (`psql`, `pg_restore`) from `postgresql-client-16`, matching the Aurora major version. Change `POSTGRES_CLIENT_VERSION` in the `Dockerfile` when Aurora is upgraded.
- AWS CLI v2 (minified to import-relevant services)
- `aws-rds-token` helper for IAM auth token + writer endpoint lookup
- Mongo shell + Mongo database tools (`mongorestore`, `mongoimport`, `mongodump`, `mongoexport`)
- Archive tooling: `tar`, `gzip`, `bzip2`, `xz`, `zstd`, `zip`, `unzip`
- RDS CA trust bundle at `/etc/ssl/certs/rds-global-bundle.pem`

Environment defaults:

- `AWS_REGION=eu-west-2`
- `PGSSLMODE=verify-full`
- `PGSSLROOTCERT=/etc/ssl/certs/rds-global-bundle.pem`

## Local build

```bash
docker build -t cdp-data-import:test .
```

## Local smoke test

```bash
docker run --rm cdp-data-import:test bash -lc "pg_restore --version && psql --version && aws --version && aws-rds-token -h >/dev/null && mongorestore --version && mongosh --version && zip -v >/dev/null && test -f \$PGSSLROOTCERT"
```

## Runtime usage

The image is intended for self-service-ops import jobs via CodeBuild `imageOverride` and buildspec override payloads.
