# Résultats de validation - 23 octobre 2026

- Nouveau noyau : **116 tests unittest réussis** lors de la validation initiale complète. Les nouveaux contrôles ajoutés ensuite sont récapitulés dans `evidence/verification.json`.
- Day Trader FR, commit `756e4f53cc1e79032ea7e1961c9e5589ae6477e0` : **318 tests hors ligne réussis**, 50,580 secondes sur l'exécution retenue. Le premier essai a échoué à cause du dossier temporaire Windows du sandbox; l'exécution avec temporaires dans le workspace a réussi.
- TradingView MCP, commit `2cbafc91b9a0c7313fd021a80a3e70576e15a8ef` : **51 tests unitaires réussis**, zéro échec, après installation `npm ci --ignore-scripts` du lockfile. Tests remote/e2e non exécutés.
- Installation du package en environnement virtuel local : réussie avec `pip install --no-build-isolation --no-deps -e ...`, à partir des dépendances déjà disponibles dans le runtime. Le venv de vérification utilisait system-site-packages. Une installation Linux ou un environnement entièrement vierge n'a pas été exécuté ici.
- Démonstration : ouverture simulée puis TP1/TP2/TP3, quantité totale clôturée, frais rapprochés au solde et quatre e-mails en attente. Pas d'envoi SMTP réel.
- MCP MoonX connecté : prix BTC et 100 bougies H1 reçus, aucune mutation appelée.

Tests nouveaux couvrent mathématiques des indicateurs, nombres non finis, mauvais stop/TP, précision, plafond dix trades, pertes, levier/liquidation, score 67, données futures/périmées, blackout inconnu, signature d'attestation, provenance de données, concurrence de quatre threads, idempotence, rollback, reprise et e-mail indisponible.

Les séquences de réseau et leurs permissions ne sont pas qualifiées par des mocks. Aucun test de compte financier démo, aucun ordre réel, aucun PostgreSQL ou cloud de production et aucune notification effective n'est revendiqué. La CI est fournie; son état GitHub doit être vérifié après le push.
