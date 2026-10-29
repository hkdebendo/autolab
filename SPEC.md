# AutoLab — Cahier des charges technique

> Version du 27 octobre 2026, fin du J1. Ce document décrit **ce qu'il faut construire** et **tout ce qui a déjà été validé** par des tests sur Google Colab. Les paramètres marqués ✅ ont été mesurés : ne pas les changer sans raison.

---

## 1. Le produit en une phrase

AutoLab est un agent IA qui cherche de nouveaux **électrolytes solides pour batteries au lithium métal** : un modèle de langage Meta propose des substitutions chimiques, le code fabrique les cristaux, UMA (Meta FAIR) les simule, des filtres scientifiques les trient, et le modèle lit les résultats pour proposer la suite.

Hackathon : Meta Global AI Developer Hackathon, piste « Push the Frontier », catégorie Indie (solo). Soumission avant le **mercredi 4 novembre 2026 à 21h00 ET** (jeudi 5 novembre 3h00 au Bénin), avec une vidéo de 3 minutes. Tout le code doit être écrit pendant le hackathon, dans un dépôt **public**.

⚠️ Ne pas écrire « cobalt-free electrolytes » : un électrolyte ne contient pas de cobalt. Formulation correcte : « solid electrolytes for lithium-metal batteries ». Le « sans cobalt » ne peut concerner que les **cathodes** testées en face de l'électrolyte.

---

## 2. Où tourne quoi

| Élément | Où | Pourquoi |
|---|---|---|
| UMA (relaxation, énergies, dynamique moléculaire) | **GPU NVIDIA uniquement** : Modal (crédits reçus : 100 $) pour les tests, la production et la démo ; Colab/Kaggle en secours | Le PC (Ryzen 5, 8 Go RAM, GPU AMD) ne peut pas faire tourner UMA ; la connexion (~50 Ko/s) ne permet pas de télécharger le checkpoint de 2,33 Go |
| ALIGNN (band gap), pymatgen (enveloppe, électrodes), générateur | CPU, n'importe où | Calculs légers |
| Backend FastAPI + frontend | Un seul service Render | Orchestration, interface |
| Données (sessions, candidats, résultats, événements) | Supabase (PostgreSQL gratuit) | Plus tard ; un cache local suffit au début |
| Modèles de langage | API distantes (Meta, Baseten) | — |

**Conséquence pour le code :** le calcul UMA doit être derrière une interface interchangeable (`backend="local"` sur une machine GPU comme Colab, `backend="modal"` en production). Le reste du code ne doit jamais importer fairchem directement.

---

## 3. Structure du dépôt

```
autolab/
├── CLAUDE.md                 # règles pour les agents de code
├── SPEC.md                   # ce document
├── README.md
├── pyproject.toml            # paquet installable : pip install -e .
├── .env.example              # noms des variables, sans valeurs
├── .gitignore                # .env, caches, *.traj, checkpoints
├── autolab/
│   ├── config.py             # lecture du .env, seuils scientifiques
│   ├── chem/
│   │   ├── oxidation.py      # degrés d'oxydation, neutralité
│   │   ├── generator.py      # substitutions → structures candidates
│   │   └── checks.py         # détecteur de liaisons S–S
│   ├── data/
│   │   └── mp.py             # accès Materials Project + cache disque
│   ├── sim/
│   │   ├── uma.py            # fabrique de calculateurs UMA (seul fichier qui importe fairchem)
│   │   ├── relax.py          # relaxation
│   │   ├── md.py             # dynamique moléculaire
│   │   └── backend.py        # interface local / modal
│   ├── analysis/
│   │   ├── stability.py      # enveloppe convexe, E_hull, décomposition
│   │   ├── bandgap.py        # ALIGNN2
│   │   ├── electrodes.py     # fenêtre, passivation, interface cathode
│   │   └── diffusion.py      # déplacement quadratique moyen, D
│   ├── llm/
│   │   ├── client.py         # client compatible OpenAI, fournisseur configurable
│   │   ├── prompts.py        # instructions système
│   │   └── schemas.py        # schémas JSON des réponses
│   ├── agent/
│   │   ├── pipeline.py       # entonnoir de filtres pour un candidat
│   │   ├── loop.py           # boucle hypothèse → évaluation → analyse
│   │   └── events.py         # événements streamés vers l'interface
│   └── store/
│       └── cache.py          # cache des relaxations et références (JSON/SQLite)
├── modal_app/                # plus tard : fonctions GPU déployées sur Modal
├── api/                      # plus tard : FastAPI
├── web/                      # plus tard : interface
├── tests/                    # tests de vérité (section 7)
├── scripts/
│   └── run_loop.py           # lance une boucle en ligne de commande
└── notebooks/                # notebooks de validation du J1
```

