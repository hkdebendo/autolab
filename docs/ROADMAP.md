# AutoLab roadmap (owner's plan, 2026-10-29)

Soumission : mercredi 4 nov. 21h00 ET (jeudi 5 nov. 3h00 au Bénin). Dépôt : https://github.com/hkdebendo/autolab.

**Étape 1** : exécution réelle validée (1 itération, 3 candidats, --novelty). Règle de la charpente : même critère que la calibration (élément non-Li > 5 % du Li → écarté, motif affiché). Confiance réduite pour les polysulfures : seulement pour la décomposition de l'électrolyte (fenêtre), pas pour l'interface cathode (FeS2 = information). Enregistrer tous les événements pour le mode rejeu.

**Étape 2** : benchmark de validation. Faire passer dans l'entonnoir des électrolytes connus, bons (Li6PS5Cl, Li10GeP2S12, Li7P3S11, Li3PS4) et mauvais (instables ou conducteurs électroniques connus), sans les montrer comme tels au modèle. Mesurer combien de bons passent et combien de mauvais sont écartés. Résultat honnête dans le rapport, même s'il est mauvais.

**Étape 3** : une exécution plus large (2 à 3 itérations, 5 candidats), dans les budgets. Elle devient l'exécution de référence de la démo, enregistrée pour le rejeu.

**Étape 4** : écrire docs/MUSE_CODE_TASKS.md pour Muse Code : interface web (FastAPI + frontend simple dans web/), mode rejeu de l'exécution de référence (événements affichés au fil de l'eau : propositions de Muse Spark, entonnoir, chiffres, classement, nouveauté), mode direct désactivé par défaut, déploiement Render. Muse Code ne touche pas à autolab/. Prévenir dans PROGRESS.md quand ce fichier est prêt : le propriétaire lancera Muse Code. Pendant ce temps, ne pas modifier web/.

**Étape 5** : README final (but, résultats honnêtes avec chiffres, tests de vérité dont les échecs, architecture, coûts, comment rejouer), schéma de l'architecture, retrait de « cobalt-free » s'il n'est pas implémenté.

**Étape 6** : script de la vidéo de 3 min dans docs/VIDEO_SCRIPT.md (problème, agent en action via le rejeu, résultats, honnêteté scientifique, suite).

**Étape 7**, seulement si les étapes 1 à 6 sont finies avant le samedi 31 oct. midi : cathodes sans cobalt comme second domaine (tension, capacité, stabilité), avec leurs propres tests de vérité. Sinon, elles restent une perspective dans le README et la vidéo.

**Finitions**, seulement à la fin : voix (Muse Voice Transcribe), Muse Glimmer via Fireworks (avec l'accord du propriétaire).

## Règles de travail (2026-10-29)

- Travail en autonomie jusqu'à la fin du projet.
- Budgets approuvés d'avance : Modal jusqu'à 15 $ au total (limite du compte : 20 $), une exécution de plus de 3 $ autorisée si annoncée dans le journal ; Meta (Muse Spark + recherche web) jusqu'à 20 $ au total ; Baseten et Fireworks : rien sans accord ; pousser sur GitHub autorisé si tous les tests passent.
- S'arrêter seulement si : un budget serait dépassé ; erreur de paiement ou de quota ; action irréversible (supprimer des résultats, réécrire l'historique Git) ; un test de vérité scientifique échoue sans règle écrite qui dise quoi faire.
- Sinon : option la plus raisonnable et la plus prudente, notée dans docs/DECISIONS.md (date, question, choix, raison).
- Rapports : 5 lignes maximum par étape dans docs/PROGRESS.md (fait, chiffres clés, coût, suivant).

## Production (owner's direction, 2026-10-29)

- The link is sent to the jury only (not published). The jury must be able to watch the agents work.
- Natural-language request in the web interface, 100 % autonomous loop (Muse Spark via the Meta API, Muse Spark Open via Baseten, Muse Glimmer via Fireworks once deployed with the owner's approval), replay mode and everything else.
- Everything that cannot run on Render free, or carries a risk (keys, spending, long jobs), moves to Modal: the whole agent loop runs in a Modal function (CPU orchestration, ALIGNN, pymatgen; UMA and MD on Modal GPUs), keys in Modal secrets created by the owner, caches in a Modal volume seeded with everything already computed, events written as they happen and streamed by Render.
- Cache first: a request already answered replays its whole workflow at a visible pace (reasoning shown), with no new computation and no paid call (model replies cached by their exact question); a request not in cache triggers the agents for real, every computation already done still coming from the cache.
- Protections: jury access code (set by the owner), one live run at a time, per-run caps, a total production cap.
- Order: after step 3, build the production backend (autolab/ and modal_app/, by Claude), then hand the web part to Muse Code (docs/MUSE_CODE_TASKS.md, updated with the live API).
