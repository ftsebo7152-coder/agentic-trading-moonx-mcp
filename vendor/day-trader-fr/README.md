# Day Trader FR

11 skills Claude pour analyser les actions américaines, préparer tes entrées et sorties, simuler un scénario et contrôler ton risque avant chaque ordre.

**Adaptation française par Dan AI Lab de [day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill), créé par [Jake Schincariol](https://opusjake.ai).** Le projet d'origine est sous licence MIT. Son copyright et le texte de sa licence sont conservés dans [LICENSE](LICENSE). Cette adaptation est indépendante et ne constitue pas une collaboration avec l'auteur.

Les instructions et les réponses de l'assistant sont en français. Les 11 scripts Python, leurs paramètres, leurs fichiers JSON et les données de test sont conservés. Le seul changement du moteur est l'acceptation du mot `oui` comme confirmation explicite d'un seul ticket, en plus des réponses anglaises d'origine. Les diagnostics bruts des scripts restent en anglais ; l'assistant les explique en français.

## Ce que tu peux faire

| Commande | Rôle |
| --- | --- |
| `/trader-scanner` | Repérer les graphiques qui correspondent à une règle : cassure de la plage d'ouverture, drapeau haussier, survente ou rebond. |
| `/trader-news` | Suivre les actualités, les dépôts SEC et les variations des actions surveillées. |
| `/trader-entry` | Attendre la clôture d'une bougie pour confirmer un déclenchement. |
| `/trader-exit` | Définir le stop, l'objectif et l'heure de sortie avant l'achat. |
| `/trader-timemachine` | Simuler 10 000 fins de séance et comparer avec les séances historiques. |
| `/trader-budget` | Calculer le nombre d'actions selon ton budget et ton risque maximal. |
| `/trader-risk` | Vérifier chaque proposition et la bloquer si elle dépasse tes règles. |
| `/trader-broker` | Préparer un ticket pour le courtier et demander ton accord pour cet ordre précis. |
| `/trader-alerts` | Signaler un seuil de prix, un stop, un objectif ou l'heure de clôturer. |
| `/trader-analyst` | Lire les résultats publiés auprès de la SEC et expliquer ce qui a changé. |
| `/trader-pelosi` | Lire les déclarations publiques de transactions des membres du Congrès américain. |

## Périmètre

- **Marchés américains.** La traduction ne transforme pas les outils en scanner Euronext, en outil pour le CAC 40 ou en gestionnaire de PEA.
- **Dollars américains.** Les budgets, prix et seuils restent en USD. Aucune conversion automatique en euros.
- **Heure de New York.** Les commandes utilisent cette heure, avec le changement d'heure intégré. Demande une conversion vers ton fuseau si nécessaire ; ne suppose pas un décalage fixe avec Paris.
- **Simulation par défaut.** Aucun ordre réel n'est envoyé par l'installation ou les tests. Un courtier, son compte et ses autorisations sont nécessaires pour aller jusqu'à un ordre.
- **Données gratuites et non officielles.** Les données Yahoo peuvent être retardées, indisponibles ou limitées. Le scanner ne lit pas chaque transaction en temps réel.

Les outils de données n'imposent ni inscription chez Dan AI Lab ni clé d'API de données payante. L'utilisation de Claude, l'accès au courtier et leurs éventuels frais restent distincts. Les outils SEC demandent un User-Agent qui t'identifie auprès de la SEC.

## Installation dans Claude Code

```text
/plugin marketplace add dan-ai-lab/day-trader-fr
/plugin install day-trader-fr@day-trader-fr
```

Les commandes portent alors le préfixe du plugin : `/day-trader-fr:trader-scanner`, `/day-trader-fr:trader-news`, etc.

Pour une importation dans les réglages de skills de Claude, télécharge le ZIP du skill souhaité depuis [les versions publiées](https://github.com/dan-ai-lab/day-trader-fr/releases). Chaque archive contient un seul dossier de skill, son script et sa licence. Le ZIP `day-trader-fr.zip` contient le dépôt complet pour une installation locale, pas un skill unique à importer.

Pour garder les commandes courtes, installe les dossiers comme skills personnels :

```bash
git clone https://github.com/dan-ai-lab/day-trader-fr.git
mkdir -p ~/.claude/skills
cp -R day-trader-fr/trader-* ~/.claude/skills/
```

Tu peux aussi copier ces dossiers dans `.claude/skills/` à la racine de ton projet. Si tu utilises déjà la version anglaise avec ces mêmes noms, choisis le plugin avec son préfixe ou sauvegarde les dossiers existants avant de les remplacer.

Les scripts nécessitent Python 3.8 ou plus récent et utilisent uniquement sa bibliothèque standard. Pour importer un skill dans Claude via un ZIP, le dossier du skill avec son `SKILL.md` doit être à la racine du ZIP ; le ZIP du dépôt entier est destiné à l'installation locale. Sans exécution Python, coller un `SKILL.md` dans une conversation donne la méthode, mais pas les outils ni leurs calculs.

Pour la SEC, renseigne toi-même ton nom et ton email dans `trader/config.json` :

```json
{"sec_user_agent": "Ton Nom toi@example.com"}
```

Ou utilise la variable `SEC_USER_AGENT`. Cette valeur accompagne les requêtes envoyées à la SEC. Les identifiants de courtage restent dans les variables d'environnement ou la configuration locale de Claude Desktop, jamais dans la conversation ni dans un dépôt Git.

## Première utilisation

```text
/trader-scanner
Analyse TSLA, NVDA et AMD. Réponds en français et indique l'heure et les limites des données.
```

Le chemin complet pour un trade :

```text
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker
alerts : stop, objectif et heure de sortie pendant la position
news / analyst / pelosi : vérifications ponctuelles ou surveillance demandée
```

Le scanner produit une liste de graphiques qui correspondent à des règles. Tu choisis celui à examiner. Le plan fixe ensuite l'entrée, le stop, l'objectif et l'heure de sortie. La simulation précède le calcul de taille, puis le contrôle du risque.

Avant de préparer un ordre, `/trader-budget` te demande ton budget et ta perte maximale par trade. Les valeurs de `config.example.json` sont des exemples, pas des limites recommandées pour ta situation.

## Exemple reproductible repris du projet d'origine

Les fichiers de test conservent les données de l'exemple TSLA du 19 octobre 2026. Ce n'est pas une recommandation actuelle ni un résultat personnel de Dan AI Lab.

1. Le scan d'exemple trouve 42 cassures parmi 231 graphiques utilisables. TSLA clôture à 364,18 USD à 10 h 15, au-dessus de sa plage d'ouverture 354,47–362,18.
2. L'entrée est confirmée à la clôture de la bougie de 10 h 10, donc à 10 h 15, heure de New York.
3. Le plan d'exemple fixe le stop à 358,32 USD, l'objectif à 370,04 USD, soit 1R, et la sortie au plus tard à 15 h 55.
4. Avec la graine 19, les 10 000 simulations donnent : objectif atteint en premier 29,4 %, stop en premier 25,5 %, ni l'un ni l'autre 45,1 %. Sur 59 séances réelles, la même règle se déclenche 33 fois : 13 objectifs, 15 stops et 5 cas restants. Le résultat simulé est proche d'un pile ou face.
5. Avec le budget d'exemple de 5 000 USD et 50 USD de risque maximal, le calcul donne 8 actions pour 2 913,44 USD. La perte au prix du stop serait de 46,88 USD ; une exécution moins favorable peut coûter davantage.
6. `/trader-risk` rend `PASS` ou `BLOCK`. Un `PASS` ne constitue pas ton accord.
7. `/trader-broker` présente un seul ticket. Tu réponds `oui` pour ce ticket, puis tu valides séparément la demande du connecteur. L'environnement de simulation reste le choix par défaut.

## Commandes des outils

Les noms de commandes, clés JSON, statuts et nombres dans le code ne sont pas traduits. Utilise un point décimal dans les commandes et fichiers JSON.

```bash
python3 trader-scanner/scan.py universe
python3 trader-scanner/scan.py daily
python3 trader-scanner/scan.py orb --at 10:15
python3 trader-news/news.py --tickers TSLA --hours 12
python3 trader-entry/entry.py check TSLA --setup orb
python3 trader-entry/entry.py watch TSLA --every 30
python3 trader-exit/exit.py plan --stop or-mid --target 1R --write
python3 trader-timemachine/timemachine.py run --write
python3 trader-budget/size.py --write
python3 trader-risk/check.py
python3 trader-broker/ticket.py show
python3 trader-alerts/alerts.py add --from-plan
python3 trader-alerts/alerts.py check
python3 trader-analyst/facts.py TSLA
python3 trader-pelosi/ptr.py index --member pelosi
```

Les commandes sans `--now` ni `--offline` peuvent consulter le réseau et écrire dans `trader/`. Pour tester sans données courantes ni courtier, lance uniquement la suite hors ligne :

```bash
python3 -m unittest discover -s tests -v
```

Validation de cette version : **318 tests hors ligne réussis**, sans connexion à un courtier ni ordre réel. Les fixtures d'origine couvrent les cours, les actualités, les déclarations du Congrès et les données SEC. Les tests de cette adaptation vérifient aussi que `oui` est accepté pour un seul ordre et que les réponses françaises conditionnelles ou collectives sont refusées.

## Avant d'aller jusqu'au courtier

Seul `/trader-broker` peut conduire à un appel d'ordre, via une intégration externe. Son propre script `ticket.py` ne se connecte jamais au courtier. Chaque ordre doit réunir ces trois conditions :

1. `/trader-risk` a validé **exactement ce ticket aujourd'hui**.
2. Tu as donné un **oui explicite pour cet ordre uniquement** dans la conversation.
3. Tu as confirmé la demande du connecteur, configuré sur **Needs approval**, avec **Allow once / Deny** dans l'interface anglaise de Claude.

Le mot `oui` seul, avec éventuellement un point ou un point d'exclamation, est accepté. « Oui à tout », « oui si… », « oui mais… » et « vas-y » ne sont pas acceptés. Le journal conserve ta réponse originale. Les réponses anglaises prises en charge par le projet d'origine restent disponibles. Aucun ordre ne part d'une surveillance en arrière-plan ou d'une tâche planifiée.

Les instructions de connexion Alpaca et Interactive Brokers sont dans [trader-broker/SKILL.md](trader-broker/SKILL.md). Vérifie directement auprès du courtier sa disponibilité dans ton pays, tes autorisations et ses conditions actuelles. Le skill ne vérifie pas ton éligibilité.

## Limites à connaître

Ce projet fournit des outils et des explications, pas un conseil financier personnalisé. Il ne garantit ni bénéfice ni prix d'exécution. Le stop est un plan, pas une garantie contre un gap ou un mouvement rapide. Le risque affiché est calculé au prix du stop.

Les 10 000 simulations rééchantillonnent les bougies récentes ; elles ne couvrent pas tous les futurs possibles. Les probabilités sont celles du modèle, pas une prévision. Le calendrier intégré couvre les jours fériés et clôtures anticipées NYSE de 2026 et 2027 ; pour les autres années, le logiciel signale que la liste est inconnue.

Les options, la marge, le levier et la vente à découvert sont désactivés par défaut. Les outils d'entrée, de sortie et de taille de ce pack ne planifient que des positions longues. L'option technique `pdt_guard` conserve le contrôle historique de 3 day trades sur 5 jours ouvrés ; demande à ton courtier quelles règles s'appliquent réellement à ton compte avant de l'activer. Les règles fiscales et les conditions d'accès varient selon ta situation et ne sont pas traitées par cette traduction.

Les déclarations du Congrès américain sont publiques et peuvent être publiées plusieurs semaines après la transaction. Les lire rapidement ne donne pas d'information privilégiée.

## Provenance et licence

- Auteur du projet d'origine : **Jake Schincariol**, [OpusJake](https://opusjake.ai).
- Source : [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill).
- Adaptation française : **Dan AI Lab**.
- Version française : **2.0.0-fr.1**. Commit source : [`3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd`](https://github.com/Jakeschincariol/day-trader-skill/commit/3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd).
- [Licence MIT d'origine](LICENSE), conservée intégralement en anglais. La présente adaptation ne revendique pas la création du moteur d'origine.
