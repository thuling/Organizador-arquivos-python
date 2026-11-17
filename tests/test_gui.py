import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from organizador.gui.main_window import MainWindow


def _get_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_gui_loads_folder_previews_organizes_and_undoes(tmp_path: Path):
    _get_app()

    target = tmp_path / "Downloads"
    target.mkdir()
    (target / "foto.png").write_bytes(b"img")
    (target / "contrato.pdf").write_bytes(b"pdf")

    cfg_path = tmp_path / "config.json"
    hist_path = tmp_path / "history.json"

    window = MainWindow(
        config_path=cfg_path,
        history_path=hist_path,
        enable_tray=False,
        sync_worker=True,
    )
    window.set_folder(target)

    assert window.preview_table.rowCount() == 2
    assert window.organize_button.isEnabled() is True
    assert window.undo_button.isEnabled() is False

    # Desmarca "Documentos" -> prévia deve cair para 1 arquivo
    window.category_pills["Documentos"].setChecked(False)
    assert window.preview_table.rowCount() == 1

    # Reativa e organiza tudo
    window.category_pills["Documentos"].setChecked(True)
    assert window.preview_table.rowCount() == 2

    window.organize_now()

    assert (target / "Imagens" / "foto.png").exists()
    assert (target / "Documentos" / "contrato.pdf").exists()
    assert window.preview_table.rowCount() == 0
    assert window.undo_button.isEnabled() is True

    # Desfaz organização pela interface
    window.undo_last_action()

    assert (target / "foto.png").exists()
    assert (target / "contrato.pdf").exists()
    assert window.preview_table.rowCount() == 2
    assert window.undo_button.isEnabled() is False

    window.close()


def test_gui_theme_toggle_updates_config_and_stylesheet(tmp_path: Path):
    _get_app()

    cfg_path = tmp_path / "config.json"
    hist_path = tmp_path / "history.json"

    window = MainWindow(
        config_path=cfg_path,
        history_path=hist_path,
        enable_tray=False,
        sync_worker=True,
    )
    initial_theme = window.config.theme
    window.toggle_theme()
    assert window.config.theme != initial_theme
    assert window.styleSheet() != ""
    window.close()
