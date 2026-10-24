# Vérification du moteur PAPER multi-stratégies — 24 octobre 2026

Base de cette extension : `bb2fe42aa4b3ce4f54273504741d617d2fb760a5` (222 tests). Le nouveau parcours ne supprime aucune fonctionnalité historique. Le seul ajout au simulateur existant est le contrôle du bail de compte avant une entrée; les sorties restent autorisées.

## Vérification logicielle

- **295 tests unittest**, dont **73 nouveaux** pour cette extension : timeframes, six stratégies, risque partagé, collecte, replay, sélection walk-forward, état persistant et CLI.
- Agrégation de bougies complètes, refus des trous/duplicates/alignements incorrects, exclusion des données futures et confirmation supérieure réellement observée.
- Scénarios synthétiques positifs LONG/SHORT pour les règles de retest, pullback, réversion Bollinger, SMC et opening range; cassure avec confirmation supérieure testée séparément. Ces tests vérifient les règles, pas leur rentabilité.
- Absence ou changement d'attestation, politique ou base de prix : entrée refusée. Contrat non qualifié, macro manquante, calendrier inconnu, quote absente/périmée, spread non couvert et parité USDT inconnue : entrée refusée.
- Deux actifs partagent le même compte, les mêmes pertes/expositions et les mêmes limites. Arrêt global, signal répété et position retirée de la watchlist traités sans effacer l'état.
- Supervision testée sur bougies M1 : sorties lorsque les entrées sont désactivées, protection d'un actif retiré, gap conservé après redémarrage et revue opérateur explicite.
- Exclusivité par compte, expiration/reprise de bail, refus d'un ancien jeton, contrôle de jeton dans la transaction de risque et protection contre les entrées des anciennes commandes sur le même compte détenu.
- Cycle déjà traité : supervision maintenue et entrée non rejouée. Échec de collecte : incident enregistré, bail libéré, essai ponctuel signalé en échec.
- Incidents persistants dédoublonnés dans les notifications; récupération et rechute distinctes, sans remise à zéro des limites de risque. L'absence d'observations fondamentales ne peut pas être compensée par un score technique élevé.
- Replay chronologique à l'ouverture suivante, contrats non promus artificiellement, compositions historiques CMC exigées, sélection uniquement sur l'entraînement et évaluation ultérieure séparée. Nombre de candidats et folds borné.
- `strategies` et `demo` ne chargent pas `.env` et ne créent pas de base de compte. `check` inspecte le bundle sans ouvrir de position; `--require-ready` produit le code 3 si les entrées ne sont pas qualifiées. La couverture inclut les membres d'un univers dynamique fourni et non seulement les priorités statiques.
- Synchronisation des 29 skills et de leurs copies Claude; validation du maître et égalité de la copie installée après synchronisation.

Commandes de contrôle :

```powershell
python -m unittest discover -s tests -q
python scripts/check_skills.py
python -m agentic_trading.autonomy.cli strategies
python -m agentic_trading.autonomy.cli --output state/autonomy-demo.json demo
```

## Vérification indépendante du skill et des commandes

Une passe indépendante a exécuté les commandes à partir du skill et de la fixture fournis, avec réseau et accès aux secrets bloqués, sorties confinées dans un dossier temporaire. La démonstration a produit deux positions synthétiques clôturées, BTC et XAUUSD, par `range-breakout-v1`. Elle n'a donc pas démontré que les six stratégies négocient toutes dans cette même fixture.

Le contrôle de la fixture a renvoyé `NOT_READY` pour les actifs non qualifiés, ce qui est attendu : elle ne fournit pas de preuve financière, calendrier, quotes ou contrat réel. Les points observés ont conduit à clarifier le code de sortie de `check`, étendre la couverture à l'univers dynamique et supprimer les lectures de secrets/créations de base inutiles pour les commandes de recherche.

## Essai réseau réel, en lecture seule

Collecte exécutée du **24 octobre 2026 à 13:57:14 UTC** à **13:57:24 UTC**, via le nouveau collecteur hybride. Client MCP Python **1.30.0** installé dans l'environnement virtuel de vérification. La session utilise la configuration privée MoonX existante et interdit les outils d'écriture. Aucune URL privée n'est incluse dans les artefacts publiés.

| Actif | Source | Bougies H1 clôturées | Bougies H4 clôturées |
|---|---|---:|---:|
| BTC | OKX spot public | 299 | 299 |
| XAUUSD | MoonX MCP, CFD | 231 | 152 |
| XAGUSD | MoonX MCP, CFD | 230 | 300 |
| NAS100 | MoonX MCP, CFD | 233 | 152 |

Aucun échec de collecte signalé dans cet essai. Les données traditionnelles se terminent vendredi soir; les contrôles temporels les refusent pour de nouvelles entrées ce samedi. Les volumes CFD nuls sont conservés. Résumé public : [autonomy-readonly-smoke.json](../evidence/autonomy-readonly-smoke.json). Les séries complètes et le contrôle détaillé restent dans `state/`, ignoré par Git.

La collecte seule ne qualifie pas des entrées : le contrôle signale notamment spécifications, quotes exécutables/parité, contexte macro/calendrier et attestations à fournir. HOOD n'a pas été collecté ni qualifié : sa source d'action reste à raccorder. Aucun test complet de tous les membres du Top 100 n'est revendiqué.

## Limites conservées

Cette livraison vérifie le logiciel et un échantillon de flux réels. Elle ne constitue pas plusieurs mois de test PAPER/forward, un audit financier, une preuve de rentabilité ou une qualification d'exécution sur compte réel.

La démonstration est synthétique. Le replay fait des hypothèses favorables pour les filtres macro/liquidité historiques manquants, explicitement inscrites dans le rapport; il ne signe aucune attestation. Les paramètres des stratégies restent des hypothèses de recherche.

Le worker continu et son thread de supervision sont fournis et testés par composants; aucun service permanent, tâche planifiée, déploiement cloud, SMTP ou ordre externe n'a été activé. Le modèle systemd n'a pas été déployé sur un hôte Linux. La concurrence du runtime est qualifiée sur SQLite; PostgreSQL y est refusé. Les stops OHLC simulés ne remplacent pas des protections natives de plateforme.

Les résultats locaux ne constituent pas un résultat CI GitHub. Lire [AUTONOMOUS_PAPER.md](AUTONOMOUS_PAPER.md) pour les commandes et prérequis de qualification propres à votre environnement.
