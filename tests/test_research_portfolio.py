import unittest
from datetime import datetime,timedelta,timezone
from agentic_trading.enhancements.portfolio import portfolio_diagnostics

NOW=datetime(2026,10,24,tzinfo=timezone.utc)


class PortfolioTests(unittest.TestCase):
    def data(self):
        return [{'symbol':s,'time':NOW-timedelta(days=5-i),'available_at':NOW-timedelta(days=5-i),
                 'source':'SYNTHETIC','return':value*sign} for s,sign in [('BTC',1),('ETH',-1)] for i,value in enumerate([-.1,.02,.03,-.02,.01])]

    def test_opposite_returns_offset_and_correlation_is_negative(self):
        report=portfolio_diagnostics({'BTC':100,'ETH':100},self.data(),NOW)
        self.assertAlmostEqual(report['correlations']['BTC']['ETH'],-1)
        self.assertEqual(report['historical_var_usd'],0)
        self.assertFalse(report['execution_authority'])

    def test_missing_dates_dropped_not_filled(self):
        report=portfolio_diagnostics({'BTC':100,'ETH':100},self.data()[:-1],NOW)
        self.assertEqual(report['aligned_observations'],4)

    def test_future_available_returns_excluded(self):
        data=self.data()
        for row in data:
            if row['symbol']=='ETH':row['available_at']=NOW+timedelta(days=1)
        report=portfolio_diagnostics({'BTC':100,'ETH':100},data,NOW)
        self.assertEqual(report['status'],'INSUFFICIENT_DATA');self.assertEqual(len(report['rejected']),5)

    def test_short_exposure_reverses_profit_and_loss(self):
        long=portfolio_diagnostics({'BTC':100},self.data(),NOW)
        short=portfolio_diagnostics({'BTC':-100},self.data(),NOW)
        self.assertGreater(long['historical_var_usd'],short['historical_var_usd'])

    def test_constant_series_has_undefined_correlation(self):
        data=self.data()
        for row in data:row['return']=0
        report=portfolio_diagnostics({'BTC':100,'ETH':100},data,NOW)
        self.assertIsNone(report['correlations']['BTC']['ETH'])


if __name__=='__main__':unittest.main()
