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
| pymatgen (enveloppe, électrodes, règle des couches complètes), générateur | CPU, n'importe où | Calculs légers |
| GPAW (band gap DFT du champion) | Modal CPU (8 cœurs) | Quelques minutes par structure |
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
│   │   ├── bandgap.py        # règle des couches complètes, gap DFT (GPAW) du champion
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
- Si vrai : le résultat UMA est marqué « fiabilité réduite » (UMA brut se trompe sur les polysulfures : LiS₄ à 0,178 eV/atome au-dessus de l'enveloppe avec UMA contre 0 dans MP).
- ⚠️ Mesure du 2026-11-01 (`results/2026-11-01_uma_error_bars`) : **avec les corrections MP2020** (utilisées partout depuis le 28 octobre), l'énergie de décomposition de LiS₄ est −0,174 eV/atome contre −0,162 dans MP, et l'écart UMA + MP2020 / MP reste ≤ 0,0124 eV/atome sur 9 polysulfures connus. L'ancien chiffre (0,17) comparait UMA sans corrections.

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

### 5.8 `analysis/bandgap.py` ✅ (isolation électronique : règle + DFT du champion ; 2026-11-03)
Règle des organisateurs : tout modèle appelé à l'exécution doit être un modèle Meta. Les band gaps déjà enregistrés (champs `gap_optb88` / `gap_mbj`, cache `.cache/bandgap`) restent tels quels et sont affichés « recorded prediction ».
- **Dans l'entonnoir** (étape `bandgap`, instantané, aucun modèle) : chaque ion, à son état d'oxydation fixe, doit avoir une couche électronique complète : électrons restants Z − charge dans `CLOSED_SHELL_ELECTRONS` (gaz rare, d10, d10 s2, 4f14, 4f14 5d10). Les tables `OXIDATION_STATES` et `SODIUM_OXIDATION_STATES` ne contiennent que de tels ions : la règle garantit le principe, elle rejette rarement.
- **Après le classement** (étape `dft_gap`, `domains/electrolyte.py`) : band gap PBE du champion avec **GPAW** (ondes planes `DFT_GAP_ECUT_EV` = 400 eV, grille Γ de densité `DFT_GAP_KDENSITY` = 2,5 /Å pour le calcul auto-cohérent, puis bandes à densité fixe le long du chemin de haute symétrie, `DFT_GAP_PATH_POINTS` = 40 ; le gap est lu sur les deux ensembles de points k). Seuils inchangés, échelle PBE : `BANDGAP_MIN` = 2,0 eV (lithium), `SODIUM_BANDGAP_MIN` = 1,8 eV (sodium). Sous le seuil, le candidat est écarté et le suivant vérifié, au plus `DFT_GAP_MAX_CALCS` = 2 calculs par recherche ; une erreur arrête la vérification (champion « non confirmé »).
- Exécution : `modal_app/dft_app.py` (Modal CPU, 8 cœurs, 16 Go, délai `DFT_GAP_TIMEOUT_S`, aucun conteneur gardé allumé, aucune nouvelle tentative), lancé par MPI (`mpiexec -n 8 gpaw python`, GPAW 26.7.0 de conda-forge, version OpenMPI). Cache par structure et réglages (`.cache/dft_gap/pbe_gpaw.json`) : un calcul n'est jamais refait. Seul `autolab/sim/dft.py` importe GPAW.
- Grille seule : bords de bande entre deux points de la grille, gap surestimé (Li₃P +0,38 eV, Li₂S +0,28 eV) ; d'où le chemin de bandes.

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

### 5.10 `sim/md.py` + `analysis/diffusion.py` ✅ (D par blocs validé par la calibration v2, 2026-10-29 ; verdict candidat/parent par la différence |D − D(parent)| ≤ 2 erreurs combinées depuis le 2026-11-02, mêmes 39 verdicts qu'avec le rapport)
- Supercellule d'au moins ~10 Å de côté (`reps = ceil(10 / L)` par axe).
- Langevin NVT, pas de 1 fs, friction 0,01/fs. Utiliser `thermalize_momenta` (et non `MaxwellBoltzmannDistribution`) et `fixcm=False` avec `ase.constraints.FixCom`.
- Positions Li enregistrées tous les 10 pas ; trajectoire sauvegardée pour l'affichage 3D. Pour chaque autre élément (P, S, …), le déplacement quadratique moyen est enregistré à chaque image (`framework_msd`) : la charpente est intacte si chaque élément autre que Li diffuse à moins de 5 % du Li (`MD_FRAMEWORK_D_RATIO_MAX`).
- **Changement d'un paramètre ✅ (2026-10-29, validé par le propriétaire)** : D est désormais la **moyenne des D ajustés dans 4 blocs** consécutifs (`MD_D_BLOCKS`), avec, dans chaque bloc, le déplacement quadratique moyen moyenné sur de nombreux instants de départ (ajustement de L/8 à L/2) ; l'**erreur type** entre blocs donne l'incertitude (`D_sem_cm2_per_s`). L'ancien D (`((pos - pos[0])**2).sum(axis=2).mean(axis=1)`, pente / 6 sur la seconde moitié) reste calculé à côté (`D_one_origin_cm2_per_s`) pour comparaison. Raison : sur les runs de 20 ps à 1000 K (étape 9C), l'ancien D s'écartait jusqu'à 50 % de la moyenne par blocs (Li₃PS₄ : 9,5e-5 contre 6,2e-5 ± 0,4e-5 cm²/s).
- Un candidat est « à égalité » avec son parent si |D/D(parent) − 1| ≤ 2 erreurs propagées (`MD_TIE_SIGMA`).
- **Paramètres de tri ✅ (calibration v2)** : 600 K, 40 ps, 2 graines par structure, blocs des graines mis en commun (`MD_SCREEN_*`, `analysis.diffusion.pool`), sur Modal A10G (`MODAL_MD_GPU`, TF32 compilé : garder le même GPU pour les parents et les candidats). À 1000 K, les deux parents sont à égalité (deux graines) : 1000 K ne trie pas.
- ⚠️ **Changement d'un paramètre ✅ (2026-11-01, décision du propriétaire)** : la dynamique moléculaire passe sur **Modal H100** (`MODAL_MD_GPU`), environ 2 fois plus rapide et environ 2 fois plus chère par simulation. Les résultats déjà calculés sur A10G gardent leurs clés de cache (`MD_LEGACY_GPU`) et sont relus tels quels (parents compris : jamais recalculés) ; les nouvelles clés portent le nom de la carte (`sim.backend.md_settings`, `dynamics.with_md_gpu`). **Vérification (critère fixé avant les calculs, `scripts/md_gpu_check.py`, `results/2026-11-01_md_gpu_check`) ✅** : une simulation de 40 ps à 600 K par parent sur H100 contre la calibration v2 A10G (3 graines) : D(Li₇P₃S₁₁) 1,27e-5 ± 0,32e-5 contre 1,28e-5 ± 0,15e-5 (−0,0 σ), D(Li₃PS₄) 0,70e-5 ± 0,19e-5 contre 0,63e-5 ± 0,09e-5 (+0,4 σ), charpente intacte : **même D sur les deux cartes**, un candidat H100 peut être comparé à un parent A10G et la calibration v2 reste valable. Vitesse H100 mesurée : 14–17 ms/pas (1,3–1,7× plus rapide que l'A10G, et non 2×), soit 2,1–2,7× plus cher par simulation.
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
| `wonder` ✅ (2026-11-03) | `https://api.meta.ai/v1` (Responses API, résumé du raisonnement) | `muse-wonder-1.0` (4 $ / 20 $ par million de tokens en entrée / sortie) | **revue de campagne** (`agent/review.py`), dernière étape de chaque domaine |

