# OKX : priorité aux démonstrations

Source officielle : [Agent Trade Kit](https://www.okx.com/docs-v5/agent_en/) et [code](https://github.com/okx/agent-trade-kit). Le toolkit fournit un serveur MCP, un profil demo et un mode read-only. Les modules et noms doivent être interrogés dans la version réellement installée; ne pas supposer la parité avec MoonX.

Exemple documenté par OKX : `okx-trade-mcp --profile demo --modules all`. Cette commande n'a pas été lancée ici : aucune clé démo n'a été fournie. Créer les clés depuis l'environnement de démonstration, sans retrait, et monter uniquement les permissions nécessaires.

Le dépôt livre `OKXBrokerAdapter.prepare_demo`, qui construit une requête POST /api/v5/trade/order avec x-simulated-trading: 1, clOrdId, marge isolée, stop et TP attachés. La conversion quantité/contrats doit être donnée depuis les spécifications vérifiées. Le constructeur est testé avec des fixtures, pas avec un compte. Le transport de soumission et la réconciliation restent non implémentés. Aucun changement de levier distant n'est réalisé.

Pour qualifier : lecture des instruments, lecture du compte démo, contrat et tick/lot, configuration du levier et mode de position, ordre démo minimal avec stop, confirmation de fill, contrôle des protections, sortie partielle, fermeture et réconciliation après timeout. Conserver une trace du mode réellement confirmé. Pas de fallback automatique vers OKX si MoonX tombe.
