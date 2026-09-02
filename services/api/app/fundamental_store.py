from __future__ import annotations

import math
import os
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .fundamental_catalog import normalize_fundamental_field_key


def default_database_path() -> Path:
    configured = os.getenv("FUNDAMENTALS_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    repository_root = Path(__file__).resolve().parents[3]
    return repository_root / "data" / "local" / "fundamentals.sqlite3"


class FundamentalStore:
    """Latest-snapshot fundamental values backed by a local SQLite database."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path).resolve() if path is not None else default_database_path()
        self._lock = threading.RLock()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fundamental_values (
                symbol TEXT NOT NULL,
                field_id TEXT NOT NULL,
                value REAL NOT NULL,
                as_of TEXT NOT NULL,
                source TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                PRIMARY KEY (symbol, field_id)
            )
            """
        )
        return connection

    @staticmethod
    def normalize_values(values: dict[str, Any]) -> tuple[dict[str, float], list[str], int]:
        normalized: dict[str, float] = {}
        unknown: list[str] = []
        ignored_nulls = 0
        for supplied_key, supplied_value in values.items():
            field_id = normalize_fundamental_field_key(supplied_key)
            if field_id is None:
                unknown.append(supplied_key)
                continue
            if supplied_value is None:
                ignored_nulls += 1
                continue
            if isinstance(supplied_value, bool):
                raise ValueError(f"Boolean is not a valid value for {supplied_key}.")
            try:
                number = float(supplied_value)
            except (TypeError, ValueError) as error:
                raise ValueError(f"Non-numeric value supplied for {supplied_key}.") from error
            if not math.isfinite(number):
                raise ValueError(f"Non-finite value supplied for {supplied_key}.")
            normalized[field_id] = number
        return normalized, unknown, ignored_nulls

    def upsert(self, rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
        prepared: list[tuple[str, str, float, str, str, str]] = []
        symbols: set[str] = set()
        ignored_nulls = 0
        unknown_keys: set[str] = set()
        imported_at = datetime.now(UTC).isoformat()
        for row in rows:
            symbol = str(row["symbol"]).strip().upper()
            as_of = str(row["as_of"])
            source = str(row["source"]).strip()
            values, unknown, ignored = self.normalize_values(dict(row["values"]))
            unknown_keys.update(unknown)
            ignored_nulls += ignored
            symbols.add(symbol)
            prepared.extend(
                (symbol, field_id, value, as_of, source, imported_at)
                for field_id, value in values.items()
            )
        if unknown_keys:
            shown = ", ".join(sorted(unknown_keys)[:10])
            suffix = "…" if len(unknown_keys) > 10 else ""
            raise ValueError(f"Unknown fundamental fields: {shown}{suffix}")
        changed = 0
        with self._lock, self._connect() as connection:
            before_changes = connection.total_changes
            connection.executemany(
                """
                INSERT INTO fundamental_values (symbol, field_id, value, as_of, source, imported_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, field_id) DO UPDATE SET
                    value = excluded.value,
                    as_of = excluded.as_of,
                    source = excluded.source,
                    imported_at = excluded.imported_at
                WHERE excluded.as_of >= fundamental_values.as_of
                """,
                prepared,
            )
            changed = connection.total_changes - before_changes
        return {
            "symbolsImported": len(symbols),
            "valuesSubmitted": len(prepared),
            "valuesImported": changed,
            "staleValuesIgnored": len(prepared) - changed,
            "nullValuesIgnored": ignored_nulls,
        }

    def values_for_symbols(self, symbols: Iterable[str]) -> dict[str, dict[str, float]]:
        normalized = sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})
        if not normalized:
            return {}
        placeholders = ",".join("?" for _ in normalized)
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"SELECT symbol, field_id, value FROM fundamental_values WHERE symbol IN ({placeholders})",
                normalized,
            ).fetchall()
        result: dict[str, dict[str, float]] = {}
        for row in rows:
            result.setdefault(str(row["symbol"]), {})[str(row["field_id"])] = float(row["value"])
        return result

    def snapshot_for_symbol(self, symbol: str) -> dict[str, Any] | None:
        normalized = symbol.strip().upper()
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT field_id, value, as_of, source, imported_at
                FROM fundamental_values
                WHERE symbol = ?
                ORDER BY field_id
                """,
                (normalized,),
            ).fetchall()
        if not rows:
            return None
        return {
            "symbol": normalized,
            "asOf": max(str(row["as_of"]) for row in rows),
            "sources": sorted({str(row["source"]) for row in rows}),
            "importedAt": max(str(row["imported_at"]) for row in rows),
            "values": {str(row["field_id"]): float(row["value"]) for row in rows},
        }

    def status(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            counts = connection.execute(
                "SELECT COUNT(DISTINCT symbol) AS symbols, COUNT(*) AS values_count, MAX(as_of) AS latest_as_of FROM fundamental_values"
            ).fetchone()
            sources = connection.execute(
                "SELECT DISTINCT source FROM fundamental_values ORDER BY source"
            ).fetchall()
        return {
            "configured": bool(counts and counts["values_count"]),
            "symbols": int(counts["symbols"] if counts else 0),
            "values": int(counts["values_count"] if counts else 0),
            "latestAsOf": counts["latest_as_of"] if counts else None,
            "sources": [str(row["source"]) for row in sources],
        }


def attach_fundamentals(
    quotes: list[dict[str, Any]],
    store: FundamentalStore,
) -> list[dict[str, Any]]:
    imported = store.values_for_symbols(quote.get("symbol", "") for quote in quotes)
    return [
        {**quote, "fundamentals": imported.get(str(quote.get("symbol", "")).upper(), {})}
        for quote in quotes
    ]
