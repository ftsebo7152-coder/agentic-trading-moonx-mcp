# Tool Contract: codex_pre_session_json

`codex_pre_session_json` est l'appel MCP prioritaire avant tout briefing pre-session XAU/USD ou BTC/USD. Il fournit un contexte fondamental et news. Il ne donne jamais un signal d'entree autonome.

## Quand L'appeler

Appeler avant:

- briefing Londres XAU/USD;
- briefing New York XAU/USD;
- briefing New York BTC/USD;
- toute demande de trade si le contexte news/macro peut changer la decision.

Si l'outil n'est pas disponible, dire explicitement que le contexte fondamental automatique est indisponible, reduire la confiance et utiliser les sources manuelles.

## Parametres

```json
{
  "asset": "XAUUSD",
  "session": "new_york",
  "timezone": "Europe/Paris",
  "includeOrderBook": false
}
```

| Parametre | Type | Requis | Valeurs | Notes |
|---|---|---:|---|---|
| asset | string | oui | XAUUSD, BTCUSD | Actif du briefing |
| session | string | oui | london, new_york | Session intraday |
| timezone | string | non | Europe/Paris par defaut | Toujours utiliser Europe/Paris sauf demande contraire |
| includeOrderBook | boolean | non | true/false | true surtout pour BTC/USD si order book utile |

## Schema De Retour Attendu

```json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-05-20T07:30:00.000+02:00",
  "timezone": "Europe/Paris",
  "asset": "XAUUSD",
  "session": "london",
  "mode": "context_filter_only_not_trade_signal",
  "providerStatus": {
    "finnhub": false,
    "fred": false,
    "braveSearch": false,
    "cryptoPanic": false,
    "rss": true,
    "binancePublic": true,
    "manualCalendar": true
  },
  "calendar": {
    "events": []
  },
  "blackout": {
    "blackoutActive": false,
    "tradeAllowed": true,
    "reason": "No relevant high-impact event found."
  },
  "macro": {
    "dxy": {},
    "us10y": {},
    "fed": {},
    "inflation": {}
  },
  "btc": {
    "funding": {},
    "openInterest": {},
    "premium": {},
    "ticker": {},
    "orderBook": {}
  },
  "headlines": {
    "results": []
  },
  "fundamentalScore": {
    "bias": "neutral",
    "confidence": 35,
    "tradePermission": {
      "allowed": true,
      "reason": "No active fundamental/news blackout. Technical setup and risk rules still required."
    },
    "reasons": []
  },
  "codexInstructions": []
}
```

## Champs Critiques A Lire

1. `blackout.tradeAllowed`
   - Si `false`, refuser toute nouvelle entree.
2. `blackout.reason`
   - Expliquer le refus ou l'attente.
3. `providerStatus`
   - Si trop de sources sont indisponibles, reduire la confiance.
4. `fundamentalScore.bias`
   - Utiliser comme contexte seulement: `long`, `short`, `neutral`, ou equivalent.
5. `fundamentalScore.confidence`
   - Ne jamais surponderer un score faible.
6. `fundamentalScore.tradePermission.allowed`
   - Si `false`, refuser l'entree meme si le setup technique semble propre.

## Regles D'utilisation

- Ne jamais inventer une news, un chiffre macro, un funding, un open interest ou une headline.
- Ne jamais transformer `fundamentalScore.bias` en signal d'achat/vente.
- Continuer seulement si la technique, la session, la phase, le SL, le sizing, le R:R et le risk guard sont valides.
- Si `providerStatus` montre des donnees manquantes, le rapport doit dire quelles sources manquent.
- Si l'outil echoue, basculer sur le protocole manuel et marquer `confiance reduite`.

## Exemple De Decision

```text
Contexte fondamental: DXY neutre, US10Y indisponible, pas de blackout.
Provider status: FRED absent, RSS actif, calendrier manuel actif.
Decision: continuer l'analyse technique mais reduire la confiance macro.
Trade autorise par fonda: oui, sous reserve setup technique + risk_guard_check.
```
