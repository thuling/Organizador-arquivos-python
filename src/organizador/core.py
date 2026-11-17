"""Núcleo de planejamento e execução da organização de arquivos."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from organizador.config import OrganizerConfig
from organizador.fs_utils import resolve_unique_path
from organizador.history import append_batch


@dataclass(frozen=True)
class PlannedMove:
    """Representa uma movimentação planejada antes da execução."""

    source: Path
    destination: Path
    category: str
    size_bytes: int
    renamed: bool


@dataclass
class OrganizationPlan:
    """Plano completo gerado para uma pasta."""

    folder: Path
    moves: list[PlannedMove]
    skipped: list[tuple[Path, str]]
    category_counts: dict[str, int]
    total_bytes: int


@dataclass
class OrganizationResult:
    """Resumo da execução do plano de organização."""

    folder: Path
    moved: list[tuple[Path, Path, str]]
    failed: list[tuple[Path, str]]
    skipped: list[tuple[Path, str]]
    batch_id: str | None
    dry_run: bool


def format_size(size_bytes: int) -> str:
    """Formata tamanho em bytes de forma legível (B, KB, MB, GB)."""
    size = float(max(0, size_bytes))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def plan_organization(
    folder: Path,
    config: OrganizerConfig | None = None,
    enabled_categories: set[str] | None = None,
    only_files: list[Path] | None = None,
) -> OrganizationPlan:
    """Analisa uma pasta e gera o plano de organização sem modificar o disco."""
    target_dir = Path(folder)
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {target_dir}")

    cfg = config or OrganizerConfig.default()

    if only_files is not None:
        resolved_dir = target_dir.resolve()
        entries = sorted(
            (
                p
                for p in only_files
                if p.exists() and not p.is_symlink() and p.is_file() and p.parent.resolve() == resolved_dir
            ),
            key=lambda p: p.name.lower(),
        )
    else:
        entries = sorted(target_dir.iterdir(), key=lambda p: p.name.lower())

    moves: list[PlannedMove] = []
    skipped: list[tuple[Path, str]] = []
    category_counts: dict[str, int] = {}
    reserved: set[Path] = set()
    total_bytes = 0

    for entry in entries:
        if entry.is_symlink() or not entry.is_file():
            continue

        if cfg.ignore_hidden and entry.name.startswith("."):
            skipped.append((entry, "Arquivo oculto ignorado"))
            continue

        category = cfg.classify_extension(entry.name)
        if category is None:
            skipped.append((entry, "Ignorado ou sem categoria ativa"))
            continue

        if enabled_categories is not None and category not in enabled_categories:
            skipped.append((entry, f"Categoria '{category}' desmarcada"))
            continue

        dest_dir = target_dir / category
        desired_dest = dest_dir / entry.name
        final_dest = resolve_unique_path(desired_dest, reserved=reserved)
        reserved.add(final_dest)

        try:
            size_bytes = entry.stat().st_size
        except OSError:
            size_bytes = 0

        moves.append(
            PlannedMove(
                source=entry,
                destination=final_dest,
                category=category,
                size_bytes=size_bytes,
                renamed=(final_dest.name != entry.name),
            )
        )
        category_counts[category] = category_counts.get(category, 0) + 1
        total_bytes += size_bytes

    return OrganizationPlan(
        folder=target_dir,
        moves=moves,
        skipped=skipped,
        category_counts=category_counts,
        total_bytes=total_bytes,
    )


def apply_plan(
    plan: OrganizationPlan,
    dry_run: bool = False,
    history_path: Path | None = None,
    progress_callback: Callable[[int, int, PlannedMove], None] | None = None,
) -> OrganizationResult:
    """Executa (ou simula) um OrganizationPlan e registra o histórico para desfazer."""
    if dry_run:
        return OrganizationResult(
            folder=plan.folder,
            moved=[(m.source, m.destination, m.category) for m in plan.moves],
            failed=[],
            skipped=list(plan.skipped),
            batch_id=None,
            dry_run=True,
        )

    moved: list[tuple[Path, Path, str]] = []
    failed: list[tuple[Path, str]] = []
    total = len(plan.moves)

    for idx, move in enumerate(plan.moves, start=1):
        if not move.source.exists():
            failed.append((move.source, "Arquivo de origem não existe mais"))
        else:
            try:
                move.destination.parent.mkdir(parents=True, exist_ok=True)
                final_dest = resolve_unique_path(move.destination)
                shutil.move(str(move.source), str(final_dest))
                moved.append((move.source, final_dest, move.category))
            except OSError as exc:
                failed.append((move.source, str(exc)))

        if progress_callback is not None:
            progress_callback(idx, total, move)

    batch_id: str | None = None
    if moved:
        batch = append_batch(plan.folder, moved, history_path=history_path)
        if batch is not None:
            batch_id = batch.batch_id

    return OrganizationResult(
        folder=plan.folder,
        moved=moved,
        failed=failed,
        skipped=list(plan.skipped),
        batch_id=batch_id,
        dry_run=False,
    )


def organize_folder(
    folder: Path,
    config: OrganizerConfig | None = None,
    dry_run: bool = False,
    enabled_categories: set[str] | None = None,
    history_path: Path | None = None,
    progress_callback: Callable[[int, int, PlannedMove], None] | None = None,
) -> OrganizationResult:
    """Planeja e executa a organização de uma pasta em uma única chamada."""
    plan = plan_organization(
        folder=folder,
        config=config,
        enabled_categories=enabled_categories,
    )
    return apply_plan(
        plan=plan,
        dry_run=dry_run,
        history_path=history_path,
        progress_callback=progress_callback,
    )
