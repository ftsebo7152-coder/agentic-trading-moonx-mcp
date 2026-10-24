"""Persistent research artifacts, leases and one-use holdouts. No broker dispatch."""
from datetime import timedelta
from uuid import uuid4
import json
from ..models import TradingError, dumps, fingerprint, utc


class ResearchWorkspace:
    def __init__(self,store):
        self.store=store
        with store.transaction() as tx:
            tx.execute('CREATE TABLE IF NOT EXISTS research_artifacts (id TEXT PRIMARY KEY, kind TEXT NOT NULL, at TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL)')
            tx.execute('CREATE TABLE IF NOT EXISTS research_jobs (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, due TEXT NOT NULL, lease_until TEXT, lease_token TEXT, attempts INTEGER NOT NULL)')
            tx.execute('CREATE TABLE IF NOT EXISTS research_holdouts (id TEXT PRIMARY KEY, dataset_hash TEXT NOT NULL, candidate_hash TEXT NOT NULL, consumed INTEGER NOT NULL DEFAULT 0)')
            tx.execute('CREATE TABLE IF NOT EXISTS research_settlements (prediction_id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL)')

    def append(self,kind,payload,now):
        with self.store.transaction() as tx:
            return self._append(tx,kind,payload,now)

    def _append(self,tx,kind,payload,now):
        if self.store.postgres:raise TradingError('POSTGRES_RESEARCH_CHAIN_NOT_QUALIFIED')
        last=tx.execute('SELECT hash,at FROM research_artifacts ORDER BY at DESC,id DESC LIMIT 1').fetchone()
        # SQLite BEGIN IMMEDIATE serializes the chain and all one-use reservations.
        when=utc(now)
        if last and when<=utc(last['at']):when=utc(last['at'])+timedelta(microseconds=1)
        body={'id':str(uuid4()),'kind':kind,'at':when.isoformat(),'payload':payload,'previous_hash':last['hash'] if last else ''}
        digest=fingerprint(body)
        tx.execute('INSERT INTO research_artifacts(id,kind,at,payload,previous_hash,hash) VALUES(?,?,?,?,?,?)',
                   (body['id'],kind,body['at'],dumps(payload),body['previous_hash'],digest))
        return {**body,'hash':digest}

    def artifacts(self,kind=None):
        with self.store.transaction() as tx:
            rows=tx.execute('SELECT * FROM research_artifacts'+(' WHERE kind=?' if kind else '')+' ORDER BY at,id',(kind,) if kind else ()).fetchall()
        return [{**dict(r),'payload':json.loads(r['payload'])} for r in rows]

    def verify_chain(self):
        previous='';count=0
        for row in self.artifacts():
            digest=row.pop('hash')
            if row['previous_hash']!=previous or fingerprint(row)!=digest:return {'status':'TAMPER_DETECTED','verified':count}
            previous=digest;count+=1
        return {'status':'VERIFIED','verified':count,'note':'Integrity chain, not a signature or an OS permission boundary.'}

    def enqueue(self,kind,payload,due):
        if kind not in {'REVIEW','COLLECT','RECONCILIATION_REMINDER'}:raise TradingError('RESEARCH_JOB_KIND_NOT_ALLOWED')
        identity=fingerprint({'kind':kind,'payload':payload,'due':utc(due)})
        with self.store.transaction() as tx:
            tx.execute('INSERT INTO research_jobs(id,kind,payload,status,due,attempts) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
                       (identity,kind,dumps(payload),'PENDING',utc(due).isoformat(),0))
        return identity

    def claim(self,now,lease_seconds=60,max_attempts=3):
        if lease_seconds<=0 or max_attempts<1:raise TradingError('INVALID_RESEARCH_LEASE')
        when=utc(now).isoformat();token=str(uuid4())
        with self.store.transaction() as tx:
            # This queue is SQLite-only unless a host has serialized claim transactions.
            if self.store.postgres:raise TradingError('POSTGRES_JOB_LEASE_NOT_QUALIFIED')
            row=tx.execute("SELECT * FROM research_jobs WHERE attempts<? AND due<=? AND (status='PENDING' OR (status='RUNNING' AND lease_until<=?)) ORDER BY due,id LIMIT 1",
                           (max_attempts,when,when)).fetchone()
            if not row:return None
            tx.execute("UPDATE research_jobs SET status='RUNNING',lease_until=?,lease_token=?,attempts=attempts+1 WHERE id=?",
                       ((utc(now)+timedelta(seconds=lease_seconds)).isoformat(),token,row['id']))
        return {**dict(row),'status':'RUNNING','payload':json.loads(row['payload']),'lease_token':token,
                'lease_until':(utc(now)+timedelta(seconds=lease_seconds)).isoformat(),'attempts':row['attempts']+1}

    def complete(self,identity,token,now):
        with self.store.transaction() as tx:
            row=tx.execute('SELECT * FROM research_jobs WHERE id=?',(identity,)).fetchone()
            if not row or row['status']!='RUNNING' or row['lease_token']!=token or utc(row['lease_until'])<=utc(now):
                raise TradingError('RESEARCH_LEASE_LOST')
            tx.execute("UPDATE research_jobs SET status='DONE' WHERE id=?",(identity,))

    def register_holdout(self,name,dataset_hash,candidate_hash):
        if self.store.postgres:raise TradingError('POSTGRES_HOLDOUT_NOT_QUALIFIED')
        if not all((name,dataset_hash,candidate_hash)):raise TradingError('HOLDOUT_BINDING_REQUIRED')
        with self.store.transaction() as tx:
            prior=tx.execute('SELECT * FROM research_holdouts WHERE id=?',(name,)).fetchone()
            if prior:
                if (prior['dataset_hash'],prior['candidate_hash'])!=(dataset_hash,candidate_hash):raise TradingError('HOLDOUT_IMMUTABLE')
                return {'id':name,'consumed':bool(prior['consumed'])}
            tx.execute('INSERT INTO research_holdouts(id,dataset_hash,candidate_hash,consumed) VALUES(?,?,?,0)',(name,dataset_hash,candidate_hash))
        return {'id':name,'consumed':False}

    def consume_holdout(self,name,dataset_hash,candidate_hash):
        if self.store.postgres:raise TradingError('POSTGRES_HOLDOUT_NOT_QUALIFIED')
        with self.store.transaction() as tx:
            row=tx.execute('SELECT * FROM research_holdouts WHERE id=?',(name,)).fetchone()
            if not row or row['consumed'] or (row['dataset_hash'],row['candidate_hash'])!=(dataset_hash,candidate_hash):
                raise TradingError('HOLDOUT_UNAVAILABLE')
            tx.execute('UPDATE research_holdouts SET consumed=1 WHERE id=?',(name,))
        return {'id':name,'status':'RESERVED_ONCE','note':'Reservation is not an evaluation result. Never tune on the consumed holdout.'}

    def register_prediction(self,symbol,value,matures_at,source,now):
        if not symbol or not source or utc(matures_at)<=utc(now):raise TradingError('FUTURE_PREDICTION_REQUIRED')
        return self.append('PREDICTION',{'symbol':symbol,'value':value,'matures_at':utc(matures_at),'source':source},now)

    def settle_prediction(self,identity,actual,now):
        with self.store.transaction() as tx:
            prediction=tx.execute("SELECT payload FROM research_artifacts WHERE id=? AND kind='PREDICTION'",(identity,)).fetchone()
            if not prediction or utc(json.loads(prediction['payload'])['matures_at'])>utc(now):raise TradingError('LABEL_NOT_MATURE')
            if tx.execute('SELECT prediction_id FROM research_settlements WHERE prediction_id=?',(identity,)).fetchone():
                raise TradingError('PREDICTION_ALREADY_SETTLED')
            artifact=self._append(tx,'SETTLEMENT',{'prediction_id':identity,'actual':actual},now)
            tx.execute('INSERT INTO research_settlements(prediction_id,artifact_id) VALUES(?,?)',(identity,artifact['id']))
            return artifact
