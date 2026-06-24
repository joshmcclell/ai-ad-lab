#!/usr/bin/env bash
# =============================================================================
# FlowBase CRM — database integration tests
#
# Spins up a throwaway PostgreSQL cluster, applies schema + seed (twice, to prove
# idempotency) + functions + policies, then runs db/test/assertions.sql.
# Exits non-zero on the first failed assertion.
#
# Usage:  db/test/run-tests.sh
# Requires: a PostgreSQL server install (initdb/pg_ctl/psql). Must NOT run as
# root — Postgres refuses. If invoked as root, it re-execs itself as the
# `postgres` user. Unix socket dir is kept short (<100 chars) per PG limits.
# =============================================================================
set -euo pipefail

REPO_DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Re-exec as an unprivileged user if we're root (Postgres won't run as root).
if [ "$(id -u)" = "0" ]; then
  WORK=/tmp/fb-dbtest
  rm -rf "$WORK"; mkdir -p "$WORK"
  cp "$REPO_DB_DIR"/schema.sql "$REPO_DB_DIR"/seed.sql \
     "$REPO_DB_DIR"/functions.sql "$REPO_DB_DIR"/policies.sql \
     "$REPO_DB_DIR"/test/assertions.sql "$WORK/"
  cp "${BASH_SOURCE[0]}" "$WORK/run-tests.sh"
  chmod +x "$WORK/run-tests.sh"
  chown -R postgres:postgres "$WORK"
  exec su postgres -c "FB_WORK=$WORK $WORK/run-tests.sh"
fi

WORK="${FB_WORK:-$(cd "$REPO_DB_DIR/.." && pwd)/.dbtest}"
SQL_DIR="${FB_WORK:-$REPO_DB_DIR}"
[ -n "${FB_WORK:-}" ] || mkdir -p "$WORK"

PGDATA="$WORK/data"
SOCK="$WORK/s"
PGBIN="$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1 || true)"
PSQL="${PGBIN:+$PGBIN/}psql"
INITDB="${PGBIN:+$PGBIN/}initdb"
PGCTL="${PGBIN:+$PGBIN/}pg_ctl"

cleanup() { "$PGCTL" -D "$PGDATA" -w stop >/dev/null 2>&1 || true; }
trap cleanup EXIT

rm -rf "$PGDATA" "$SOCK"; mkdir -p "$SOCK"
"$INITDB" -D "$PGDATA" -U postgres --auth=trust >/dev/null
"$PGCTL" -D "$PGDATA" -o "-k $SOCK -c listen_addresses=" -w start >/dev/null

run() { "$PSQL" -h "$SOCK" -U postgres -d flowbase -v ON_ERROR_STOP=1 -q "$@"; }

"$PSQL" -h "$SOCK" -U postgres -q -c "create database flowbase;"
echo "applying schema, seed (x2), functions, policies…"
run -f "$SQL_DIR/schema.sql"    >/dev/null
run -f "$SQL_DIR/seed.sql"      >/dev/null
run -f "$SQL_DIR/seed.sql"      >/dev/null   # idempotency check
run -f "$SQL_DIR/functions.sql" >/dev/null
run -f "$SQL_DIR/policies.sql"  >/dev/null

echo "running assertions…"
run -f "$SQL_DIR/assertions.sql"

echo
echo "PASS — all database integration tests green"
