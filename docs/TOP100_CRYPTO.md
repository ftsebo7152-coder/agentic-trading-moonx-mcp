# Top 100 dynamique et identité

CoinMarketCapUniverse utilise l'API officielle `/v1/cryptocurrency/listings/latest`, limit=100, sort=market_cap et convert=USD, avec CMC_API_KEY. Documentation consultée : https://coinmarketcap.com/api/documentation/ . `python -m agentic_trading.cli top100` demande la clé, sauvegarde le snapshot en SQL, conserve IDs/noms/slugs/rangs/tags/plateforme/quotes et calcule entrées/sorties depuis le snapshot précédent.

La liste n'est pas codée en dur et les stablecoins restent dans le référentiel tout en étant exclus des opportunités. Le scan de volatilité distingue HIGH_VOLATILITY_TRADABLE, HIGH_VOLATILITY_HIGH_RISK, LOW_LIQUIDITY, INSUFFICIENT_DATA; il exige profondeur, spread, volume, funding et open interest. Les seuils actuels sont des règles de recherche à calibrer, pas une preuve d'exploitabilité.

Aucune clé CMC n'a été fournie : pas de récupération Top 100 authentifiée pendant cette livraison. Un snapshot initial ne reconstitue pas les compositions historiques; conserver les snapshots à partir du déploiement et acquérir l'historique autorisé pour éviter le biais de survivance. La disponibilité MoonX ne se déduit pas du classement. PUMP exige vérification d'identifiant/slug/contrat; INJ désigne Injective. Les profils prioritaires peuvent être hors Top 100 à une date donnée.
