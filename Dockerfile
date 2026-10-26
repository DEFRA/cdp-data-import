ARG MONGOSH_VERSION=2.3.2
ARG MONGOTOOLS_VERSION=100.10.0
# Keep in step with the Aurora major version: pg_restore 17 fails against a 16 server
ARG POSTGRES_CLIENT_VERSION=16

################################
# AWS-RDS-Token util
################################
FROM golang:1.24 AS awsrdstoken
COPY aws-rds-token ./aws-rds-token
RUN cd aws-rds-token && CGO_ENABLED=0 go build -ldflags="-s -w" -o aws-rds-token

################################
# Tool building stage
################################
FROM debian:bookworm-slim AS tools
ARG MONGOSH_VERSION
ARG MONGOTOOLS_VERSION

RUN apt-get update && \
    apt-get install -y curl unzip zstd python3 binutils ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tools

# AWS CLI (minified)
RUN curl -s -L "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip -q awscliv2.zip
COPY utils/aws-minify.py .
COPY utils/minify.keep .
RUN python3 aws-minify.py ./aws

# Mongosh
RUN curl -sS -L "https://downloads.mongodb.com/compass/mongosh-${MONGOSH_VERSION}-linux-x64.tgz" | tar xz && \
    mv "mongosh-${MONGOSH_VERSION}-linux-x64" mongosh
RUN strip -s mongosh/bin/*

# Mongo tools
RUN curl -sS -L "https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-${MONGOTOOLS_VERSION}.tgz" | tar xz && \
    mv "mongodb-database-tools-debian12-x86_64-${MONGOTOOLS_VERSION}" mongotools
RUN rm mongotools/bin/bsondump && \
    rm mongotools/bin/mongofiles && \
    rm mongotools/bin/mongotop && \
    rm mongotools/bin/mongostat
RUN strip -s mongotools/bin/*

################################
# Runnable image stage
################################
FROM debian:bookworm-slim
ARG POSTGRES_CLIENT_VERSION

RUN apt-get update && \
    apt-get install -y gnupg2 lsb-release ca-certificates curl jq bash tar gzip bzip2 xz-utils zstd zip unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install postgres client
RUN curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor > /usr/share/keyrings/postgresql.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y "postgresql-client-${POSTGRES_CLIENT_VERSION}" && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install AWS RDS CA bundle for verify-full SSL mode
RUN curl -fsSL "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem" -o /etc/ssl/certs/rds-global-bundle.pem

# Add aws-rds-token helper
COPY --from=awsrdstoken /go/aws-rds-token/aws-rds-token /usr/local/bin/aws-rds-token

# Add AWS CLI
COPY --from=tools /tools/aws/dist /usr/local/aws
RUN ln -s /usr/local/aws/aws /usr/local/bin/aws

# Add mongo tools
COPY --from=tools /tools/mongosh/bin/* /usr/local/bin/
COPY --from=tools /tools/mongotools/bin/* /usr/local/bin/

ENV AWS_REGION=eu-west-2
ENV PGSSLMODE=verify-full
ENV PGSSLROOTCERT=/etc/ssl/certs/rds-global-bundle.pem

CMD ["bash"]
