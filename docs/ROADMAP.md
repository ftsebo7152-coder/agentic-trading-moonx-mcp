# Travail restant et conditions d'admission

1. Comptes de démonstration OKX/Bybit : obtenir les clés via configuration sécurisée, vérifier l'identité et le mode du compte; implémenter le transport, la gestion du levier et la réconciliation des requêtes préparées; tester ordre+stop, TP, partiels, timeout et reconnexion. Aucun compte démo n'est supposé validé.
2. Données : collecteur continu à cache/rate-limit, contrats réels vérifiés, profondeur/funding/OI, Top 100 authentifié et snapshots historiques, calendrier couvert et observations point-in-time; mapping d'identité PUMP et contrats Nasdaq. Clés externes absentes durant la livraison.
3. Quant : historique assez riche, protocole OOS fixé avant recherche, walk-forward complet de marché, coûts/impact, délisting et composition historique, stress extrêmes, validation de chaque filtre et régime. Pas de stratégie actuellement qualifiée financièrement.
4. Production : tests PostgreSQL réels et multi-hôtes, migrations, sauvegarde/restauration, monotonicité/réconciliation de l'horloge et réservations d'ordres distants, supervision et télémétrie. Le Dockerfile/systemd n'a pas été déployé.
5. Macro : adapter les fournisseurs historiques au contrat de disponibilité, sources officielles BLS/BEA, flux ETF/on-chain autorisés et validation des signaux qualitatifs. Multi-timeframe et scoring historique doivent être étayés, pas simulés.
6. Stratégies avancées : CHOCH/MSS/breaker/mitigation/ORB/retest et gestion de sessions par contrat, puis validations indépendantes. Les SMC restent désactivés.
7. E-mail : configurer SMTP, effectuer un envoi autorisé, surveiller les bounces et définir un fournisseur idempotent si nécessaire. Les messages sont en attente tant que le service n'est pas configuré.
8. Réel MoonX : diligence fournisseur, contrat et protection, mécanisme d'intention UNKNOWN/reconciled, supervision persistante, consentement administratif borné et contrôle des permissions de l'hôte. Ne pas activer le réel par simple changement du prompt. La disponibilité de trois TP natifs reste à démontrer.

Cette feuille de route distingue des dépendances externes et des développements encore nécessaires. La v0.1 livre le cycle PAPER local; elle n'est pas un système de production réel achevé.

Mise a jour du 23 octobre 2026 : une voie LIVE supervisee MoonX futures est maintenant implementee et testee avec transport simule (entree protegee, intents persistants, reconciliation et fermeture). Voir [LIVE_TRADING_SAFETY.md](LIVE_TRADING_SAFETY.md) pour le perimetre et les qualifications de plateforme restantes. PAPER reste le choix courant.
