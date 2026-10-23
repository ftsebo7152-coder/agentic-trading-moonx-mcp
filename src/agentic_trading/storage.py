"""Transactional SQLite/PostgreSQL persistence; no ephemeral trading state."""
from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
from uuid import uuid4
from .models import D, dumps, now_utc, TradingError

DDL = (
    "CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, balance TEXT NOT NULL, halted INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS positions (id TEXT PRIMARY KEY, account TEXT NOT NULL, signal TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(account, signal))",
    "CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, account TEXT NOT NULL, at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS events_account_time ON events(account, at)",
    "CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, account TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, next_attempt TEXT NOT NULL, receipt TEXT)",
    "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, account TEXT NOT NULL, at TEXT NOT NULL, payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)",
)


class Transaction:
    def __init__(self, connection, postgres=False):
        self.connection, self.postgres = connection, postgres

    def execute(self, sql, args=()):
        return self.connection.execute(sql.replace("?", "%s") if self.postgres else sql, args)

    def account(self, account):
        row = self.execute("SELECT * FROM accounts WHERE id=?", (account,)).fetchone()
        if row is None:
            raise TradingError("unknown account")
        return dict(row)

    def positions(self, account, open_only=True):
        rows = self.execute("SELECT payload FROM positions WHERE account=?" + (" AND status='OPEN'" if open_only else ""), (account,))
        return [json.loads(row["payload"]) for row in rows]

    def events(self, account):
        return [dict(row) | {"payload": json.loads(row["payload"])} for row in self.execute(
            "SELECT * FROM events WHERE account=? ORDER BY at,id", (account,))]

    def event(self, account, kind, payload, at, notify=False):
        event_id = str(uuid4())
        body = {"event_id": event_id, "kind": kind, "time": at.isoformat(), **payload}
        self.execute("INSERT INTO events(id,account,at,kind,payload) VALUES(?,?,?,?,?)",
                     (event_id, account, at.isoformat(), kind, dumps(body)))
        if notify:
            self.execute("INSERT INTO outbox(id,account,payload,status,next_attempt) VALUES(?,?,?,?,?)",
                         (event_id, account, dumps(body), "PENDING", at.isoformat()))
        return body

    def save_position(self, position):
        self.execute("UPDATE positions SET payload=?,status=? WHERE id=? AND account=?",
                     (dumps(position), position["status"], position["id"], position["account"]))


class Store:
    def __init__(self, url="state/trading.sqlite"):
        self.url = str(url)
        self.postgres = self.url.startswith(("postgresql://", "postgres://"))
        if not self.postgres:
            Path(self.url).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as tx:
            for sql in DDL:
                tx.execute(sql)

    def connect(self):
        if self.postgres:
            import psycopg
            from psycopg.rows import dict_row
            return psycopg.connect(self.url, row_factory=dict_row)
        conn = sqlite3.connect(self.url, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def transaction(self, account=None):
        conn = self.connect()
        tx = Transaction(conn, self.postgres)
        try:
            conn.execute("BEGIN" if self.postgres else "BEGIN IMMEDIATE")
            if account is not None:
                suffix = " FOR UPDATE" if self.postgres else ""
                if tx.execute("SELECT id FROM accounts WHERE id=?" + suffix, (account,)).fetchone() is None:
                    raise TradingError("unknown account")
            yield tx
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_account(self, account, capital):
        if D(capital) <= 0:
            raise TradingError("positive capital required")
        with self.transaction() as tx:
            tx.execute("INSERT INTO accounts(id,balance) VALUES(?,?) ON CONFLICT(id) DO NOTHING", (account, str(D(capital))))

    def halt(self, account):
        with self.transaction(account) as tx:
            tx.execute("UPDATE accounts SET halted=1 WHERE id=?", (account,))
            tx.event(account, "HALT", {"reason": "operator kill switch"}, now_utc(), notify=True)

    def resume(self, account, *, administrative_confirmation=False):
        if not administrative_confirmation:
            raise TradingError("explicit operator confirmation required")
        with self.transaction(account) as tx:
            tx.execute("UPDATE accounts SET halted=0 WHERE id=?", (account,))
            tx.event(account, "RESUME", {"reason": "operator confirmed"}, now_utc())

    def snapshot(self, kind, payload, at):
        with self.transaction() as tx:
            tx.execute("INSERT INTO snapshots(id,at,kind,payload) VALUES(?,?,?,?)", (str(uuid4()), at.isoformat(), kind, dumps(payload)))

    def report(self, account):
        with self.transaction(account) as tx:
            events = tx.events(account)
            positions = tx.positions(account, False)
            return {"account": tx.account(account), "positions": positions, "events": events,
                    "notifications": [dict(r) for r in tx.execute("SELECT id,status,attempts,receipt FROM outbox WHERE account=?", (account,))]}
