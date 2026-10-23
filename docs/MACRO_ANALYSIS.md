# Fondamentaux et disponibilité temporelle

Chaque observation normalisée contient source, date économique, publication, disponibilité, récupération et confiance. context_at rejette les observations futures ou périmées; un calendrier non couvert bloque les entrées. La liste d'événements seule ne prouve pas la couverture du calendrier. Les blackouts avant/après sont paramétrables.

FREDProvider et FinnhubCalendarProvider implémentent des lectures officielles à clé. Le fournisseur FRED ne prétend pas déduire l'heure de publication à partir d'une simple date : ses résultats bruts sont point_in_time_eligible=false tant que les vintages/disponibilités ne sont pas établis. Le calendrier Finnhub brut exige une normalisation temporelle. Sources à vérifier directement pour les séries : Fed, BLS, BEA et banques centrales; FRED ne remplace pas leur date de disponibilité.

Les intégrations historiques FRED, Finnhub, CryptoPanic, RSS et contexte BTC sont conservées dans vendor/codex-tradingview-xau-btc-mcp/src/providers et core/context.js. Elles ne sont pas chargées automatiquement par le nouveau worker; leurs horodatages doivent être adaptés. Connecteurs BLS/BEA directs, on-chain, ETF et liquidations historiques ne sont pas implémentés dans le nouveau noyau.

Le contexte ne fabrique aucune valeur DXY, rendement réel, funding, dominance ou flux ETF absent. Les proxys tels que l'indice large du dollar ne doivent pas être nommés DXY sans justification. Aucune analyse fondamentale en cours n'est revendiquée à partir du scénario synthétique.
