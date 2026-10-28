"""AutoLab: agent searching solid electrolytes for lithium-metal batteries."""

import warnings

# Known, harmless and very repetitive: scipy during cell relaxations, pymatgen on MP structures.
warnings.filterwarnings("ignore", message="logm result may be inaccurate")
warnings.filterwarnings("ignore", message="Not all sites have property magmom")
