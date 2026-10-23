from dataclasses import dataclass, fields
from pathlib import Path
import json
import os
from .models import D, Mode, TradingError


def load_private_env(path=".env"):
    """Load only documented settings without shell interpolation or overriding the host."""
    file=Path(path)
    if not file.exists():return
    allowed={"TRADING_DATABASE_URL","TRADING_EMAIL_TO","SMTP_HOST","SMTP_PORT","SMTP_USERNAME","SMTP_PASSWORD","SMTP_FROM",
             "CMC_API_KEY","FRED_API_KEY","FINNHUB_API_KEY","CRYPTOPANIC_API_KEY","MOONX_MCP_URL"}
    for line in file.read_text(encoding="utf8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:continue
        key,value=line.split("=",1);key=key.strip()
        if key in allowed:os.environ.setdefault(key,value.strip())


@dataclass(frozen=True)
class RiskLimits:
    max_risk_per_trade: str = "10"
    max_daily_loss: str = "30"
    max_weekly_loss: str = "60"
    max_aggregate_risk: str = "30"
    max_notional: str = "1500"
    max_margin: str = "750"
    max_asset_notional: str = "750"
    max_correlated_risk: str = "20"
    max_leverage: str = "1"
    max_trades_per_day: int = 10
    max_consecutive_losses: int = 3
    max_data_age_seconds: int = 3900
    max_spread_bps: str = "20"
    max_cost_fraction_of_risk: str = "0.30"
    minimum_reward_risk: str = "1.5"
    liquidation_buffer_fraction: str = "0.02"
    minimum_setup_score: str = "67"

    def __post_init__(self):
        for f in fields(self):
            value = getattr(self, f.name)
            if D(value) <= 0:
                raise TradingError(f"positive limit required: {f.name}")
        for key in ("max_trades_per_day", "max_consecutive_losses", "max_data_age_seconds"):
            if isinstance(getattr(self, key), bool) or not isinstance(getattr(self, key), int):
                raise TradingError(f"integer required: {key}")
        if self.max_trades_per_day > 10 or D(self.minimum_setup_score) > 100:
            raise TradingError("daily ceiling is ten; score ceiling is 100")


@dataclass(frozen=True)
class Settings:
    mode: Mode = Mode.PAPER
    account: str = "local-paper"
    capital: str = "1250"
    watchlist: tuple[str, ...] = ("BTC", "ETH", "SOL", "INJ", "TRX")
    scan_interval_minutes: int = 60
    timezone: str = "Africa/Lagos"
    limits: RiskLimits = RiskLimits()

    def __post_init__(self):
        object.__setattr__(self, "mode", Mode(self.mode))
        object.__setattr__(self, "watchlist", tuple(self.watchlist))
        if D(self.capital) <= 0 or not self.watchlist or len(set(self.watchlist)) != len(self.watchlist):
            raise TradingError("positive capital and unique watchlist required")
        if not isinstance(self.scan_interval_minutes, int) or self.scan_interval_minutes <= 0:
            raise TradingError("invalid scan interval")
        if self.mode == Mode.LIVE_EXECUTION:
            raise TradingError("LIVE_EXECUTION is unavailable in this release; administrative qualification required")

    @classmethod
    def load(cls, path: str | Path):
        data = json.loads(Path(path).read_text(encoding="utf8"))
        data["limits"] = RiskLimits(**data.get("limits", {}))
        return cls(**data)
