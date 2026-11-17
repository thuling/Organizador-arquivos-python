from pathlib import Path

from organizador.cli import main


def test_cli_dry_run_and_organize_and_undo(tmp_path: Path, capsys):
    target = tmp_path / "pasta"
    target.mkdir()
    (target / "a.jpg").write_bytes(b"1")
    (target / "b.pdf").write_bytes(b"2")
    history_file = tmp_path / "history.json"

    exit_code = main(["--path", str(target), "--dry-run", "--history", str(history_file)])
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Pré-visualização" in captured or "Imagens" in captured
    assert (target / "a.jpg").exists()

    exit_code = main(["--path", str(target), "--history", str(history_file)])
    assert exit_code == 0
    assert (target / "Imagens" / "a.jpg").exists()
    assert (target / "Documentos" / "b.pdf").exists()

    exit_code = main(["--path", str(target), "--undo", "--history", str(history_file)])
    assert exit_code == 0
    assert (target / "a.jpg").exists()
    assert (target / "b.pdf").exists()


def test_cli_returns_nonzero_on_invalid_folder(tmp_path: Path, capsys):
    missing = tmp_path / "nao_existe"
    exit_code = main(["--path", str(missing)])
    assert exit_code != 0
    captured = capsys.readouterr().err
    assert "não encontrada" in captured.lower() or "erro" in captured.lower()