---

## 4. Variables d'environnement (`.env.example`)

```
MP_API_KEY=
HF_TOKEN=
BASETEN_API_KEY=
MODEL_API_KEY=            # Meta Model API (Muse Spark)
FIREWORKS_API_KEY=        # Fireworks (Muse Glimmer)
LLM_PROVIDER=meta         # meta | baseten
SIM_BACKEND=modal         # modal | local (local = machine avec GPU NVIDIA, ex. Colab)
```

**Modal** n'utilise pas le `.env` pour s'authentifier : la commande `modal token new` (à lancer une seule fois sur le PC) enregistre les identifiants dans `~/.modal.toml`. Le `HF_TOKEN` est ajouté dans les **Secrets Modal** (secret `huggingface-secret` contenant `HF_TOKEN`), pour que le checkpoint UMA soit téléchargé directement dans le cloud, jamais sur le PC.

Le fichier `.env` est dans `.gitignore` **dès le premier commit**. Aucune clé ne doit jamais apparaître dans le code, les notebooks, les logs ou le navigateur.

---

## 5. Modules : contrat et paramètres validés

### 5.1 `chem/oxidation.py` ✅
- Degrés d'oxydation fixés (uniquement des ions à couche fermée) :
  `Li+1, Na+1, Mg+2, Al+3, Si+4, Ge+4, Sn+4, P+5, As+5, Sb+5, S-2, Se-2, O-2, F-1, Cl-1, Br-1, I-1`.
- `charge_totale(structure) -> float`, `est_neutre(structure) -> bool` (somme des charges = 0).
- Un élément hors de cette table → candidat **rejeté** (règle chimique d'isolation électronique : pas de métaux de transition à valence variable comme Fe, Co, Ni, Mn, V, Ti³⁺).

### 5.2 `chem/generator.py` ✅
- Entrée : une structure parente (pymatgen) et une substitution au format :
  ```json
  {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}
  ```
  ou une substitution totale `{"remove": "P", "add": "Sb", "count": "all"}`.
- Substitution totale : `structure.replace_species({ancien: nouveau})`.
- Substitution partielle : remplacer `count` sites tirés au hasard, retirer `li_vacancies` Li tirés au hasard, générer **8 arrangements** (graine fixée), retirer les doublons avec `StructureMatcher().group_structures`.
- **Contrôle de neutralité avant tout calcul UMA** : un candidat non neutre est rejeté et l'événement est enregistré avec la raison.
- Sortie : liste de structures candidates + métadonnées (parent, substitution, graine).
- Résultat validé : S→Cl avec retrait d'un Li dans Li₃PS₄ (maille de 32 atomes) donne 7 arrangements distincts ; **26 meV/atome d'écart** entre le meilleur et le pire → il faut toujours relaxer plusieurs arrangements et garder le plus bas.
- Limite connue : la structure héritée du parent n'est pas forcément la plus stable (Li₃SbS₄ généré à 0,047 eV/atome alors qu'une autre structure existe dans MP). Prévoir plusieurs parents pour une même composition.

