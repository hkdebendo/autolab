# Règles pour les agents de code (Claude Code, Muse Code)

Lis **SPEC.md** avant toute modification. Il contient l'architecture, le contrat de chaque module et les paramètres déjà validés par des tests.

## Règles absolues
1. **Aucune clé API dans le code, les notebooks, les tests ou les logs.** Tout passe par `.env` (ignoré par Git) et `autolab/config.py`. Le dépôt est public.
   - **Ne jamais demander la valeur d'une clé, ni l'afficher, ni l'écrire dans un fichier autre que `.env`.** Le propriétaire remplit lui-même `.env` à partir de `.env.example`.
   - Vérifier seulement la **présence** d'une clé. Si une clé nécessaire manque : s'arrêter et indiquer son nom et le fichier à compléter (`.env`). Les tests qui en ont besoin sont **ignorés** (`pytest.skip`) avec un message clair, sans échouer.
2. **Seul `autolab/sim/uma.py` importe `fairchem`.** Le reste du code passe par `autolab/sim/backend.py`.
3. **UMA ne tourne jamais sur le PC de développement** (pas de GPU NVIDIA, connexion lente). Les tests UMA portent le marqueur `@pytest.mark.gpu` et tournent sur Colab ; en local, ils sont ignorés.
4. **Ne jamais mélanger énergies UMA et énergies Materials Project** dans une même enveloppe convexe.
5. **Les seuils scientifiques sont dans `config.py`**, jamais dans les prompts écrits par le modèle ni en dur dans le code.
6. **Ne pas changer un paramètre marqué ✅ dans SPEC.md** sans le signaler et sans relancer le test de vérité correspondant.
7. Un module n'est terminé que si son **test de vérité** (SPEC.md, section 7) passe.
8. Ne pas inventer de fonctions pymatgen, fairchem ou alignn : en cas de doute, vérifier la signature (`inspect.signature`) ou la documentation installée.

## Budget : ne jamais gaspiller les crédits ni la connexion
Les ressources du projet sont limitées et ne se rechargent pas pendant le hackathon :

| Ressource | Limite |
|---|---|
| Baseten (Muse Spark Open) | 100 $ au total, 2 M tokens/min |
| Meta Model API (Muse Spark) | 150 $ au total (reçus ; carte bancaire enregistrée : tout dépassement est facturé) |
| Modal (GPU) | 100 $ au total (reçus) : chaque minute de GPU est facturée |
| Fireworks (Muse Glimmer) | 100 $ au total (reçus) |
| Materials Project | gratuit mais limité en nombre de requêtes |
| Connexion Internet du PC | très lente (~50 Ko/s) |
| GPU gratuits Colab/Kaggle | sessions limitées dans le temps |

Règles :
1. **Les tests n'appellent jamais une API payante par défaut.** Les réponses des modèles de langage sont simulées (mocks) dans les tests ordinaires. Les tests qui font de vrais appels portent le marqueur `@pytest.mark.api` et ne sont lancés que sur demande explicite du propriétaire.
2. **Demander avant toute exécution qui consomme des crédits** : appel réel à Baseten ou Meta, boucle complète, déploiement ou calcul sur Modal. Annoncer d'abord le nombre d'appels prévu et le coût estimé.
3. **Toute boucle a une limite stricte**, définie dans `config.py` : nombre maximal d'itérations, de candidats par itération, d'appels au modèle et de tokens par exécution. Valeurs par défaut petites (ex. 2 itérations, 5 candidats). Un dépassement arrête l'exécution proprement, sans réessayer.
4. **Aucune nouvelle tentative automatique illimitée** : 3 essais maximum pour une réponse JSON mal formée, puis échec explicite. En cas d'erreur de quota, de paiement ou de limite de débit, s'arrêter et le signaler, ne pas relancer en boucle.
5. **Compter et journaliser la consommation** : tokens de chaque appel (`response.usage`), cumul par exécution, affiché en fin d'exécution.
6. **Mettre en cache tout ce qui est coûteux** : références Materials Project, relaxations UMA, band gaps, réponses déjà obtenues. Ne jamais refaire un calcul ou un appel dont le résultat est déjà en cache.
7. **Materials Project** : regrouper les requêtes, ne demander que les champs utiles, réutiliser le cache disque.
8. **Pas de téléchargement lourd sur le PC** : ni checkpoint UMA, ni gros jeux de données. Les modèles ALIGNN sont téléchargés une seule fois puis réutilisés depuis le cache.
9. Ne jamais lancer de processus en arrière-plan qui appelle une API ou un GPU sans surveillance.
10. **Modal** : chaque fonction GPU a un `timeout` court adapté à sa tâche ; aucun conteneur gardé allumé en permanence (pas de `min_containers` / `keep_warm` sauf demande explicite) ; choisir le GPU le moins cher qui suffit ; le checkpoint UMA est stocké dans un volume Modal et jamais retéléchargé ; tester d'abord sur une seule petite structure avant de lancer un lot.

## Expliquer au fur et à mesure
Le propriétaire veut comprendre le projet au fil du travail, pas seulement recevoir du code.
- **Avant chaque étape**, dire en une ou deux phrases simples, en français, ce qui va être fait et pourquoi (ex. « Je crée le module qui vérifie que chaque candidat est électriquement neutre, pour éviter de calculer des cristaux impossibles. »).
- **Après chaque étape**, résumer en langage simple ce qui a été construit, le résultat des tests (avec les chiffres obtenus face aux valeurs attendues) et ce qui vient ensuite.
- Expliquer les notions scientifiques ou techniques avec des mots simples et, si utile, une analogie du quotidien ; éviter le jargon non expliqué.
- Signaler clairement, et tout de suite, ce qui ne marche pas ou ce qui surprend, au lieu de le contourner en silence.
- Rester bref : quelques phrases claires valent mieux qu'un long rapport.

## Style
- Python 3.12, type hints, docstrings courtes en anglais, noms de code en anglais.
- Fonctions pures autant que possible : entrée structure → sortie dictionnaire sérialisable en JSON.
- Chaque étape de l'entonnoir émet un événement (`agent/events.py`).
- Masquer les avertissements connus et sans importance (scipy « logm result may be inaccurate », messages répétitifs d'ALIGNN).

## Commits
- Petits commits fréquents, messages clairs : ils prouvent au jury que le travail date du hackathon.
- Mentionner dans les messages de commit les parties écrites avec Muse Code.
- **Claude ne doit jamais apparaître comme contributeur du dépôt sur GitHub.** Ne jamais ajouter de ligne `Co-Authored-By: Claude …` ni de mention « Generated with Claude Code » dans les commits ou les pull requests, et ne jamais configurer Git avec un nom ou une adresse e-mail de Claude ou d'Anthropic. Les commits portent uniquement l'identité Git du propriétaire du dépôt.
