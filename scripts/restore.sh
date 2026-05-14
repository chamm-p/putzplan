#!/usr/bin/env bash
# Restore SQLite from a backup file
# Usage:  ./scripts/restore.sh backups/putzplan-2026-05-14T12-00-00Z.db.gz

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <backup-file.db.gz>"
  echo "Available backups:"
  ls -1t backups/putzplan-*.db.gz 2>/dev/null | head -10 || echo "  (none)"
  exit 1
fi

BACKUP="$1"
[ -f "$BACKUP" ] || { echo "Backup not found: $BACKUP"; exit 1; }

echo ">>> Stopping app container"
docker compose stop putzplan_app

echo ">>> Replacing data/putzplan.db with $BACKUP"
gunzip -c "$BACKUP" > data/putzplan.db.restored
mv data/putzplan.db data/putzplan.db.before-restore.$(date -u +%Y%m%dT%H%M%SZ) 2>/dev/null || true
mv data/putzplan.db.restored data/putzplan.db

echo ">>> Starting app container"
docker compose start putzplan_app

echo ">>> Restore complete."