### 5.3 `chem/checks.py` ✅
- `a_liaisons_SS(atoms, rayon=2.3)` : vrai si deux S sont à moins de 2,3 Å (via `ase.neighborlist.neighbor_list`).
- **Ne s'applique qu'aux composés** (ignorer le soufre élémentaire, fait d'anneaux S₈).
- Si vrai : le résultat UMA est marqué « fiabilité réduite » (UMA se trompe sur les polysulfures : LiS₄ à 0,178 eV/atome avec UMA contre 0 dans MP).

### 5.4 `data/mp.py` ✅
- `MPRester(MP_API_KEY)`, `mpr.materials.summary.search(...)`.
- Références d'un système chimique : tous les sous-systèmes (combinaisons de 1 à n éléments), filtrés à **E_hull MP ≤ 0,05 eV/atome et ≤ 80 atomes**.
- Pour les électrodes : `mpr.get_entries_in_chemsys(elements, additional_criteria={"thermo_types": ["GGA_GGA+U"]})`.
- Cache disque obligatoire (par système chimique et par `material_id`).

### 5.5 `sim/uma.py` ✅ (seul fichier qui importe fairchem)
```python
from fairchem.core import pretrained_mlip, FAIRChemCalculator
predictor = pretrained_mlip.get_predict_unit(MODEL, device="cuda", inference_settings=...)
calc = FAIRChemCalculator(predictor, task_name="omat")   # tête « cristaux inorganiques »
```
- Modèle : `uma-s-1p2` (validé). `uma-s-1p2p1` (« nitro ») n'apporte rien sur T4, à retester sur GPU récent.
- **Haute précision** (`inference_settings="high-precision"`) pour les énergies et l'E_hull.
- **Précision normale** (réglage par défaut) pour la dynamique moléculaire : 2× plus rapide.
- Pour cribler des compositions différentes en série, UMA conseille `inference_settings="batch"` : **à vérifier** avant de l'utiliser.
- Accès au checkpoint : dépôt Hugging Face restreint `facebook/UMA`, `HF_TOKEN` en lecture.

### 5.6 `sim/relax.py` ✅
- ASE : `FIRE(FrechetCellFilter(atoms), logfile=None).run(fmax=0.05, steps=500)`.
- Retourne : énergie totale, énergie par atome, structure relaxée, convergence (bool), nombre d'étapes.
- Un candidat non convergé n'est jamais classé comme stable.
- Validation : LiCl relaxé à **5,145 Å** (expérimental ≈ 5,13 Å).

### 5.7 `analysis/stability.py` ✅
- **Toutes les énergies de l'enveloppe viennent d'UMA** (références MP relaxées par UMA). Ne **jamais** mélanger énergies UMA et énergies MP.
- `PDEntry(composition, energie, name=...)`, `PhaseDiagram(entries)`, `get_decomp_and_e_above_hull(entry, allow_negative=True)`.
- Sortie : E_hull (eV/atome), produits de décomposition avec fractions.
- Calibration Li-P-S : Li₃PS₄ 0,000 / 0,007 / 0,015 (MP : 0,000 / 0,007 / 0,014) ; Li₇P₃S₁₁ 0,010 (MP : 0,020) ; Li₂S 0.
- ⚠️ **Changement du 28 octobre 2026 (validé par le propriétaire)** : toutes les énergies UMA reçoivent les **corrections MP2020** (`config.UMA_MP2020`, `stability.uma_entry`), comme les énergies MP : corrections d'anions et mélange GGA/GGA+U (valeurs de U dans `config.MP2020_HUBBARD_U`). Sans elles, une interface où Co ou Fe passe d'un oxyde (GGA+U) à un sulfure (GGA) est faussée de ≈ 0,2 eV/atome. Chaque entrée reçoit sa **structure** (sulfure ou sulfate) et ses **états d'oxydation** devinés sans la limite de 20 atomes de pymatgen (sinon Se n'est pas corrigé dans Li₇P₃SeS₁₀). Un test vérifie que les atomes d'anion corrigés sont conservés entre chaque phase et ses produits (exception voulue : anion d'état formel entre −1 et 0, ex. Sb dans LiSb₃). Tests de vérité relancés : Li₂S 0,0 ; LiS fictif 0,445 ; Li₃PS₄ 0,0 ; écart moyen aux E_hull MP sur 52 phases Li-P-S 0,0091 → 0,0057 eV/atome ; polymorphes et Li₇P₃S₁₁ inchangés. Approximation connue du schéma : les polysulfures reçoivent la correction des sulfures, le soufre élémental aucune (déplace les candidats As et Sb).
- L'E_hull est toujours précisé **par atome** (eV/atome) ou **par substitution** (eV par site modifié) dans les rapports.
- Seuils : `E_hull ≤ 0,05` = fabricable (métastable acceptable) ; `≤ 0,025` = très bon.

