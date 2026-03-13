from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_public_cadiax_package_reexports_version() -> None:
    import cadiax
    import otonomassist

    assert cadiax.__version__ == otonomassist.__version__
    assert cadiax.Assistant is otonomassist.Assistant


def test_public_cadiax_cli_wrapper_points_to_main() -> None:
    from cadiax.cli import main as cadiax_main
    from otonomassist.cli import main as internal_main

    assert cadiax_main is internal_main
