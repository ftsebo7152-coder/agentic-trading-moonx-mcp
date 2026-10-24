"""Synthetic fixtures and test-only attestations. Never market validation evidence."""
from dataclasses import asdict
from datetime import timedelta
import hashlib,hmac
from agentic_trading.models import dumps,fingerprint
from agentic_trading.autonomy.demo import synthetic_bundle
from agentic_trading.demo import scenario

KEY='UNIT_TEST_ONLY_NEVER_A_VALIDATION_KEY'


def runtime_bundle(policy):
    scene=scenario();data=synthetic_bundle();now=scene['now']
    for name in ('markets','higher_markets'):
        data[name]={s:[r for r in rows if r['time']<=now] for s,rows in data[name].items()}
    data.update(macro=scene['macro'],asset_identities={'BTC':{'cmc_slug':'bitcoin'}},validation={},liquidity={},market_metadata={})
    for s in data['markets']:
        basis='SYNTHETIC_UNIT_TEST_ONLY'
        data['market_metadata'][s]={'source':'SYNTHETIC_UNIT_TEST_ONLY','basis':basis,'base_interval':policy.base_interval,
                                   'higher_interval':policy.higher_interval,'fetched_at':now}
        body={'symbol':s,'strategy':'range-breakout-v1','stage':'PAPER_VALIDATED','admitted':True,'artifact_hash':'SYNTHETIC_UNIT_TEST_NOT_A_REAL_QUALIFICATION',
              'issued_at':(now-timedelta(hours=1)).isoformat(),'expires_at':(now+timedelta(days=1)).isoformat(),
              'policy_hash':fingerprint(asdict(policy)),'basis':basis}
        signature=hmac.new(KEY.encode(),dumps(body).encode(),hashlib.sha256).hexdigest()
        data['validation'][s]={'strategies':{'range-breakout-v1':{**body,'signature':signature}}}
        data['liquidity'][s]={'source':'SYNTHETIC_UNIT_TEST_ONLY','asof':now,'bid':'102.49','ask':'102.50','volume_24h':10_000_000,
                              'depth_usd':1_000_000,'quote_currency':'USD','executable_quote':True}
    return data,now