**Revue de campagne (2026-11-03, propriétaire)** : après le rapport, Muse Wonder lit en une fois un dossier compact de toute la campagne (hypothèse et candidats de chaque tour avec leurs mesures, tests lents, analyses des échecs par Muse Spark, résumés des étapes, finalistes, littérature, rapport ; sans structures ni séries brutes ; taille ≤ `CAMPAIGN_REVIEW_MAX_INPUT_CHARS`, sinon les candidats des recherches antérieures sont retirés). Réponse JSON `campaign_review` : `headline`, `learned`, `worked`, `failed`, `next_campaign` {`goal`, `parents`, `directions`, `why`}. Un appel par recherche (client à part, plafond `LLM_COST_CAPS_USD["wonder"]`, `CAMPAIGN_REVIEW_MAX_OUTPUT_TOKENS`) ; elle ne décide rien (seuils, classement et verdicts restent ceux du code). Sans clé, l'étape est ignorée et l'indique. Événement `llm/campaign_review`, dernier message de la conversation (`review`), recopié quand une recherche connue est réutilisée. Les trois recherches de la page d'accueil l'ont reçue a posteriori (`scripts/add_campaign_review.py`, 0,26 $ au total).

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
4. Ions à couches complètes (règle, sans modèle) → sinon rejet ; le band gap DFT du champion (GPAW, ≥ 2,0 eV) est calculé après le classement.
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

