from pathlib import Path
from unittest.mock import patch

import pytest

from organizador.config import OrganizerConfig
from organizador.core import apply_plan, organize_folder, plan_organization


def test_organize_moves_files_case_insensitive_and_ignores_subfolders(tmp_path: Path):
    (tmp_path / "foto.PNG").write_bytes(b"img")
    (tmp_path / "doc.pdf").write_bytes(b"pdf")
    (tmp_path / "backup.zip").mkdir()  # subpasta com ponto no nome NÃO deve ser movida
    (tmp_path / "baixando.crdownload").write_bytes(b"tmp")
    (tmp_path / ".oculto.txt").write_bytes(b"hidden")

    history_file = tmp_path / "_meta" / "history.json"
    result = organize_folder(tmp_path, history_path=history_file)

    assert len(result.moved) == 2
    assert not result.failed
    assert (tmp_path / "Imagens" / "foto.PNG").exists()
    assert (tmp_path / "Documentos" / "doc.pdf").exists()
    assert (tmp_path / "backup.zip").is_dir()
    assert (tmp_path / "baixando.crdownload").exists()
    assert (tmp_path / ".oculto.txt").exists()


def test_collision_uses_incremental_suffix_instead_of_uuid(tmp_path: Path):
    img_dir = tmp_path / "Imagens"
    img_dir.mkdir()
    (img_dir / "foto.jpg").write_bytes(b"existente")
    (img_dir / "foto (1).jpg").write_bytes(b"existente-1")
    (tmp_path / "foto.jpg").write_bytes(b"novo")

    history_file = tmp_path / "_meta" / "history.json"
    result = organize_folder(tmp_path, history_path=history_file)

    assert len(result.moved) == 1
    _, dest, _ = result.moved[0]
    assert dest.name == "foto (2).jpg"
    assert dest.read_bytes() == b"novo"
    assert (img_dir / "foto.jpg").read_bytes() == b"existente"


def test_dry_run_does_not_create_folders_or_move_files(tmp_path: Path):
    (tmp_path / "a.jpg").write_bytes(b"1")
    (tmp_path / "b.mp3").write_bytes(b"2")

    history_file = tmp_path / "_meta" / "history.json"
    plan = plan_organization(tmp_path)
    assert len(plan.moves) == 2
    assert plan.category_counts == {"Imagens": 1, "Áudios e Vídeos": 1}

    result = apply_plan(plan, dry_run=True, history_path=history_file)
    assert result.dry_run is True
    assert len(result.moved) == 2
    assert (tmp_path / "a.jpg").exists()
    assert not (tmp_path / "Imagens").exists()
    assert not history_file.exists()


def test_enabled_categories_filter_only_plans_selected_categories(tmp_path: Path):
    (tmp_path / "a.jpg").write_bytes(b"1")
    (tmp_path / "b.pdf").write_bytes(b"2")

    plan = plan_organization(tmp_path, enabled_categories={"Imagens"})
    assert len(plan.moves) == 1
    assert plan.moves[0].source.name == "a.jpg"
    assert plan.moves[0].category == "Imagens"


def test_permission_error_on_one_file_does_not_abort_other_files(tmp_path: Path):
    (tmp_path / "a.pdf").write_bytes(b"a")
    (tmp_path / "b.pdf").write_bytes(b"b")

    plan = plan_organization(tmp_path)
    original_move = __import__("shutil").move

    def flaky_move(src: str, dst: str):
        if Path(src).name == "a.pdf":
            raise PermissionError("Arquivo em uso")
        return original_move(src, dst)

    history_file = tmp_path / "_meta" / "history.json"
    with patch("organizador.core.shutil.move", side_effect=flaky_move):
        result = apply_plan(plan, history_path=history_file)

    assert len(result.moved) == 1
    assert len(result.failed) == 1
    assert result.failed[0][0].name == "a.pdf"
    assert (tmp_path / "a.pdf").exists()
    assert (tmp_path / "Documentos" / "b.pdf").exists()


def test_organize_raises_for_missing_folder(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        plan_organization(tmp_path / "nao_existe")


def test_compound_extension_and_others_option(tmp_path: Path):
    (tmp_path / "pacote.tar.gz").write_bytes(b"gz")
    (tmp_path / "desconhecido.xyz").write_bytes(b"xyz")

    cfg = OrganizerConfig.default()
    cfg.include_others = True
    plan = plan_organization(tmp_path, config=cfg)

    categories = {m.source.name: m.category for m in plan.moves}
    assert categories["pacote.tar.gz"] == "Compactados"
    assert categories["desconhecido.xyz"] == "Outros"
