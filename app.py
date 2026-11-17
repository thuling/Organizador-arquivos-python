"""Ponto de entrada principal (abre a GUI ou executa via CLI)."""

from __future__ import annotations

import sys
from pathlib import Path

# Garante importação do pacote src/ mesmo quando executado diretamente via `python app.py`.
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from organizador.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
