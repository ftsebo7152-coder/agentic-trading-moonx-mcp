"""Convert an observed H1 MCP response to a research bundle; never invent contract specs."""
from pathlib import Path
import argparse,json
from agentic_trading.market_data import moonx_candles
from agentic_trading.models import dumps,utc

p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');p.add_argument('--asof',required=True)
a=p.parse_args();raw=json.loads(Path(a.input).read_text(encoding='utf8'))
bars=moonx_candles(raw,3600,utc(a.asof))
bundle={'label':'OBSERVED_MOONX_HISTORICAL_RESEARCH_ONLY','markets':{raw['symbol']:bars},
        'instruments':{raw['symbol']:{'specs_verified':False}},'macro':{},'liquidity':{},'validation':{}}
Path(a.output).write_text(dumps(bundle),encoding='utf8')
print(f'{len(bars)} completed bars exported. Contract specs and validation remain unverified.')
