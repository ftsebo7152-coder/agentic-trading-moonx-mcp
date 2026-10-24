# Vérification des extensions — 24 octobre 2026

Base avant modification : `0d3e73e99686cbf254868ebfa0a050b65f5680f7`.

## Vérifications hors ligne

- Suite initiale : **146 tests réussis** avant l'ajout des nouveaux tests.
- Suite étendue : **222 tests**, dont **76 nouveaux**, couvrant purge/embargo, sessions multi-actifs, disponibilité des caractéristiques/labels, causalité, coûts, carnet, TWAP, portefeuille, structures, collecte simulée, journal et intégration.
- Scénarios concurrents SQLite : chaîne d'artefacts, réclamation exclusive d'un job, expiration et changement de jeton, holdout consommé une seule fois et règlement unique d'une prédiction.
- Test d'intégration : une position PAPER ouverte par la démonstration synthétique est protégée et clôturée par le cycle enrichi alors que les entrées sont suspendues. Aucune nouvelle position n'est ouverte dans ce scénario.
- `cycle` refuse `LIVE_EXECUTION`. Aucun outil de compte ni d'ordre réel appelé.
- Neuf exemples CLI synthétiques exécutés, réponses JSON parsées : partitions purgées et walk-forward, robustesse, coûts, carnet, TWAP, portefeuille, revue et structure.
- Synchronisation et contrôle des **29 skills Codex et 29 copies Claude**. Le guide du maître est étendu; les autres skills sont conservés.
- Installateur du maître testé pour idempotence, sauvegarde avant remplacement, conservation des fichiers personnalisés et refus d'une cible portant un autre nom.
- Conservation intégrale du texte initial des fichiers suivis modifiés : README et deux SKILL.md. Les ajouts y sont seulement appendus. Aucun module du noyau, configuration de trading ou dépendance existante modifié; aucun fichier supprimé.

Commandes :

```powershell
python -m unittest discover -s tests -q
python scripts/check_skills.py
python -m agentic_trading.enhancements.cli --help
```

## Essai public en lecture seule

Collecte effectuée le **24 octobre 2026 à 12:38:28 UTC**, sur BTC uniquement, avec plafond de 12 requêtes. Résumé inspectable : [research-public-smoke.json](../evidence/research-public-smoke.json).

| Élément | Observation de cet essai |
|---|---|
| Bougies | 99 bougies horaires clôturées BTC-USDT reçues d'OKX; dernière clôture 12:00 UTC. |
| Carnet | Carnet OKX reçu et diagnostic valide; instantané vers 12:38:30 UTC. |
| Funding / open interest | Les deux champs publics du swap BTC-USDT-SWAP sont disponibles. |
| RSS Cointelegraph | 8 actualités admissibles dans la fenêtre de 24 h. |
| RSS Federal Reserve | Lecture réussie, aucun item admissible dans cette fenêtre. Ce n'est pas une preuve d'absence d'événement macro. |
| RSS CoinDesk | Lecture indisponible pendant l'essai, explicitement signalée. |
| Calendrier USD public | Réponse reçue, 413 événements normalisés; couverture exhaustive inconnue. |
| Budget | 8 requêtes utilisées. Aucun ordre envoyé. |

Les réponses publiques et les disponibilités peuvent évoluer. Cet essai ne qualifie ni tous les actifs CMC, ni toutes les paires des deux plateformes. Le repli Bybit est vérifié par tests de schéma simulés; il n'a pas été nécessaire dans cet essai BTC. Le bundle réel de contrôle reste dans `state/` ignoré par Git; seul le résumé public est publié.

## Limites conservées explicitement

Pas de démonstration de rentabilité ou de validation d'une stratégie financière; pas de refit ML complet, PBO/DSR, carnet en streaming, priorité de file, historique de liquidations ou collecte on-chain exhaustive. Les desks sans données restent manquants.

Les données spot et l'identité de recherche ne qualifient pas un contrat MoonX futures. La parité USDT/USD, les spécifications et les attestations nécessaires aux entrées ne sont pas fabriquées. Le calendrier observé ne lève pas un blackout de couverture inconnue.

Aucun ordre réel ou de compte démo externe, aucune notification e-mail, tâche récurrente ou infrastructure cloud n'a été lancé. PostgreSQL n'est pas qualifié pour les nouvelles opérations concurrentes et celles-ci le refusent. Les tests locaux ne constituent pas un résultat CI GitHub; l'état de cette dernière est à constater séparément après publication.
