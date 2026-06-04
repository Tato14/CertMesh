"""Microsoft IQ layers.

* :mod:`foundry_iq` — the REQUIRED, real IQ layer: a knowledge base with
  agentic retrieve-and-cite. Uses Azure AI Search when configured, and a local
  vector/BM25 index over data/knowledge/ with the *same* contract otherwise.
* :mod:`work_iq` — concept-faithful Work IQ context layer over synthetic work
  signals (capacity / focus / preferred slot).
* :mod:`fabric_iq` — concept-faithful Fabric IQ semantic layer: an ontology over
  the synthetic certification seed (entities + relationships, semantic queries).

See docs/iq-layers.md for what is real vs. concept-faithful and the upgrade path.
"""

from .fabric_iq import FabricIQ, get_fabric_iq
from .foundry_iq import FoundryIQ, get_foundry_iq, supports
from .work_iq import WorkIQ, get_work_iq

__all__ = [
    "FoundryIQ", "get_foundry_iq", "supports",
    "WorkIQ", "get_work_iq",
    "FabricIQ", "get_fabric_iq",
]