**Boucle complète (2026-10-29)** : après les itérations, les étapes du domaine tournent dans l'ordre sur tous les candidats (ceux de l'exécution et, avec `--prior`, ceux des exécutions précédentes, jamais reproposés). Chaque étape lit les caches avant de calculer, émet ses événements (`stage` et `candidate`, étape `nom:sous-étape`) et décide selon `config.py` ; une étape arrêtée par un budget n'empêche pas les suivantes.
1. **Électrodes** (`ELECTRODES_TOP` premiers par E_hull par substitution) : fenêtre, passivation, puis interface avec `AGENT_CATHODES` (LiFePO₄) si la calibration Li₃PS₄/cathode est dans la tolérance. « Non passivant » → écarté (`ELECTRODE_EXCLUDED_PASSIVATION`, SPEC 5.9), sans calcul d'interface. Un polysulfure parmi les produits → confiance réduite des résultats d'électrode (information seulement : presque tous les sulfures donnent FeS₂ face à LiFePO₄). Un calcul qui dépasserait le budget de relaxations est sauté et signalé.
2. **Choix pour la dynamique moléculaire** : Muse Spark choisit au plus `MD_SELECT_MAX` candidats non écartés, à partir des comparaisons calculées par le code ; les identifiants hors liste sont ignorés ; sans réponse du modèle (budget), règle : meilleurs E_hull par substitution.
3. **Dynamique moléculaire** aux paramètres de tri ✅ (600 K, 2 graines de 40 ps, Modal H100 depuis le 2026-11-01, A10G avant ; même D sur les deux cartes), parents compris ; pas lancée si le coût estimé dépasse `MD_MAX_USD_PER_RUN`. Plus lent que le parent de plus de `MD_TIE_SIGMA` erreurs combinées (`MD_EXCLUDED_VERDICTS`) ou charpente déplacée → écarté pour la conduction, mais listé avec ses chiffres.
4. **Classement final** (depuis le 2026-11-02, voir « Conductivité à 300 K ») : niveau face au parent à 300 K, puis départage par convention (`RANK_TIE_BREAK`) ; les écartés en fin de liste avec leur motif ; `FINALISTS_MAX` finalistes.
5. **Nouveauté** (seulement avec `--novelty`) : témoin LGPS d'abord ; s'il n'est pas trouvé publié, la recherche n'est pas jugée fiable et les finalistes ne sont pas interrogés (`NOVELTY_STOP_IF_CONTROL_FAILS`) ; plafond `NOVELTY_COST_CAP_USD` ; réponses en cache.

