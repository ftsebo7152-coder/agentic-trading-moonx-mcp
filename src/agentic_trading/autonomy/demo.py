"""Small reproducible multi-asset research fixture; never actual market observations."""
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
from ..demo import scenario
from ..models import Candle,Instrument


def synthetic_bundle():
    scene=scenario();base=scene['bars']+scene['exit_bars'];end=base[-1].time
    anchor=datetime.fromtimestamp(int(end.timestamp())//14400*14400,timezone.utc)
    higher=[Candle(anchor-timedelta(hours=4*(79-i)),80+i*.25,81+i*.25,79+i*.25,80+i*.25,100) for i in range(80)]
    spec=asdict(Instrument('BTC',specs_verified=True,quantity_step='.01',minimum_quantity='.01'));spec.pop('symbol')
    metal={**spec,'correlation_group':'metals'}
    return {'label':'SYNTHETIC_SOFTWARE_DEMONSTRATION_NOT_FINANCIAL_VALIDATION',
            'markets':{s:[asdict(b) for b in base] for s in ('BTC','XAUUSD')},
            'higher_markets':{s:[asdict(b) for b in higher] for s in ('BTC','XAUUSD')},
            'instruments':{'BTC':spec,'XAUUSD':metal}}
