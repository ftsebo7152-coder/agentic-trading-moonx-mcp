"""Administrative strategy configuration. Market content never mutates policy."""
from dataclasses import dataclass,field
from pathlib import Path
import json
from ..models import TradingError
from .timeframes import INTERVALS

STRATEGIES=('range-breakout-v1','breakout-retest-v1','trend-pullback-v1','bollinger-reversion-v1','smc-retest-v1','opening-range-v1')


@dataclass(frozen=True)
class StrategyPolicy:
    strategies:tuple=STRATEGIES
    base_interval:str='1h'
    higher_interval:str='4h'
    minimum_base_bars:int=60
    minimum_higher_bars:int=60
    maximum_signal_age_seconds:int=3900
    retest_lookback:int=12
    session_open:str='09:30'
    opening_range_minutes:int=30
    session_timezone:str='America/New_York'
    asset_classes:dict=field(default_factory=lambda:{'XAUUSD':'metal','XAGUSD':'metal','NAS100':'index','HOOD':'equity'})

    def __post_init__(self):
        object.__setattr__(self,'strategies',tuple(self.strategies))
        if not self.strategies or len(set(self.strategies))!=len(self.strategies) or any(s not in STRATEGIES for s in self.strategies):raise TradingError('UNKNOWN_OR_DUPLICATE_STRATEGY')
        if self.base_interval not in INTERVALS or self.higher_interval not in INTERVALS or INTERVALS[self.higher_interval]<=INTERVALS[self.base_interval]:raise TradingError('HIGHER_INTERVAL_REQUIRED')
        for name in ('minimum_base_bars','minimum_higher_bars','maximum_signal_age_seconds','retest_lookback','opening_range_minutes'):
            value=getattr(self,name)
            if type(value) is not int or value<1:raise TradingError('POSITIVE_INTEGER_POLICY_REQUIRED')
        if min(self.minimum_base_bars,self.minimum_higher_bars)<60 or self.retest_lookback>100:raise TradingError('INSUFFICIENT_OR_UNBOUNDED_STRATEGY_HISTORY')
        if any(v not in ('crypto','metal','index','forex','equity') for v in self.asset_classes.values()):raise TradingError('UNKNOWN_ASSET_CLASS')

    def asset_class(self,symbol):return self.asset_classes.get(symbol,'crypto')

    @classmethod
    def load(cls,path):return cls(**json.loads(Path(path).read_text(encoding='utf8')))
