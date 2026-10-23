"""Detached operator attestation for quantitative evidence; no agent-facing signer."""
import hashlib
import hmac
import os
from .models import dumps,utc


def verify_evidence(evidence,symbol,strategy,now,*,key=None):
    key=key if key is not None else os.environ.get("TRADING_VALIDATION_HMAC_KEY")
    if not key or not evidence:return False
    body={k:v for k,v in evidence.items() if k!="signature"}
    expected=hmac.new(key.encode(),dumps(body).encode(),hashlib.sha256).hexdigest()
    try:
        return (hmac.compare_digest(expected,evidence.get("signature","")) and body["symbol"]==symbol and
                body["strategy"]==strategy and body["stage"]=="PAPER_VALIDATED" and body["admitted"] is True and
                bool(body["artifact_hash"]) and not body.get("synthetic") and
                utc(body["issued_at"])<=utc(now)<utc(body["expires_at"]))
    except (ValueError,KeyError,TypeError):return False
