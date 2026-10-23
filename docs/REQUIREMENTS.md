# Traçabilité des exigences du PDF

PDF lu intégralement : 55 pages, 72 759 caractères extraits; contrôle visuel des pages 1, 20, 49, 51 et 55 rendues. Le complément pages 51–55 est pris en compte : MoonX futur réel; OKX/Bybit prioritaires pour démo; autonomie fictive; e-mail obligatoire; aucune transaction réelle pendant le développement.

**Livré** signifie implémenté et testé localement dans le périmètre décrit. **Partiel** indique du code concret accompagné d'un développement ou d'une qualification encore nécessaire. **Externe** indique une dépendance non disponible dans cette mission. Le logiciel n'est pas déclaré terminé au sens de toute l'infrastructure de production.

| Section | Exigence | Statut et preuve |
|---|---|---|
| 0–1 | Audit des deux sources et licences | Inventaire statique complet, revue ciblée et deux suites hors ligne exécutées; archives MIT conservées; SOURCE_AUDIT.md décrit la portée |
| 2 | Nouveau dépôt privé, installable | Projet Git séparé, installation editable exécutée; compte et visibilité vérifiés par GitHub |
| 3 | Priorité MoonX / matrice réelle | 35 déclarations, prix et bougies MCP lus; adaptateur read-only et préparation; soumission/réconciliation future non implémentée |
| 4 | OKX / Bybit | Sources officielles et requêtes démo testées avec mocks; pas de compte ni transport démo qualifié |
| 5 | Univers Top 100 et profils | Client CMC dynamique et snapshots SQL; clés, historique et identités/contrats réels non fournis; profils bloqués par défaut |
| 6 | Technique et SMC | Indicateurs testés, breakout confirmé, plusieurs features SMC calculables; plusieurs SMC et fusion multi-timeframe restent non implémentés |
| 7 | Fondamentale/macro | Contrats point-in-time, blackout, lecteurs FRED/Finnhub et fournisseurs archivés; flux frais/intégration continue et filtres statistiques à qualifier |
| 8 | Régimes | Classificateur heuristique structuré et abstention; incertitude explicitée, pas de calibration statistique prétendue |
| 9 | Score 67 | Score décomposé non probabiliste et blocages indépendants; tests aux bornes; confirmation HTF absente vaut zéro |
| 10 | Validation quantitative | Backtest chronologique, walk-forward générique, MC, bootstrap, stress, calibration et métriques; aucune stratégie qualifiée sur marché réel |
| 11 | Risque | Decimal, coût, stop, limites journalières/hebdomadaires, exposition/corrélation/marge et levier; liquidation approximative isolée, contrat réel requis |
| 12 | Stop et TP | Stop obligatoire et trois sorties partielles PAPER, fees et gap; stop ne s'élargit pas; trailing et temporal exit automatique restent à étendre |
| 13 | Orchestrateur | Scan → contexte/régime/setup/score → preuve → risque → simulation → journal/outbox; NO_TRADE explicite; aucun LLM requis |
| 14 | Modes | PAPER par défaut, BACKTEST/REPLAY séparés, LIVE_READ_ONLY prévu; LIVE_EXECUTION rejeté dans cette version |
| 15 | Skills | 29 fichiers canoniques + 29 copies générées; validation structurelle, chargement effectif hôtes/cloud non testé |
| 16 | Cloud / concurrence | Worker et moniteur distincts, SQLite persistant et idempotence testés; backend PostgreSQL et exemples de déploiement fournis mais non exécutés |
| 17 + complément | Notifications e-mail | Outbox atomique, retry, bail et SMTP STARTTLS; destinataire privé configuré localement; fournisseur SMTP absent donc aucun envoi effectif |
| 18 | Journal / performances | Événements, positions, coûts, refus, rapports et métriques par période/groupe; régime non enregistré explicitement UNRECORDED |
| 19 | Supervision / sécurité | Kill switch, fraîcheur, protections, cohérence, blocages et mocks; tests réels de pannes réseau et unknown-fill broker restent liés au futur transport |
| 20–21 | Structure / templates | Modules fonctionnels, CI, docs, sept templates et scripts; aucune tâche cloud réelle créée |
| 22 | Marketing | Aucune promesse de gain ni assimilation à Bloomberg |
| 23–24 | Phases / tests | Noyau PAPER réalisé et suites exécutées; qualifications de production et critères de stratégie restent ouverts |
| 25 | Documentation | Guides demandés et statut de chaque fonction fournis |
| 26–27 | Acceptation / livraison | Cycle local vérifié; exigences externes et fonctions restantes explicitement listées |

## Les 25 critères d'acceptation

1–4 : installation, tests, PAPER et watchlist réalisés. 5 : lecture MoonX constatée et clients de données livrés; collecte continue non qualifiée. 6 : indicateurs exécutés. 7 : contexte fondamental point-in-time exécuté sur fixture, aucune macro live inventée. 8–12 : régime, score, rejet, plan et risque exécutés. 13–18 : ouverture, stop, trois TP, partiels, fermeture et enregistrement exécutés. 19 : notification durable produite; envoi effectif en attente de SMTP. 20 : rapport généré. 21–22 : skills créés et validés; chargement dans nouvelles sessions Codex/Claude à vérifier. 23 : entrée worker --once exécutée, déploiement récurrent externe non activé. 24 : redémarrage vérifié par tests. 25 : inventaire MoonX et sources OKX/Bybit vérifiés, connexions démo et exécution non qualifiées.
