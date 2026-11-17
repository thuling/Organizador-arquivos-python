"""Histórico de movimentações e suporte para desfazer organizações."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from organizador.config import get_app_data_dir
from organizador.fs_utils import resolve_unique_path


@dataclass(frozen=True)
class MoveRecord:
    """Registro individual de arquivo movido em um lote."""

    source: str
    destination: str
    category: str


@dataclass
class HistoryBatch:
    """Conjunto de movimentações executadas em uma mesma operação."""

    batch_id: str
    timestamp: str
    folder: str
    moves: list[MoveRecord]


@dataclass
class UndoResult:
    """Resultado detalhado da operação de desfazer."""

    restored: list[tuple[Path, Path]]
    skipped_missing: list[Path]
    errors: list[tuple[Path, str]]
    removed_dirs: list[Path]


def get_default_history_path(create_dir: bool = False) -> Path:
    """Retorna o caminho padrão do arquivo history.json."""
    return get_app_data_dir(create=create_dir) / "history.json"


def _normalize_folder(folder: Path) -> str:
    return str(folder.resolve())


def load_history(history_path: Path | None = None) -> list[HistoryBatch]:
    """Carrega os lotes salvos do arquivo de histórico."""
    path = history_path or get_default_history_path()
    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(raw, list):
        return []

    batches: list[HistoryBatch] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        raw_moves = item.get("moves", [])
        if not isinstance(raw_moves, list):
            continue
        moves = [
            MoveRecord(
                source=str(m["source"]),
                destination=str(m["destination"]),
                category=str(m.get("category", "")),
            )
            for m in raw_moves
            if isinstance(m, dict) and "source" in m and "destination" in m
        ]
        if not moves:
            continue
        batches.append(
            HistoryBatch(
                batch_id=str(item.get("batch_id", "")),
                timestamp=str(item.get("timestamp", "")),
                folder=str(item.get("folder", "")),
                moves=moves,
            )
        )
    return batches


def save_history(batches: list[HistoryBatch], history_path: Path | None = None) -> Path:
    """Persiste a lista de lotes no disco."""
    path = history_path or get_default_history_path(create_dir=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "batch_id": batch.batch_id,
            "timestamp": batch.timestamp,
            "folder": batch.folder,
            "moves": [asdict(move) for move in batch.moves],
        }
        for batch in batches
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def append_batch(
    folder: Path,
    moves: list[tuple[Path, Path, str]],
    history_path: Path | None = None,
    max_batches: int = 30,
) -> HistoryBatch | None:
    """Registra um novo lote de arquivos movidos no histórico."""
    if not moves:
        return None

    batches = load_history(history_path)
    batch = HistoryBatch(
        batch_id=uuid.uuid4().hex[:10],
        timestamp=datetime.now(UTC).isoformat(),
        folder=_normalize_folder(folder),
        moves=[
            MoveRecord(source=str(src), destination=str(dst), category=cat)
            for src, dst, cat in moves
        ],
    )
    batches.append(batch)
    if len(batches) > max_batches:
        batches = batches[-max_batches:]
    save_history(batches, history_path)
    return batch


def get_latest_batch(
    folder: Path | None = None,
    history_path: Path | None = None,
) -> HistoryBatch | None:
    """Obtém o lote mais recente (global ou filtrado por pasta)."""
    batches = load_history(history_path)
    if not batches:
        return None

    if folder is None:
        return batches[-1]

    target = _normalize_folder(folder)
    for batch in reversed(batches):
        if batch.folder == target:
            return batch
    return None


def undo_last(
    folder: Path | None = None,
    history_path: Path | None = None,
) -> UndoResult | None:
    """Desfaz o último lote registrado para a pasta (ou o último geral)."""
    batches = load_history(history_path)
    if not batches:
        return None

    target_index: int | None = None
    if folder is None:
        target_index = len(batches) - 1
    else:
        normalized = _normalize_folder(folder)
        for idx in range(len(batches) - 1, -1, -1):
            if batches[idx].folder == normalized:
                target_index = idx
                break

    if target_index is None:
        return None

    batch = batches[target_index]
    restored: list[tuple[Path, Path]] = []
    skipped_missing: list[Path] = []
    errors: list[tuple[Path, str]] = []
    remaining_moves: list[MoveRecord] = []
    touched_dirs: set[Path] = set()

    for record in reversed(batch.moves):
        current_path = Path(record.destination)
        original_path = Path(record.source)

        if not current_path.exists():
            skipped_missing.append(current_path)
            continue

        try:
            original_path.parent.mkdir(parents=True, exist_ok=True)
            restore_dest = resolve_unique_path(original_path)
            shutil.move(str(current_path), str(restore_dest))
            restored.append((current_path, restore_dest))
            touched_dirs.add(current_path.parent)
        except OSError as exc:
            errors.append((current_path, str(exc)))
            remaining_moves.append(record)

    removed_dirs: list[Path] = []
    for directory in sorted(touched_dirs, key=lambda p: len(p.parts), reverse=True):
        try:
            if directory.exists() and directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
                removed_dirs.append(directory)
        except OSError:
            pass

    if remaining_moves:
        batches[target_index].moves = list(reversed(remaining_moves))
    else:
        batches.pop(target_index)
    save_history(batches, history_path)

    return UndoResult(
        restored=restored,
        skipped_missing=skipped_missing,
        errors=errors,
        removed_dirs=removed_dirs,
    )
