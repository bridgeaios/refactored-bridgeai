#!/usr/bin/env bash
# backup_before_merge.sh — Dump PostgreSQL, Redis, and Neo4j before schema merge.
#
# Works on Linux (VPS) and Git-Bash/WSL on Windows.
# Requires: pg_dump, redis-cli (optional), neo4j-admin or cypher-shell (optional).
#
# Usage:
#   DATABASE_URL=postgresql://user:pass@host/db ./backup_before_merge.sh
#   # or just set the individual vars below.

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-./backups/${TIMESTAMP}}"
DATABASE_URL="${DATABASE_URL:-}"
REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-}"

mkdir -p "${BACKUP_DIR}"
echo "=== Backup starting at ${TIMESTAMP} ==="
echo "    Target dir: ${BACKUP_DIR}"

# ── 1. PostgreSQL ────────────────────────────────────────────────────────────

if [ -n "${DATABASE_URL}" ]; then
    PG_DUMP_FILE="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql.gz"
    echo ""
    echo "[1/3] Dumping PostgreSQL ..."
    pg_dump "${DATABASE_URL}" --no-owner --no-acl | gzip > "${PG_DUMP_FILE}"
    echo "      Done: ${PG_DUMP_FILE} ($(du -h "${PG_DUMP_FILE}" | cut -f1))"
else
    echo ""
    echo "[1/3] SKIP PostgreSQL — DATABASE_URL not set"
fi

# ── 2. Redis ─────────────────────────────────────────────────────────────────

REDIS_CLI="redis-cli"
if command -v ${REDIS_CLI} &>/dev/null; then
    echo ""
    echo "[2/3] Triggering Redis BGSAVE ..."
    AUTH_FLAG=""
    if [ -n "${REDIS_PASSWORD}" ]; then
        AUTH_FLAG="-a ${REDIS_PASSWORD}"
    fi
    # Trigger background save
    ${REDIS_CLI} -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${AUTH_FLAG} BGSAVE 2>/dev/null || true

    # Wait briefly for save to complete
    sleep 2

    # Try to find and copy the dump.rdb
    REDIS_DIR=$(${REDIS_CLI} -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${AUTH_FLAG} CONFIG GET dir 2>/dev/null | tail -1 || echo "")
    REDIS_FILE=$(${REDIS_CLI} -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${AUTH_FLAG} CONFIG GET dbfilename 2>/dev/null | tail -1 || echo "dump.rdb")

    if [ -n "${REDIS_DIR}" ] && [ -f "${REDIS_DIR}/${REDIS_FILE}" ]; then
        cp "${REDIS_DIR}/${REDIS_FILE}" "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
        echo "      Done: ${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
    else
        echo "      BGSAVE triggered but could not locate dump file (remote Redis or non-standard path)."
        echo "      Check server manually: ${REDIS_HOST}:${REDIS_PORT}"
    fi
else
    echo ""
    echo "[2/3] SKIP Redis — redis-cli not found"
fi

# ── 3. Neo4j ─────────────────────────────────────────────────────────────────

NEO4J_DUMP_FILE="${BACKUP_DIR}/neo4j_${TIMESTAMP}.cypher.gz"

if command -v cypher-shell &>/dev/null && [ -n "${NEO4J_PASSWORD}" ]; then
    echo ""
    echo "[3/3] Exporting Neo4j via cypher-shell ..."
    cypher-shell -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" -a "${NEO4J_URI}" \
        "CALL apoc.export.cypher.all(null, {format:'plain', stream:true}) YIELD cypherStatements RETURN cypherStatements" \
        2>/dev/null | gzip > "${NEO4J_DUMP_FILE}" || true

    if [ -s "${NEO4J_DUMP_FILE}" ]; then
        echo "      Done: ${NEO4J_DUMP_FILE}"
    else
        rm -f "${NEO4J_DUMP_FILE}"
        echo "      Export produced no data (APOC may not be installed). Skipping."
    fi
elif command -v neo4j-admin &>/dev/null; then
    echo ""
    echo "[3/3] Dumping Neo4j via neo4j-admin ..."
    neo4j-admin database dump neo4j --to-path="${BACKUP_DIR}" 2>/dev/null || {
        echo "      neo4j-admin dump failed (server may need to be stopped first). Skipping."
    }
else
    echo ""
    echo "[3/3] SKIP Neo4j — neither cypher-shell nor neo4j-admin found"
fi

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "=== Backup complete ==="
echo "    Location: ${BACKUP_DIR}"
ls -lh "${BACKUP_DIR}/" 2>/dev/null || true
echo ""