**Boucle de rétroaction sur l'erreur (2026-11-01, décision du propriétaire, `FEEDBACK_LOOP`)** : les étapes 1 à 3 ci-dessus (électrodes, revues, choix pour la dynamique moléculaire, dynamique moléculaire) tournent aussi **dans chaque itération**, sur les candidats de l'itération : `ITERATION_MD_SELECT_MAX` = 1 candidat simulé par itération (choisi par Muse Spark), aucun nouveau après les itérations (`FINAL_MD_SELECT_MAX` = 0 ; les verdicts en cache s'appliquent toujours). Les résultats de ces tests lents (`domains.electrolyte.feedback`) — échecs au contact du lithium (produits, énergie), plus lent que le parent, charpente qui bouge (rapport de diffusion de chaque élément au Li, déplacement final) — sont donnés à Muse Spark avec leurs mesures, sous forme factuelle, avant l'analyse de l'itération ; il donne pour chaque échec une **hypothèse** sur la cause (étiquetée comme telle : le code n'a mesuré que les chiffres) et une **correction** (`failure_analysis`, facultative, vérifiée si donnée), reprises dans l'historique de la proposition suivante. Recherche en direct : 3 itérations, 1 candidat simulé par itération ; plafond de dynamique moléculaire sur toute la recherche (`MD_MAX_USD_PER_RUN` = 7 $). L'ancien déroulement reste possible (`FEEDBACK_LOOP = False`). Aucune itération n'est promise réussie.

