# codex-tradingview-xau-btc-mcp

Pont MCP personnalise pour connecter Codex a TradingView Desktop sous Windows 11.

Le projet est optimise d'abord pour :

- XAU/USD en day trading intraday M15/H1 ;
- BTC/USD en day trading intraday M15/H1 ;
- Paper Trading ;
- validation humaine avant toute execution reelle ;
- extension future a d'autres paires via un profil generique.

## Regles Absolues

- Pas de trade sans stop-loss.
- Risque calcule avant toute entree.
- Paper Trading d'abord.
- Mode reel : validation humaine explicite obligatoire.
- Les news et fondamentaux servent de filtre, jamais de signal d'entree seul.

## Installation Rapide

```powershell
npm install
copy .env.example .env
copy rules.xau-btc.json rules.json
npm run setup:codex:windows
```

Lancer TradingView Desktop avec le port CDP :

```powershell
npm run tv -- launch
```

Verifier la connexion dans le terminal :

```powershell
npm run tv -- status
```

Diagnostic complet :

```powershell
npm run tv -- doctor
```

Dans Codex, l'outil MCP de verification est :

```text
tv_health_check
```

## Commandes De Session

Londres XAU/USD :

```text
session_start asset=XAUUSD session=london mode=paper
```

New York XAU/USD :

```text
session_start asset=XAUUSD session=new_york mode=paper
```

Scan immediat :

```text
session_scan_now
```

Stop session :

```text
session_stop
```

## News Et Fondamentaux

Avant une session XAU/USD :

```text
codex_pre_session_json asset=XAUUSD session=new_york timezone=Europe/Paris
```

Avant une session BTC/USD :

```text
codex_pre_session_json asset=BTCUSD session=new_york timezone=Europe/Paris includeOrderBook=true
```

Sources supportees :

- Binance Futures public API pour BTC ;
- Finnhub pour calendrier economique ;
- FRED pour donnees macro US ;
- Brave News Search ;
- CryptoPanic ;
- RSS publics ;
- calendrier manuel JSON.

Si `blackout.tradeAllowed` vaut `false`, Codex doit refuser toute nouvelle entree.

## Garde-Fous

Avant toute execution :

1. `codex_pre_session_json`
2. `session_scan_now`
3. `risk_calculate_position`
4. `trade_validate_plan`
5. `risk_guard_check`
6. `trading_detect_mode`
7. validation humaine si mode reel

## Documentation

- `SETUP_GUIDE.md`
- `docs/CODEX_WINDOWS_SETUP.md`
- `docs/TRADING_WORKFLOW_XAU_BTC.md`
- `docs/SAFETY_AND_LIMITS.md`
- `docs/MULTI_ASSET_EXTENSION.md`
