# Risque et capital

Capital initial paramétrable (exemple 1 250 USD); risque 10 USD/trade, pertes quotidiennes 30, hebdomadaires 60, risque agrégé 30, notionnel 1 500, marge 750, notionnel par actif 750, risque corrélé 20; levier maximal 1x dans l'exemple. Dix entrées/jour est un plafond absolu, jamais un objectif. Ces valeurs servent aux simulations et ne sont pas des recommandations personnalisées.

Formule de base : risque brut = quantité × valeur du point × distance au stop. Le coût stressé comprend frais des deux côtés, spread et slippage. La quantité est arrondie vers le bas au pas du contrat, avec réserve de mouvement d'entrée et d'arrondi. Marge = notionnel / levier. Les coûts, l'exposition restante et le risque ouvert sont conservés après les partiels.

Le moteur rejette les données périmées/futures, score bas, stratégie non qualifiée, blackout/inconnu, liquidité inconnue, contrat non vérifié, mauvais ticks/lots, dépassements de pertes, marge, exposition, corrélation et séquence de pertes. La liquidation approximative doit rester au-delà du stop et de son tampon. Le fournisseur reste l'autorité sur la liquidation réelle.

Un budget/marge de 50 USD n'est pas une perte autorisée de 50 USD. Un gain théorique 150 pour perte 40 donne 3,75 avant coûts et sorties pondérées. Cette configuration peut être refusée par les limites prudentes. Les leviers 5/10/20/25/30 sont représentables, mais les limites et le contrat doivent les autoriser; ils ne sont pas activés par disponibilité.

Le stop ne peut pas être élargi par l'API de gestion. Le coupe-circuit suspend les entrées et laisse les clôtures protectrices. Les coûts de gap peuvent dépasser le risque calculé au stop.