**Conductivité à 300 K (2026-11-01)** : étape `conductivity` après le classement, sans calcul (cache seulement) : D des exécutions en cache jusqu'à `CONDUCTIVITY_FIT_T_MAX_K` (750 K, sous la transition β → α de Li₃PS₄), ajustement d'Arrhenius pondéré, extrapolation à 300 K, Nernst-Einstein (densité de Li de la maille relaxée, rapport de Haven 1), plage = une erreur type de l'extrapolation. Candidat à une seule température : énergie d'activation du parent, étiquetée. Températures supplémentaires (500 et 700 K) par `scripts/conductivity.py`. **Classement (2026-11-01, propriétaire)** : l'étape passe avant le classement ; un candidat ayant sa propre droite est « plus lent » ou « plus rapide » que son parent seulement si les deux plages ne se recouvrent pas, sinon « à égalité » (`CONDUCTIVITY_RANK_ORDER` : plus rapide > égalité > non ajusté > plus lent), critère placé avant le verdict à 600 K ; le rapport cite toujours les plages. **Règles complétées (2026-11-02, propriétaire)** : (1) les candidats sans droite propre forment un groupe à part, « non évalués à 300 K », après tous les candidats évalués (`CONDUCTIVITY_RANK_ORDER` = plus rapide > égalité > plus lent > non ajusté), ordonnés entre eux par leur verdict à 600 K ; ailleurs, la diffusion à 600 K n'est qu'un pré-filtre (« plus lent » écarte) ; (4) à l'intérieur d'un niveau, départage **par convention**, pas une différence significative (`RANK_TIE_BREAK`) : plus faible E_hull par substitution, puis plus faible énergie d'activation (droite propre), puis fenêtre la plus large (largeur nulle ou non calculée : 0 V) ; le classement donne les niveaux (`levels`) et le rapport le dit ; l'écart d'E_hull de chaque finaliste au champion est jugé par le code (dans ou hors de la somme des barres d'erreur) ; (5) la droite du parent qui sert à la comparaison est faite avec les mêmes exécutions que celle du candidat (`CONDUCTIVITY_PARENT_SAME_PROTOCOL` : mêmes températures, même nombre d'exécutions, mêmes durées et graines si elles sont en cache), les écarts restants sont listés (aujourd'hui : 700 K, 30 ps pour les parents contre 40 ps) ; la droite complète des parents reste celle du test de vérité. Non fait (coût) : σ(300 K) donnée à Muse Spark à chaque itération, deuxième graine à 500 et 700 K.

**Second domaine : cathodes sans cobalt (2026-11-02, propriétaire ; `domains/cathode.py`, `analysis/cathode.py`)** : substitutions dans quatre cathodes connues sans cobalt (`CATHODE_PARENTS` : LiFePO₄, LiMnPO₄, spinelle LiMn₂O₄, LiNi₀.₅Mn₁.₅O₄). Entonnoir : cobalt refusé et neutralité avec valence mixte (`CATHODE_OXIDATION_RANGES`, plages contiguës : neutre si 0 est entre les sommes des états bas et hauts ; oxygène fixé à −2, pas de redox de l'oxygène) → composition déjà dans MP non calculée → relaxation UMA de `CATHODE_N_ARRANGEMENTS` arrangements → E_hull contre les phases MP stables du système relaxées avec UMA (`CATHODE_HULL_REF_EHULL_MAX` = 0, jamais d'énergie MP), ≤ `CATHODE_EHULL_MAX` (0,08 eV/atome : le spinelle commercial LiMn₂O₄ est à 0,045 au-dessus de l'enveloppe MP) → retrait du Li permis par la neutralité, cellule chargée relaxée : tension moyenne V = −(E_lith − E_délith − k E_Li)/k (énergies UMA brutes ; les corrections MP2020 de O et des métaux de transition s'annulent), capacité théorique k F/(3,6 M), densité d'énergie, variation de volume ; filtres `CATHODE_VOLTAGE_MIN`–`MAX` (3,0–4,8 V), `CATHODE_CAPACITY_MIN` (120 mAh/g), `CATHODE_VOLUME_CHANGE_MAX` (10 %) ; chaque candidat comparé à son parent calculé de la même façon. Boucle pilotée par l'erreur : chaque échec, avec ses chiffres, revient au modèle (la boucle appelle `feedback` même sans tests lents). Après les itérations : revues Muse Spark Open, classement par densité d'énergie puis E_hull par substitution, rapport Muse Spark. Une demande cathode tourne dans ce domaine (service : domaine de la conversation), sans les candidats électrolytes. Un composé dont aucun Li ne peut sortir est refusé dès sa composition, avant toute simulation. Chaque E_hull porte sa barre d'erreur UMA/DFT, mesurée sur les phases stables du système (`cached_system_errors(..., ehull_max=0.0)`). Non calculé : profil de tension (seule la moyenne sur la charge complète), diffusion du Li dans la cathode, cyclage.

**Troisième domaine : électrolytes solides au sodium (2026-11-02, propriétaire ; `domains/sodium.py`)** : l'entonnoir et les tests lents des électrolytes au lithium, avec Na⁺ comme ion mobile (`MOBILE_IONS` : l'ion suivi par la dynamique moléculaire et retiré par les lacunes, `"vacancies"` dans une substitution, est le premier de cette liste présent dans le cristal). Parents (`SODIUM_PARENTS`) : Na₃PS₄ tétragonal (mp-28782), Na₃SbS₄ cubique (mp-10167), NASICON Na₃Zr₂Si₂PO₁₂ (mp-532695). Neutralité avec des états d'oxydation fixes (`SODIUM_OXIDATION_STATES`, Zr, Ti, Nb… ajoutés) → composition déjà dans MP non calculée → relaxation UMA → E_hull contre les phases MP stables du système relaxées avec UMA (`SODIUM_HULL_REF_EHULL_MAX` = 0), ≤ `SODIUM_EHULL_MAX` (0,05) → ions à couches complètes ; après le classement, band gap DFT (GPAW) du champion ≥ `SODIUM_BANDGAP_MIN` (1,8 eV : Na₃SbS₄, électrolyte qui fonctionne, a un gap PBE de 1,93 eV ; la limite lithium de 2,0 eV le rejetterait). Dans chaque tour : fenêtre en V vs Na/Na⁺ et réaction avec le sodium métal (potentiel chimique de Na métal ; non passivant → écarté), revue indépendante, choix d'un candidat par le modèle, diffusion de Na à 600 K contre son parent (2 graines × 40 ps), plafond `SODIUM_MD_MAX_USD`. Pas d'interface cathode (`SODIUM_CATHODES` vide : la calibration de l'interface n'existe que pour les cathodes au lithium). Après les tours : classement (verdict de diffusion, puis E_hull par substitution), vérification bibliographique (témoin Na₃PS₄), rapport. Pas de conductivité à 300 K. La dynamique moléculaire ne peut écarter ni classer un candidat que si sa calibration sodium a réussi (`SODIUM_MD_CAN_EXCLUDE`, réglage `md_ranks`, section 7) : la n° 1 (deux cristaux différents) a échoué, la n° 2 (un cristal contre son propre parent, ce que fait le domaine) a réussi avec le test par différence : elle écarte et classe. Les étapes partagées lisent les réglages du domaine (`Domain.settings` : ion, cathodes, prompts, plafond).

