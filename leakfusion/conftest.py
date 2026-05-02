"""Pytest configuration for leakfusion.

Adds syn-engine/ to sys.path so tests can `import src` (syn-engine's package) as `syn_engine_src`.
"""
import sys
from pathlib import Path

LEAKFUSION_ROOT = Path(__file__).parent
SYN_ENGINE_ROOT = LEAKFUSION_ROOT.parent / "syn-engine"

# syn-engine uses `src` as its package name; re-expose under a non-conflicting alias
if str(SYN_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(SYN_ENGINE_ROOT))

# leakfusion uses `leakfusion.src` via the package hierarchy
if str(LEAKFUSION_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(LEAKFUSION_ROOT.parent))
