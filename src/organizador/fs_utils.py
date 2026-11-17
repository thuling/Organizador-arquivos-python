"""Utilitários de sistema de arquivos compartilhados entre módulos."""

from __future__ import annotations

from pathlib import Path

COMPOUND_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz")


def split_stem_and_suffix(path: Path) -> tuple[str, str]:
    """Separa nome base e extensão preservando extensões compostas comuns."""
    lower_name = path.name.lower()
    for compound in COMPOUND_SUFFIXES:
        if lower_name.endswith(compound) and len(path.name) > len(compound):
            ext = path.name[-len(compound) :]
            stem = path.name[: -len(compound)]
            return stem, ext
    return path.stem, path.suffix


def resolve_unique_path(target_path: Path, reserved: set[Path] | None = None) -> Path:
    """Resolve conflitos de nome usando sufixo incremental estilo 'arquivo (1).ext'."""
    reserved_paths = reserved or set()
    if not target_path.exists() and target_path not in reserved_paths:
        return target_path

    stem, ext = split_stem_and_suffix(target_path)
    counter = 1
    while True:
        candidate = target_path.with_name(f"{stem} ({counter}){ext}")
        if not candidate.exists() and candidate not in reserved_paths:
            return candidate
        counter += 1
