"""AutoLab: agent searching solid electrolytes for lithium-metal batteries."""

import warnings

# Known, harmless and very repetitive: scipy during cell relaxations, pymatgen on MP structures.
warnings.filterwarnings("ignore", message="logm result may be inaccurate")
warnings.filterwarnings("ignore", message="Not all sites have property magmom")
# MP2020 corrections on polysulfides (e.g. LiS2): pymatgen falls back to the most electronegative atom, as MP does.
warnings.filterwarnings("ignore", message="Failed to guess oxidation states")
