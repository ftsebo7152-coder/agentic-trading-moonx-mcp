"""Transactional outbox. SMTP acceptance is not a delivery/read receipt."""
from datetime import timedelta
from email.message import EmailMessage
from email.utils import make_msgid
import json
import os
import smtplib
import ssl
from uuid import uuid4
from .models import dumps, TradingError


class SMTPEmailSender:
    def __init__(self,env=None):
        self.env=os.environ if env is None else env

    def send(self,event_id,payload):
        env=self.env
        required=("SMTP_HOST","SMTP_FROM","TRADING_EMAIL_TO")
        if any(not env.get(k) for k in required):
            raise TradingError("EMAIL_NOT_CONFIGURED")
        msg=EmailMessage()
        msg["From"]=env["SMTP_FROM"];msg["To"]=env["TRADING_EMAIL_TO"]
        msg["Message-ID"]=f"<{event_id}@agentic-trading.local>"
        msg["Subject"]=f"[{payload.get('mode','SYSTEM')}] {payload['kind']} {payload.get('symbol',payload.get('position',{}).get('symbol',''))}"
        msg.set_content(dumps(payload))
        with smtplib.SMTP(env["SMTP_HOST"],int(env.get("SMTP_PORT",587)),timeout=20) as smtp:
            smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
            if env.get("SMTP_USERNAME"):
                smtp.login(env["SMTP_USERNAME"],env.get("SMTP_PASSWORD",""))
            refused=smtp.send_message(msg)
            if refused:
                raise TradingError("SMTP_RECIPIENT_REJECTED")
        return {"status":"SMTP_ACCEPTED","message_id":msg["Message-ID"],"delivered":False}


class NotificationWorker:
    def __init__(self,store,sender):
        self.store,self.sender=store,sender

    def flush(self,now,limit=50):
        results=[]
        for _ in range(limit):
            token=str(uuid4())
            with self.store.transaction() as tx:
                # PostgreSQL workers skip already claimed rows. SQLite serializes the claim.
                suffix=" FOR UPDATE SKIP LOCKED" if self.store.postgres else ""
                row=tx.execute("SELECT * FROM outbox WHERE status IN ('PENDING','SENDING') AND next_attempt<=? ORDER BY next_attempt,id LIMIT 1"+suffix,(now.isoformat(),)).fetchone()
                if row is None:break
                row=dict(row)
                tx.execute("UPDATE outbox SET status='SENDING',attempts=attempts+1,next_attempt=?,receipt=? WHERE id=?",
                           ((now+timedelta(minutes=2)).isoformat(),token,row["id"]))
            try:
                receipt=self.sender.send(row["id"],json.loads(row["payload"]))
                if receipt.get("status")!="SMTP_ACCEPTED":
                    raise TradingError("PROVIDER_ACCEPTANCE_NOT_CONFIRMED")
                with self.store.transaction() as tx:
                    tx.execute("UPDATE outbox SET status='SMTP_ACCEPTED',receipt=? WHERE id=? AND receipt=?",(dumps(receipt),row["id"],token))
                results.append({"id":row["id"],**receipt})
            except Exception:
                delay=min(3600,30*2**min(row["attempts"],7))
                with self.store.transaction() as tx:
                    tx.execute("UPDATE outbox SET status='PENDING',next_attempt=?,receipt=? WHERE id=? AND receipt=?",
                               ((now+timedelta(seconds=delay)).isoformat(),"EMAIL_SEND_FAILED",row["id"],token))
                results.append({"id":row["id"],"status":"PENDING","incident":"EMAIL_SEND_FAILED"})
        return results
