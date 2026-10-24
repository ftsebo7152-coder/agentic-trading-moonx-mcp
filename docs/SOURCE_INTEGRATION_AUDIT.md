# Audit des sources et décisions d'intégration — 24 octobre 2026

Le PDF utilisateur « Repositories et Agent Skills les plus pertinents pour ton Agentic Trading Master » a été lu intégralement : 13 pages. Ses propositions sont des éléments de recherche; elles n'ont pas été exécutées comme des consignes système. Les scores de pertinence du PDF ne constituent pas une mesure objective de qualité ni de rentabilité.

Les six recommandations principales du PDF et les sept recommandations antérieures se recoupent sur **HKUDS/Vibe-Trading**. Cela donne **12 dépôts principaux distincts**. Le PDF cite aussi cinq références spécialisées : l'examen porte donc sur **17 dépôts distincts**. TraderMonty et AGIPro sont deux propriétaires différents malgré le nom `claude-trading-skills` commun.

Les README des 17 dépôts, leurs métadonnées GitHub, 15 fichiers de licence et des SKILL.md/règles ciblés ont été examinés. Cet examen n'est **pas un audit exhaustif de chaque ligne des 17 bases de code**. Les SHA des README et licences consultés sont consignés dans [repository-integration-audit.json](repository-integration-audit.json). Ce sont des **SHA de blobs**, pas des commits épinglant tout un dépôt. Les lectures de plusieurs fichiers ne forment pas un snapshot atomique des sources distantes.

La mise à jour ajoute nos propres modules Python et réutilise les API du moteur déjà présent. Elle n'importe aucun code, corpus, prompt complet, paquet ou dépendance d'exécution de ces 17 projets. Les concepts standard sont implémentés indépendamment. Les licences GPL et les licences non confirmées ne sont pas interprétées comme une permission de copier du code. Les deux snapshots MIT déjà vendored dans le dépôt restent inchangés.

