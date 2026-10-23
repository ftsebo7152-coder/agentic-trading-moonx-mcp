# E-mails obligatoires et outbox

Une ouverture confirmée par le simulateur et chaque sortie partielle/totale créent un événement et une notification dans la même transaction. Le corps inclut mode, plateforme, instrument, direction, prix, quantité, levier, marge, notionnel, stop, TP, score, stratégie, raison, résultat et identifiants. Les montants restants après sortie sont distingués du montant initial.

L'adresse fournie par l'utilisateur a été placée dans le .env local ignoré, pas dans GitHub. Renseigner le serveur SMTP et les identifiants via gestionnaire de secrets. Le CLI charge les variables documentées du .env sans interpolation shell et sans remplacer celles de l'environnement.

`python -m agentic_trading.cli notify` réserve les événements, utilise STARTTLS et une connexion authentifiée si configurée. État PENDING en absence de service; SENDING pendant le bail; SMTP_ACCEPTED après acceptation. Le nombre d'essais et une prochaine date sont conservés avec backoff borné. Une panne de mail n'annule jamais la clôture déjà commitée.

Le message possède un Message-ID stable. La livraison est au moins une fois : un crash après acceptation SMTP et avant commit peut produire un doublon. Une garantie exactement une fois requiert un fournisseur idempotent et ses callbacks. Les bounces/livraison/lecture ne sont pas suivis; SMTP_ACCEPTED n'est pas DELIVERED. Aucun e-mail effectif n'a été envoyé pendant les tests; l'indisponibilité et l'acquittement ont été simulés.

SMS, WhatsApp Business et push d'hôte restent facultatifs et non implémentés. Une installation de skill n'active aucun canal externe.
