from pathlib import Path

from organizador.core import organize_folder
from organizador.history import get_latest_batch, undo_last


def test_undo_last_restores_files_and_removes_empty_created_dirs(tmp_path: Path):
    target = tmp_path / "downloads"
    target.mkdir()
    (target / "foto.png").write_bytes(b"png")
    (target / "texto.pdf").write_bytes(b"pdf")
    history_file = tmp_path / "history.json"

    result = organize_folder(target, history_path=history_file)
    assert result.batch_id is not None
    assert (target / "Imagens" / "foto.png").exists()
    assert (target / "Documentos" / "texto.pdf").exists()

    undo_res = undo_last(folder=target, history_path=history_file)
    assert undo_res is not None
    assert len(undo_res.restored) == 2
    assert (target / "foto.png").exists()
    assert (target / "texto.pdf").exists()
    assert not (target / "Imagens").exists()
    assert not (target / "Documentos").exists()
    assert get_latest_batch(folder=target, history_path=history_file) is None


def test_undo_last_handles_missing_moved_file_and_collision_on_restore(tmp_path: Path):
    target = tmp_path / "downloads"
    target.mkdir()
    (target / "doc.pdf").write_bytes(b"original")
    (target / "sumido.jpg").write_bytes(b"img")
    history_file = tmp_path / "history.json"

    organize_folder(target, history_path=history_file)

    # Usuário apagou sumido.jpg e criou um novo doc.pdf na raiz
    (target / "Imagens" / "sumido.jpg").unlink()
    (target / "doc.pdf").write_bytes(b"novo-na-raiz")

    undo_res = undo_last(folder=target, history_path=history_file)
    assert undo_res is not None
    assert len(undo_res.restored) == 1
    assert len(undo_res.skipped_missing) == 1
    assert (target / "doc.pdf").read_bytes() == b"novo-na-raiz"
    assert (target / "doc (1).pdf").read_bytes() == b"original"


def test_undo_last_returns_none_when_history_empty(tmp_path: Path):
    history_file = tmp_path / "history.json"
    assert undo_last(folder=tmp_path, history_path=history_file) is None