**Vue en direct de l'interface (2026-11-02, propriétaire)** : pendant une recherche, la page joue les événements un à un comme des cartes (qui travaille — Muse Spark, Muse Spark Open, Muse Glimmer, UMA, GPAW, pymatgen, Materials Project — et ce qu'il fait, avec ses chiffres), la liste « Progrès » se coche et un carnet note les décisions ; les cartes disparaissent, la carte Recherche, le résumé et le rapport final s'affichent à la fin. Les événements arrivent par WebSocket (`web/app.py`, `/ws/conversations/{id}`, interrogation de secours). L'événement de relaxation porte la structure avant et après relaxation du meilleur arrangement (`pipeline.live_structure`) et, pour les nouvelles relaxations, `RELAX_TRAJECTORY_FRAMES` (12) images du chemin réel (affichage seulement : le résultat ne change pas) ; sans chemin enregistré, l'animation entre les deux structures est indiquée comme interpolée. Les résultats repris du cache sont joués à un rythme lisible et marqués « reused ». Une demande identique à une recherche terminée la réutilise (`REUSE_IDENTICAL_GOAL`) : événements, résultat, dernier résumé, dernier rapport et fichiers 3D copiés, rien n'est recalculé ni payé, la conversation n'est pas une recherche en direct (source `reuse`). Les formules s'écrivent avec des indices (Li₇P₃S₁₁).

