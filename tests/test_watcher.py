import time
from pathlib import Path

from organizador.config import OrganizerConfig
from organizador.watcher import FolderWatcher


def test_watcher_organizes_new_file_and_ignores_temp_files(tmp_path: Path):
    history_file = tmp_path / "_meta" / "history.json"
    organized_events: list[tuple[Path, Path, str]] = []

    watcher = FolderWatcher(
        folder=tmp_path,
        config=OrganizerConfig.default(),
        history_path=history_file,
        debounce_seconds=0.15,
        on_organized=lambda res: organized_events.extend(res.moved),
    )
    watcher.start()
    try:
        (tmp_path / "download.crdownload").write_bytes(b"parcial")
        (tmp_path / "foto.png").write_bytes(b"imagem")

        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline and not (tmp_path / "Imagens" / "foto.png").exists():
            time.sleep(0.05)

        assert (tmp_path / "Imagens" / "foto.png").exists()
        assert (tmp_path / "download.crdownload").exists()
        assert any(dst.name == "foto.png" for _, dst, _ in organized_events)
    finally:
        watcher.stop()