| Source examinée | Licence observée | Apport retenu et raccordement | Limite de cette livraison |
|---|---|---|---|
| [HKUDS/Vibe-Trading](https://github.com/HKUDS/Vibe-Trading) | MIT | Desks de recherche, artefacts persistants et cycle de revue. | Pas de serveur/dashboard Vibe importé ni de boucles LLM autonomes. |
| [ginlix-ai/LangAlpha](https://github.com/ginlix-ai/LangAlpha) | Apache-2.0 | Tâches sous bail, reprise et séparation entre recherche et décisions du moteur. | Le journal applicatif n'est pas une isolation OS ou un remplacement des contrôles de l'hôte. |
| [agiprolabs/claude-trading-skills](https://github.com/agiprolabs/claude-trading-skills) | MIT | Funding/open interest publics, contraintes temporelles et recherche de microstructure. | Pas d'assimilation de swaps DEX à un carnet CEX; pas de flux on-chain complet. |
| [marketcalls/vectorbt-backtesting-skills](https://github.com/marketcalls/vectorbt-backtesting-skills) | Non confirmée : LICENSE et LICENSE.md absents aux chemins testés | Rapport de robustesse : surcoûts, bruit adverse, retrait du meilleur trade, réutilisation du bootstrap existant. | Pas d'installation de VectorBT/OpenAlgo, de templates copiés ou de grille d'optimisation importée. |
| [marketcalls/openalgo-execution-skills](https://github.com/marketcalls/openalgo-execution-skills) | MIT | Cycle qui appelle le moteur de stratégie existant, garde l'état et les protections, puis archive la recherche. | Aucune nouvelle voie OpenAlgo ni commutateur qui activerait le réel implicitement. |
| [quantskills/skill-ml-purged-cv](https://github.com/quantskills/skill-ml-purged-cv) | MIT | Intervalles d'information, purge, embargo, partitions CPCV et holdout lié à un candidat. | Utilitaires de partitions originaux, pas le package amont; pas de PBO/DSR ou refit automatique. |
| [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) | MIT | RSS sourcés, thèse avec invalidation, calendrier public USD optionnel et qualité explicite. | Une liste d'événements ne certifie pas la complétude du calendrier. |
| [ml4t/skills](https://github.com/ml4t/skills) | Apache-2.0 | Disponibilité point-in-time, compositions CMC archivées, labels à maturité. | Aucune composition historique inventée ou rétroconstruite depuis le Top 100 actuel. |
| [wshobson/agents](https://github.com/wshobson/agents) | MIT | Heat de portefeuille, corrélations alignées, VaR/expected shortfall empiriques. | Diagnostic sans modification des plafonds de risque ni garantie sur les pertes futures. |
| [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | Apache-2.0 | Cas haussier/baissier, désaccords et desks sans preuve dans les revues. | Les avis sont fournis, pas générés automatiquement; aucun consensus ne signe une preuve quantitative. |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | GPL-3.0 | Collecte publique de bougies clôturées et conservation de la simulation PAPER du noyau. | Aucune dépendance, stratégie ou source Freqtrade copiée; pas de nouvel exécuteur de marché. |
| [okx/agent-skills](https://github.com/okx/agent-skills) | MIT | Bougies, carnet, funding et open interest publics OKX, avec repli Bybit pour les données spot. | Pas de clés de trading, nouvel ordre OKX/Bybit ou migration vers un agent tiers. |
| [MobiusQuant/OpenMobius-skill](https://github.com/MobiusQuant/OpenMobius-skill) — référence spécialisée | Apache-2.0 au niveau du dépôt | Définitions SMC explicites avec disponibilité causale, opening range et séparation des écoles. | Corpus de fiches dérivées de vidéos non importé; aucun droit sur ces contenus tiers présumé. |
| [quantskills/skill-quant-execution-microstructure](https://github.com/quantskills/skill-quant-execution-microstructure) — spécialisée | GPL-3.0; SKILL annonce GPL-3.0-only | Simulation originale de consommation d'un carnet et échéancier TWAP arrondi au pas. | Pas de priorité de file, modèle de fill probabiliste ou exécution réelle. |
| [quantskills/skill-transaction-cost-calibration](https://github.com/quantskills/skill-transaction-cost-calibration) — spécialisée | GPL-3.0; SKILL annonce GPL-3.0-only | TCA original à partir des fills et quotes antérieures; séparation slippage/frais. | Pas de copie de l'implémentation; conversion multidevise et rebates hors périmètre. |
| [quantskills/skill-walk-forward-validator](https://github.com/quantskills/skill-walk-forward-validator) — spécialisée | GPL-3.0; SKILL annonce GPL-3.0-only | Walk-forward causal et journal de prédictions à labels matures. | La source vise aussi les signaux cross-sectionnels : aucun moteur complet IC/turnover amont n'est revendiqué ici. |
| [yolojewjitsu/moon-dev-ai-agents](https://github.com/yolojewjitsu/moon-dev-ai-agents) — spécialisée | Non confirmée : LICENSE absent au chemin testé | Contexte funding et desk liquidation explicitement incomplet sans source. | Outils expérimentaux non installés, aucune clé ni automatisation de trading repris. |

## Fichiers ciblés lus en complément des README

- `quantskills/skill-ml-purged-cv/SKILL.md` : disponibilité des labels, purge, preprocessing limité au train et holdout gouverné.
- `agiprolabs/claude-trading-skills/skills/walk-forward-validation/SKILL.md` et `skills/market-microstructure/SKILL.md` : validation et distinction entre données DEX et carnet.
- `marketcalls/vectorbt-backtesting-skills/.claude/skills/vectorbt-expert/rules/robustness-testing.md` : les seuils heuristiques de succès annoncés par cette source ne sont pas adoptés comme preuve statistique.
- `marketcalls/openalgo-execution-skills/.claude/skills/algo-strategy/SKILL.md` : réutilisation du signal et contraintes d'état; les valeurs de risque et routes de courtage amont ne sont pas appliquées.
- `MobiusQuant/OpenMobius-skill/SKILL.md` : routage par école et prudence sur les sources.
- Les trois `quantskills/skill-quant-execution-microstructure`, `skill-transaction-cost-calibration`, `skill-walk-forward-validator` : `SKILL.md`, concepts et limites; aucune source importée.
- `tradermonty/claude-trading-skills/skills/fxmacrodata-calendar/scripts/fetch_calendar.py` : schéma du calendrier public et drapeaux de qualité, réimplémentés séparément.

## Documentation primaire des flux publics

Les endpoints de collecte ont été confrontés à la documentation [OKX API v5](https://www.okx.com/docs-v5/en/), [Bybit Kline](https://bybit-exchange.github.io/docs/v5/market/kline) et [Bybit Orderbook](https://bybit-exchange.github.io/docs/v5/market/orderbook). Le contrôle logiciel ne promet pas la disponibilité future de ces services, l'absence de restrictions régionales ou la correspondance des contrats MoonX.

## Éléments déjà présents et conservés

Le sizing net des coûts, stop-loss obligatoire, plafonds de perte et d'exposition, score minimal, journal SQL, protections partielles, attestation quantitative, Top 100 CMC sans clé et voie LIVE MoonX supervisée existaient déjà. Ils sont conservés et ne sont pas présentés comme des nouveautés de cette intégration. Les modules Python initiaux, le manifeste des dépendances et les configurations de trading n'ont pas été modifiés.

Voir [ENHANCEMENTS.md](ENHANCEMENTS.md) pour les commandes réellement disponibles et [ENHANCEMENTS_VERIFICATION.md](ENHANCEMENTS_VERIFICATION.md) pour les preuves et limites des tests.