**Barres d'erreur UMA (2026-11-01)** : chaque E_hull est donnée avec l'écart moyen UMA + MP2020 / DFT (MP) mesuré sur les composés connus de son système (énergie de décomposition, composé retiré de l'enveloppe, deux enveloppes séparées ; `analysis/uma_errors.py`, `scripts/uma_error_bars.py`). **Fenêtre** : confiance réduite seulement si ses limites bougent de plus de `WINDOW_SENSITIVITY_MAX_V` (0,1 V) quand l'énergie de chaque polysulfure est décalée de ±`POLYSULFIDE_ENERGY_ERROR_EV` (0,025 eV/atome, 2 × la plus grande erreur mesurée sur 9 polysulfures).

**Domaines** (`autolab/domains/`) : la boucle est générique. Un domaine fournit l'entonnoir d'un candidat, les prompts, les champs vus par le modèle, les comparaisons, les étapes après les itérations et les seuils de `config.py` qu'il utilise (`AGENT_DOMAIN`). Trois domaines : `electrolyte` (lithium), `cathode` (cathodes sans cobalt), `sodium` (électrolytes au sodium) ; un nouveau domaine est un nouveau module de ce dossier, sans modifier la boucle.

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
| Band gap DFT GPAW (PBE) contre Materials Project : Li, Li₂S, LiI, Li₃P, Na₃SbS₄, Li₃PS₄ (2026-11-03, `results/2026-11-03_dft_gap_truth`) | écart ≤ 0,3 eV (métaux ≤ 0,1) : **6/6**, écart moyen 0,03 eV, maximum 0,08 (Na₃SbS₄) ; Li₃PS₄ (32 atomes) 7 min 18 s |
| Fenêtre Li₃PS₄ (énergies MP) | 1,6–1,9 V à 2,2–2,5 V |
| Passivation LGPS | non passivante (Li₁₅Ge₄) |
| Passivation LLZO | quasi stable |
| Détecteur S–S sur Li₂S / LiS₄ | faux / vrai |
| Client LLM : réponse JSON valide | clés présentes après ≤ 3 essais |
| Calibration de la dynamique moléculaire (plan A, D par blocs) : Li₇P₃S₁₁ contre β-Li₃PS₄ à 600 et 700 K ❌ (2026-10-29, Modal A10G : charpente intacte, bon sens aux deux températures mais 1,9 σ à 600 K et 0,4 σ à 700 K ; barrières 0,19 ± 0,07 et 0,33 ± 0,09 eV) | charpente P/S intacte ; D(Li₇P₃S₁₁) > D(Li₃PS₄) de plus de 2 erreurs combinées |
| Calibration v2 de la dynamique moléculaire (fixée le 2026-10-29, avant les calculs) : 600 K seulement, 3 graines de 40 ps combinées (graines 0, 1, 2 ; la graine 0 est le run du plan A). D combiné = moyenne des 12 blocs (4 par graine), erreur = écart type des blocs / √12. Justification : 700 K est trop proche de la transition β→α de Li₃PS₄ (746 K), connue avant les calculs. Si réussi : D par blocs ✅ et tri à 600 K, 2 graines, 40 ps ; si échoué : la dynamique moléculaire UMA reste une information secondaire, sans pouvoir éliminer un candidat ✅ (réussi : rapport 2,04, 3,6 σ, charpente intacte) | charpente P/S intacte ; D(Li₇P₃S₁₁) > D(Li₃PS₄) avec un écart supérieur à 2 erreurs combinées |
| Comparaison A10G / H100 de la dynamique moléculaire (2026-11-01, critère fixé avant : écart ≤ 2 erreurs combinées, charpente intacte, pour les deux parents ; `scripts/md_gpu_check.py`) ✅ | mesuré : Li₇P₃S₁₁ −0,0 σ, Li₃PS₄ +0,4 σ : même D |
| Conductivité à 300 K (2026-11-01, fixé avant les nouveaux calculs, `CONDUCTIVITY_REFERENCE_MS_CM`) : Li₇P₃S₁₁ > β-Li₃PS₄ et chacun à un facteur 10 près de l'expérience (3,2–17 et 0,16 mS/cm) | ✅ mesuré (500, 600, 700 K) : Li₇P₃S₁₁ 99,9 mS/cm (58–170), β-Li₃PS₄ 1,18 (0,43–3,2), ordre juste ; tous deux ~6–7 × au-dessus de l'expérience (cristal parfait) ; Ea 0,14 ± 0,03 et 0,34 ± 0,05 eV |
| Barres d'erreur UMA / DFT (2026-11-01, mesure sans seuil) | écart moyen 0,004–0,006 eV/atome sur les systèmes de sulfures, ≤ 0,0124 sur 9 polysulfures, systèmes Sb moins bons (LiSb₃ 0,161) |
| Benchmark avec pièges (2026-11-01, mesure sans seuil) : 5 isolants stables mais mauvais conducteurs du Li (Li₂S, LiCl, LiI, Li₃PO₄, Li₄GeS₄), dynamique moléculaire contre β-Li₃PS₄ | mesuré : pièges écartés par stabilité + gap 0/5, après lithium métal et diffusion 5/5 (Li₂S, Li₃PO₄ sans saut de Li ; LiCl plus lent ; Li₄GeS₄ non passivant ; LiI à égalité en D, écarté seulement par la règle de charpente, faiblement) ; bons 3/4 (2/4 avec le lithium), mauvais 8/8 |
| Tension moyenne UMA de quatre cathodes connues sans cobalt (2026-11-02, critère fixé avant : chaque écart à l'expérience ≤ `CATHODE_VOLTAGE_TRUTH_TOL_V` = 0,4 V, LiFePO₄ la plus basse et LiNi₀.₅Mn₁.₅O₄ la plus haute ; même relaxation et même délithiation qu'un candidat ; `scripts/cathode_truth.py`, `results/2026-11-02_cathode_truth/`) ✅ | mesuré : LiFePO₄ 3,45 V (exp. 3,45), LiMnPO₄ 3,79 (4,10), LiMn₂O₄ 3,82 (4,05), LiNi₀.₅Mn₁.₅O₄ 4,72 (4,70) ; ordre juste ; capacités 169,9 / 170,9 / 148,2 / 146,7 mAh/g ; variation de volume 3,6–5,8 % (LiFePO₄ 6,8 % mesuré : sous-estimée) |
| Benchmark à l'aveugle des cathodes (2026-11-02, résultats attendus fixés avant, `CATHODE_BENCHMARK` ; composé connu retiré de sa propre enveloppe ; `scripts/run_cathode_benchmark.py`, `results/2026-11-02_cathode_benchmark/`) | mesuré 9/10 : bonnes 2/2 (LiNiO₂ 3,95 V, Li₃V₂(PO₄)₃ 3,73 V), mauvaises 6/6 (LiCoO₂ cobalt ; Li₂MnO₃, LiFeO₂, Li₃PO₄, LiAlO₂, Li₄Ti₅O₁₂ : aucun Li ne peut sortir, tranché avant toute simulation), pièges 1/2 (LiTiO₂ rejeté à 1,46 V ; ❌ Li₂FeSiO₄ passe à 3,29 V contre 2,8 V mesurés : UMA surestime ce silicate de fer) |
| Barres d'erreur UMA / DFT des systèmes cathodes (2026-11-02, phases stables, mesure sans seuil ; `results/2026-11-02_cathode_error_bars/`) | écart moyen 0,005–0,010 eV/atome sur 8 systèmes (Li-Mn-Ni-O-Ti/V/Zr, Li-Mn-Ni-O, Li-Mn-Al-O, Li-Mn-Ti-O, Li-Mn-P-Si-O, Li-Fe-P-O) ; plus grand écart Fe₂O₃ 0,064 |
| Calibration de la dynamique moléculaire du sodium (2026-11-02, critère fixé avant : à 600 K, 2 graines × 40 ps, D(Na₃SbS₄) > D(Na₃PS₄ tétragonal) de plus de 2 erreurs combinées, charpentes intactes ; `scripts/sodium_md_calibration.py`, `results/2026-11-02_sodium_md_calibration/`) ❌ | mesuré : Na₃SbS₄ 7,6 ± 6,0 × 10⁻⁸ cm²/s (24 Na), Na₃PS₄ 2,3 ± 0,9 × 10⁻⁷ cm²/s (48 Na), rapport 0,33 ± 0,29 : ordre inverse de l'expérience, charpentes intactes. Règle fixée avant appliquée : `SODIUM_MD_CAN_EXCLUDE` = False, la diffusion de Na informe seulement (n'écarte ni ne classe). Hypothèses non testées : cristaux ordonnés sans lacune de Na (la conduction rapide de Na₃SbS₄ passe par ses lacunes) ; Na₃PS₄ passe en phase cubique vers 530 K |
| Calibration n° 2 de la dynamique moléculaire du sodium (2026-11-02, fixée avant ses calculs après l'échec de la n° 1, `SODIUM_MD_CALIBRATION_V2` : des lacunes de Na créées par W⁶⁺ sur Sb⁵⁺ doivent accélérer Na dans Na₃SbS₄, comme dans l'expérience où Na₂.₈₈Sb₀.₈₈W₀.₁₂S₄ atteint environ 32 mS/cm ; même maille de 64 atomes, mêmes graines ; `scripts/sodium_md_calibration_v2.py`, `results/2026-11-02_sodium_md_calibration_v2/`) ❌ | mesuré : Na₂₃Sb₇WS₃₂ 2,1 ± 0,7 × 10⁻⁶ cm²/s contre Na₃SbS₄ 7,6 ± 6,0 × 10⁻⁸, soit 28 fois plus vite, dans le sens de l'expérience ; mais le test du rapport donne 27,7 ± 24,0 (1,1 σ, « comparable ») car Na₃SbS₄ bouge à peine (80 % d'erreur relative). Avec ce test du rapport : échec. **Puis le propriétaire a choisi le test par différence** (celui de la calibration lithium v2 ✅, déjà utilisé) pour tout verdict candidat/parent (`analysis/diffusion.compare`, 2026-11-02) : différence +2,8 erreurs combinées → ✅ réussie, `SODIUM_MD_CAN_EXCLUDE` = True. La n° 1 reste en échec (−1,5). Les 39 verdicts déjà enregistrés (lithium et sodium) sont identiques avec les deux tests ; la calibration lithium, qui utilisait déjà la différence, ne change pas |
| Benchmark de validation à l'aveugle (2026-10-29, mesure sans seuil) : 4 bons électrolytes et 8 mauvais composés connus passent dans l'entonnoir, leur propre composition retirée des références, sans le modèle (`scripts/run_benchmark.py`, `results/2026-10-29_benchmark/`) | mesuré : bons qui passent 3/4 (2/4 avec le lithium métal : Li₆PS₅Cl écarté à 0,080 eV/atome, cellule ordonnée ; LGPS non passivant, Li₁₅Ge₄) ; mauvais écartés 8/8 (6 par le band gap, 2 Li₂PS₃ par la stabilité) |

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
