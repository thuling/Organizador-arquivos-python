import json
from pathlib import Path

import pytest

from organizador.config import (
    OTHERS_CATEGORY,
    ConfigError,
    OrganizerConfig,
    load_config,
    reset_config,
    save_config,
)


def test_default_config_classifies_case_insensitive_extensions():
    cfg = OrganizerConfig.default()
    assert cfg.classify_extension("FOTO.PNG") == "Imagens"
    assert cfg.classify_extension("relatorio.PDF") == "Documentos"
    assert cfg.classify_extension("video.MKV") == "Áudios e Vídeos"
    assert cfg.classify_extension("backup.tar.gz") == "Compactados"
    assert cfg.classify_extension("instalador.EXE") == "Executáveis"
    assert cfg.classify_extension("script.PY") == "Código e Dados"


def test_config_ignores_temp_and_system_files():
    cfg = OrganizerConfig.default()
    assert cfg.classify_extension("download.crdownload") is None
    assert cfg.classify_extension("arquivo.PART") is None
    assert cfg.classify_extension("temp.tmp") is None
    assert cfg.classify_extension("desktop.ini") is None
    assert cfg.classify_extension("Thumbs.db") is None


def test_config_routes_unknown_extension_to_others_when_enabled():
    cfg = OrganizerConfig.default()
    assert cfg.classify_extension("arquivo.xyz") == OTHERS_CATEGORY

    cfg.include_others = False
    assert cfg.classify_extension("arquivo.xyz") is None


def test_config_handles_files_without_extension():
    cfg = OrganizerConfig.default()
    assert cfg.classify_extension("README") == OTHERS_CATEGORY
    cfg.include_others = False
    assert cfg.classify_extension("README") is None


def test_save_and_load_config_roundtrip(tmp_path: Path):
    cfg_path = tmp_path / "config.json"
    cfg = OrganizerConfig.default()
    cfg.categories["Modelos 3D"] = ["stl", ".OBJ"]
    cfg.include_others = False
    cfg.theme = "light"

    save_config(cfg, cfg_path)
    loaded = load_config(cfg_path)

    assert loaded.include_others is False
    assert loaded.theme == "light"
    assert loaded.classify_extension("peca.stl") == "Modelos 3D"
    assert loaded.classify_extension("cena.obj") == "Modelos 3D"


def test_load_config_raises_config_error_on_invalid_json(tmp_path: Path):
    cfg_path = tmp_path / "broken.json"
    cfg_path.write_text("{json invalido", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(cfg_path)


def test_reset_config_restores_defaults(tmp_path: Path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"categories": {"Custom": [".abc"]}}), encoding="utf-8")

    restored = reset_config(cfg_path)
    assert "Imagens" in restored.categories
    assert "Custom" not in restored.categories
    assert cfg_path.exists()