### 5.8 `analysis/bandgap.py` ✅ (ALIGNN2, sans DGL, CPU)
```python
import os
import alignn.pretrained as ap
from jarvis.core.atoms import Atoms as JAtoms

def to_jarvis(s):
    return JAtoms(lattice_mat=s.lattice.matrix, coords=s.frac_coords,
                  elements=[str(sp.symbol) for sp in s.species], cartesian=False)

dossier = os.path.dirname(ap.get_alignn2_model(NOM)["best_model.pt"])
gap = ap.get_prediction_pure(model_name=dossier, atoms=to_jarvis(structure))[0]
```
- **Filtre** : `optb88vdw_bandgap_knn` (échelle PBE, écart moyen à MP 0,14 eV). Seuil **≥ 2,0 eV** (Li₆PS₅Cl, excellent électrolyte, n'est qu'à 2,19 eV sur cette échelle).
- **Valeur affichée** : `mbj_bandgap_knn` (plus proche de l'expérience : Si 1,18 eV).
- Si les deux modèles divergent sur « isolant oui/non » : signaler une confiance faible.
- Ne pas utiliser : `get_prediction` avec les anciens noms (KeyError), `mbj_bandgap_radius` (incohérent), modèles `snumat_Band_gap_HSE_*` (≈ 2,5 eV pour le lithium métal). MEGNet n'existe plus dans matgl 4.1.2.
- Rediriger la sortie standard pendant l'appel (messages répétitifs).

### 5.9 `analysis/electrodes.py` ✅ (méthode Zhu, He & Mo 2015)
- **Fenêtre électrochimique** : balayage de 0 à 5 V au pas de 0,02 V. À chaque tension V, `GrandPotentialPhaseDiagram(entries, {Li: mu_Li_metal - V})` et `GrandPotPDEntry(entry, {Li: mu})`. Le composé est stable à V si les **produits de décomposition sont exactement ceux de sa décomposition naturelle** (sans échange de Li). Ce critère fonctionne pour les composés métastables.
- **Passivation à 0 V** (contact avec le lithium métal) : lister les produits ; un produit est métallique si son gap MP est `< 0.1` (écrire `g is not None and g < 0.1`, **pas** `(g or 1) < 0.1`, qui rate les métaux).
  - pas de produit métallique → « passivante » ;
  - produit métallique mais force de réaction à 0 V < 0,1 eV/atome → « quasi stable » ;
  - produit métallique et force ≥ 0,1 → « non passivante » (rédhibitoire).
- **Interface avec une cathode** : `InterfacialReactivity(comp_electrolyte, comp_cathode, pd, norm=True, use_hull_energy=True)`, minimum de `get_kinks()`.
- Cathodes : la liste doit être configurable. Validé avec LiCoO₂ ; pour le récit « sans cobalt », utiliser par défaut **LiFePO₄** et **LiMn₂O₄** (non encore testées).
- Validé avec les énergies MP : Li₃PS₄ 1,72-2,34 V (publié 1,71-2,31), Li₆PS₅Cl 1,72-2,14 (1,71-2,01), LGPS 1,72-2,28 (1,71-2,14), LLZO 0,06-2,88 (0,05-2,91) ; LGPS non passivant (Li₁₅Ge₄), LLZO quasi stable (force 0,028), Li₃PS₄/LiCoO₂ −0,416 eV/atome.
- ✅ Même méthode avec les énergies UMA + MP2020 (28 octobre 2026) : fenêtre Li₃PS₄ 1,74-2,36 V (MP 1,72-2,34) ; interfaces avec les seules références sur l'enveloppe MP (`INTERFACE_REF_EHULL_MAX = 0`) : Li₃PS₄/LiCoO₂ −0,415 (MP −0,416), Li₃PS₄/LiFePO₄ −0,144 (MP −0,133) eV/atome, tolérance 0,05.
- Coût : fenêtre 4-8 s ; interface à 5 éléments 16-28 s (sans compter les relaxations). À réserver au **top 20**.

### 5.10 `sim/md.py` + `analysis/diffusion.py` ✅ (D par blocs validé par la calibration v2, 2026-10-29)
- Supercellule d'au moins ~10 Å de côté (`reps = ceil(10 / L)` par axe).
- Langevin NVT, pas de 1 fs, friction 0,01/fs. Utiliser `thermalize_momenta` (et non `MaxwellBoltzmannDistribution`) et `fixcm=False` avec `ase.constraints.FixCom`.
- Positions Li enregistrées tous les 10 pas ; trajectoire sauvegardée pour l'affichage 3D. Pour chaque autre élément (P, S, …), le déplacement quadratique moyen est enregistré à chaque image (`framework_msd`) : la charpente est intacte si chaque élément autre que Li diffuse à moins de 5 % du Li (`MD_FRAMEWORK_D_RATIO_MAX`).
- **Changement d'un paramètre ✅ (2026-10-29, validé par le propriétaire)** : D est désormais la **moyenne des D ajustés dans 4 blocs** consécutifs (`MD_D_BLOCKS`), avec, dans chaque bloc, le déplacement quadratique moyen moyenné sur de nombreux instants de départ (ajustement de L/8 à L/2) ; l'**erreur type** entre blocs donne l'incertitude (`D_sem_cm2_per_s`). L'ancien D (`((pos - pos[0])**2).sum(axis=2).mean(axis=1)`, pente / 6 sur la seconde moitié) reste calculé à côté (`D_one_origin_cm2_per_s`) pour comparaison. Raison : sur les runs de 20 ps à 1000 K (étape 9C), l'ancien D s'écartait jusqu'à 50 % de la moyenne par blocs (Li₃PS₄ : 9,5e-5 contre 6,2e-5 ± 0,4e-5 cm²/s).
- Un candidat est « à égalité » avec son parent si |D/D(parent) − 1| ≤ 2 erreurs propagées (`MD_TIE_SIGMA`).
- **Paramètres de tri ✅ (calibration v2)** : 600 K, 40 ps, 2 graines par structure, blocs des graines mis en commun (`MD_SCREEN_*`, `analysis.diffusion.pool`), sur Modal A10G (`MODAL_MD_GPU`, TF32 compilé : garder le même GPU pour les parents et les candidats). À 1000 K, les deux parents sont à égalité (deux graines) : 1000 K ne trie pas.
- Calibration (2026-10-29, Modal A10G) : test initial 600 + 700 K ❌ (1,9 σ et 0,4 σ) ; test v2, fixé avant les calculs, 600 K, 3 graines ✅ : D(Li₇P₃S₁₁) = 1,28e-5 ± 0,15e-5, D(Li₃PS₄) = 0,63e-5 ± 0,09e-5 cm²/s, rapport 2,04, 3,6 σ ; charpente P/S intacte (MSD final P ≤ 0,12 Å², S ≤ 0,24 Å²). Barrières 600–700 K : 0,19 ± 0,07 eV (Li₇P₃S₁₁, littérature 0,19) et 0,33 ± 0,09 eV (Li₃PS₄, littérature 0,35–0,41). Vitesse A10G : 18–24 ms/pas pour 84–128 atomes.
- **Test de vérité de ce changement : la calibration (plan A)**, sur les deux parents seulement : β-Li₃PS₄ (mp-985583, Pnma) et Li₇P₃S₁₁ (mp-641703), à 600 K / 40 ps, 700 K / 30 ps et 1000 K / 20 ps (autre graine) (`MD_CALIBRATION_*`, `scripts/md_calibration.py`). À 600 et 700 K, sous la transition β → α de Li₃PS₄ (~746 K) : charpente intacte, et D(Li₇P₃S₁₁) > D(Li₃PS₄) de plus de 2 erreurs combinées. Barrières d'Arrhenius comparées (sans seuil) aux simulations publiées : ~0,19 eV pour Li₇P₃S₁₁, 0,35–0,41 eV pour β-Li₃PS₄. À 1000 K, Li₃PS₄ peut légitimement rattraper Li₇P₃S₁₁ (barrière plus haute, phase α) : 1000 K n'est montré qu'à titre d'information.
- Vitesse mesurée sur T4, 128 atomes : 129 ms/pas en haute précision, **65 ms/pas en précision normale**. 50 ps ≈ 55 min sur T4.
- Kaggle T4 (torch 2.13, étape 9C, 20 ps à 1000 K) : 72–128 ms/pas pour 84–128 atomes, soit 0,56–1,16 ms par atome et par pas (les petites cellules sont plus lentes par atome) ; estimation retenue `KAGGLE_MD_MS_PER_ATOM_STEP = 1,2`.
- 2 ps ne suffisent pas pour un D fiable (Li₃PS₄ à 800 K : plateau à ~1 Å², pas de sauts). Pour la vraie mesure : 1000-1200 K, simulations plus longues, plusieurs températures en parallèle sur Modal. Réservé au **top 3 à 5**.

### 5.11 `llm/client.py` ✅
- Un seul client compatible OpenAI ; le fournisseur est choisi par `LLM_PROVIDER`.

| Fournisseur | base_url | modèle | rôle |
|---|---|---|---|
| `meta` ⏳ (crédits reçus, appel à valider) | `https://api.meta.ai/v1` | `muse-spark-1.3` | **cerveau principal** : hypothèses, décisions, analyse |
| `baseten` ✅ | `https://inference.baseten.co/v1` | `meta-models/muse-spark-open-1026` (seul nom accepté par la clé) | analyses en parallèle des candidats ; secours si Meta échoue |
| `fireworks` ⏳ (crédits reçus, appel à valider) | fournie par Fireworks | Muse Glimmer (nom exact à vérifier dans le catalogue Fireworks) | petites tâches rapides : validation de formules, conversion en JSON, résumés d'itération |

- Raisonnement Baseten : `message.reasoning_content` (≈ 11 s par réponse). Streaming : `stream=True`, champs `delta.reasoning_content` et `delta.content`.
- Muse Spark (Meta) : la Responses API permet de conserver le raisonnement d'un tour à l'autre avec `include=["reasoning.encrypted_content"]` ; le SDK OpenAI ne lit pas `MODEL_API_KEY` tout seul, passer `api_key` explicitement. À tester dès que les crédits arrivent.
- Compter les tokens de chaque appel (`response.usage`) dans un compteur global.
- Appels Baseten en parallèle pour analyser plusieurs candidats (limite : 2 M tokens/min ; budget : 100 $).

### 5.12 `llm/prompts.py` et `llm/schemas.py` ✅ (principes validés)
- Instructions système **en anglais**.
- Réponse **uniquement en JSON** ; côté code : retirer les balises ```` ```json ````, `json.loads`, vérifier les clés, jusqu'à **3 tentatives** en renvoyant l'erreur au modèle.
- **Les seuils viennent du code, pas du modèle** : les instructions les donnent explicitement (E_hull ≤ 0,05, gap optb88 ≥ 2,0, etc.).
- Chaque champ envoyé au modèle est expliqué dans les instructions (ex. `ss_bonds: true` = chaînes S–S, UMA moins fiable).
- Schéma de proposition (l'agent → le générateur) :
  ```json
  {"hypothesis": "short sentence",
   "proposals": [{"parent": "mp-985583",
                  "substitution": {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1},
                  "rationale": "short sentence"}]}
  ```
- Schéma d'analyse (après évaluation d'un lot) :
  ```json
  {"ranking": ["candidate_id", "..."],
   "lessons": ["short sentence"],
   "next_direction": "short sentence",
   "stop": false}
  ```

---

## 6. Le pipeline et la boucle

### 6.1 Entonnoir pour chaque candidat (`agent/pipeline.py`)
1. Règle chimique + neutralité (instantané) → rejet immédiat sinon.
2. Relaxation UMA haute précision de chaque arrangement, on garde le plus bas.
3. E_hull UMA ≤ 0,05 → sinon rejet (avec les produits de décomposition, utiles au modèle).
4. Band gap ALIGNN (optb88 ≥ 2,0) → sinon rejet.
5. Détecteur S–S → avertissement.
6. **Top 20** : fenêtre électrochimique, passivation, interface avec les cathodes.
7. **Top 3 à 5** : dynamique moléculaire sur GPU.
Chaque étape émet un **événement** (`events.py`) : `{"type", "candidate_id", "step", "data", "timestamp"}`, pour l'affichage en direct.

### 6.2 Boucle (`agent/loop.py`)
1. Le chercheur donne un objectif en langage naturel.
2. Le modèle reçoit l'objectif, les parents disponibles et l'historique → **propositions** (JSON).
3. Le générateur fabrique les candidats ; l'entonnoir les évalue.
4. Le modèle reçoit les résultats chiffrés → **analyse** (JSON) et nouvelle direction.
5. Arrêt après N itérations, sur budget, ou si `stop: true`.
6. Rapport final : candidats classés, chiffres, raisonnement de l'agent.

Version minimale (J3) : boucle séquentielle, `LLM_PROVIDER=meta` (Baseten en secours), UMA sur Modal, 2-3 itérations de 5-10 candidats, sans électrodes ni MD. Les étapes 6 et 7 s'ajoutent ensuite.

### 6.3 Ce que les résultats ne sont pas
Les candidats sont des **prédictions par calcul**, jamais des découvertes prouvées. Pas de calcul DFT dans le pipeline. La confiance repose sur la calibration sur des cas connus (section 7).

---

## 7. Tests de vérité (`tests/`)

Un module n'est terminé que si son test de vérité passe. Les tests UMA ne tournent que sur GPU (marqueur `@pytest.mark.gpu`).

| Test | Attendu |
|---|---|
| Relaxation LiCl (rocksalt, départ a = 5,0 Å) | 5,10 – 5,18 Å, convergé |
| E_hull Li₂S (système Li-S, énergies UMA) | ≤ 0,005 |
| E_hull LiS rocksalt fictif | ≥ 0,3 |
| Calibration Li₃PS₄ mp-985583 (système Li-P-S) | ≤ 0,01 |
| Fenêtre Li₃PS₄ (énergies UMA + MP2020, cache) | 1,6–1,9 V à 2,2–2,5 V |
| Interfaces Li₃PS₄/LiCoO₂ et Li₃PS₄/LiFePO₄ (UMA + MP2020 contre MP) | écart ≤ 0,05 eV/atome |
| Conservation des atomes d'anion corrigés (MP2020), chaque candidat et chaque phase du hull | aucun écart |
| Neutralité : S→Cl sans retrait de Li dans Li₁₂P₄S₁₆ | rejeté (charge +1) |
| Générateur S→Cl + 1 lacune Li | ≥ 2 arrangements distincts, tous neutres |
| Band gap optb88 : Li métal / Li₂S / LiCl | < 0,3 / > 3,0 / > 5,5 |
| Fenêtre Li₃PS₄ (énergies MP) | 1,6–1,9 V à 2,2–2,5 V |
| Passivation LGPS | non passivante (Li₁₅Ge₄) |
| Passivation LLZO | quasi stable |
| Détecteur S–S sur Li₂S / LiS₄ | faux / vrai |
| Client LLM : réponse JSON valide | clés présentes après ≤ 3 essais |
| Calibration de la dynamique moléculaire (plan A, D par blocs) : Li₇P₃S₁₁ contre β-Li₃PS₄ à 600 et 700 K ❌ (2026-10-29, Modal A10G : charpente intacte, bon sens aux deux températures mais 1,9 σ à 600 K et 0,4 σ à 700 K ; barrières 0,19 ± 0,07 et 0,33 ± 0,09 eV) | charpente P/S intacte ; D(Li₇P₃S₁₁) > D(Li₃PS₄) de plus de 2 erreurs combinées |
| Calibration v2 de la dynamique moléculaire (fixée le 2026-10-29, avant les calculs) : 600 K seulement, 3 graines de 40 ps combinées (graines 0, 1, 2 ; la graine 0 est le run du plan A). D combiné = moyenne des 12 blocs (4 par graine), erreur = écart type des blocs / √12. Justification : 700 K est trop proche de la transition β→α de Li₃PS₄ (746 K), connue avant les calculs. Si réussi : D par blocs ✅ et tri à 600 K, 2 graines, 40 ps ; si échoué : la dynamique moléculaire UMA reste une information secondaire, sans pouvoir éliminer un candidat ✅ (réussi : rapport 2,04, 3,6 σ, charpente intacte) | charpente P/S intacte ; D(Li₇P₃S₁₁) > D(Li₃PS₄) avec un écart supérieur à 2 erreurs combinées |

---

## 8. Ordre de construction

1. Squelette du dépôt, `pyproject.toml`, `.gitignore`, `.env.example`, `config.py`.
2. `chem/` + tests (CPU).
3. `data/mp.py` + cache (CPU).
4. `analysis/bandgap.py` + tests (CPU).
5. `analysis/stability.py` et `analysis/electrodes.py` avec énergies MP + tests (CPU).
6. `sim/` (uma, relax, md) + `modal_app/` : fonctions GPU sur Modal, checkpoint UMA stocké dans un **volume Modal** (téléchargé une seule fois), tests de vérité UMA lancés sur Modal. Commencer par le GPU le moins cher qui convient, mesurer le temps par relaxation et par pas de dynamique, et retester `uma-s-1p2p1` (nitro) sur un GPU récent.
7. `llm/` : client à trois fournisseurs. Premier test réel avec Muse Spark (Meta) : un appel, une réponse JSON, le raisonnement en streaming. Puis Baseten (déjà validé), puis Fireworks.
8. `agent/pipeline.py` puis `agent/loop.py` + `scripts/run_loop.py` → **première boucle complète** (UMA sur Modal).
9. Électrodes avec énergies UMA.
10. `api/`, `web/`, mode « rejeu ».

---

## 9. Plus tard (hors périmètre de cette nuit)

- Benchmark de redécouverte : cacher Li₆PS₅Cl, LGPS, LLZO, Li₃PS₄ ; comparer l'agent à une recherche aléatoire et à une heuristique, à budget UMA égal, sur plusieurs graines ; ablation avec et sans résultats UMA.
- Interface web (FastAPI + Render, Supabase), visualisation 3D de la dynamique moléculaire (3Dmol.js ou NGL), **mode « rejeu »** avec des résultats déjà calculés pour sécuriser la démo.
- Domaine suivant possible : cathodes sans cobalt (calibrer d'abord les tensions UMA sur LiFePO₄ ≈ 3,4 V, LiMn₂O₄ ≈ 4,0 V, LiNi₀.₅Mn₁.₅O₄ ≈ 4,7 V).
- Muse Code pour une partie visible du développement, à mentionner dans la soumission.
