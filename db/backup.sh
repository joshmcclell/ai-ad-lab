#!/usr/bin/env bash
# =============================================================================
# FlowBase CRM — database backup (workflow W8, docs/04)
#
# Takes a portable, gzipped pg_dump of the whole database and rotates old
# backups. Designed to run unattended on a schedule (cron / n8n Execute Command
# / a CI job). Restore with:  gunzip -c <file> | psql "$DATABASE_URL"
#
# Config via environment:
#   DATABASE_URL        Postgres connection string (required, or set PG* vars)
#   BACKUP_DIR          where to write dumps        (default: ./backups)
#   BACKUP_RETAIN_DAYS  delete dumps older than N   (default: 14)
#
# Free off-site storage (see docs/04 W8): after this runs, sync $BACKUP_DIR to
# Backblaze B2 (10 GB free) / Supabase Storage / Google Drive with rclone.
# =============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/flowbase-${STAMP}.sql.gz"

if [ -z "${DATABASE_URL:-}" ] && [ -z "${PGHOST:-}" ] && [ -z "${PGDATABASE:-}" ]; then
  echo "ERROR: set DATABASE_URL (or PG* env vars) before running." >&2
  exit 2
fi

mkdir -p "$BACKUP_DIR"

# --no-owner/--no-privileges keep the dump portable across roles (e.g. restoring
# a Supabase dump into a local Postgres).
DUMP_ARGS=(--no-owner --no-privileges --format=plain)
if [ -n "${DATABASE_URL:-}" ]; then
  DUMP_ARGS+=("$DATABASE_URL")
fi

echo "Backing up to $OUT …"
pg_dump "${DUMP_ARGS[@]}" | gzip -9 > "$OUT"

SIZE="$(wc -c < "$OUT")"
if [ "$SIZE" -lt 100 ]; then
  echo "ERROR: backup looks empty ($SIZE bytes) — failing." >&2
  rm -f "$OUT"
  exit 1
fi

# Rotate: drop backups older than the retention window.
find "$BACKUP_DIR" -name 'flowbase-*.sql.gz' -type f \
  -mtime "+${BACKUP_RETAIN_DAYS}" -print -delete | sed 's/^/removed old: /' || true

echo "OK: wrote $OUT (${SIZE} bytes); retaining ${BACKUP_RETAIN_DAYS} days."
