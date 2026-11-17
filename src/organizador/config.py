"""Gerenciamento de configurações e regras de categorização."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from organizador import APP_NAME

OTHERS_CATEGORY = "Outros"

DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "Imagens": [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".bmp",
        ".ico",
        ".jfif",
        ".heic",
        ".tiff",
        ".raw",
    ],
    "Documentos": [
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".md",
        ".rtf",
        ".odt",
        ".csv",
        ".xlsx",
        ".xls",
        ".pptx",
        ".ppt",
        ".epub",
    ],
    "Áudios e Vídeos": [
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".m4a",
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".webm",
        ".wmv",
    ],
    "Compactados": [
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".tar.gz",
        ".tar.bz2",
        ".tar.xz",
    ],
    "Executáveis": [
        ".exe",
        ".msi",
        ".bat",
        ".cmd",
        ".ps1",
        ".apk",
        ".appimage",
    ],
    "Código e Dados": [
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".html",
        ".css",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".sql",
        ".ipynb",
    ],
}

DEFAULT_IGNORED_EXTENSIONS: tuple[str, ...] = (
    ".crdownload",
    ".part",
    ".tmp",
    ".download",
    ".partial",
)

DEFAULT_IGNORED_NAMES: tuple[str, ...] = (
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
)


class ConfigError(ValueError):
    """Erro ao carregar ou validar o arquivo de configuração."""


def normalize_extension(ext: str) -> str:
    """Normaliza uma extensão para minúscula com ponto inicial."""
    cleaned = ext.strip().lower()
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith(".") else f".{cleaned}"


def _candidate_app_dirs() -> list[Path]:
    """Lista diretórios candidatos para dados da aplicação em ordem de preferência."""
    candidates: list[Path] = []
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / APP_NAME)
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            candidates.append(Path(local_appdata) / APP_NAME)
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            candidates.append(Path(xdg) / APP_NAME)
        candidates.append(Path.home() / ".config" / APP_NAME)

    candidates.append(Path.home() / f".{APP_NAME.lower()}")
    candidates.append(Path(tempfile.gettempdir()) / APP_NAME)
    return candidates


def _is_dir_writable(path: Path) -> bool:
    """Testa escrita real no diretório (mais confiável que os.access no Windows)."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def get_app_data_dir(create: bool = False) -> Path:
    """Retorna o diretório de dados da aplicação, com fallback seguro se não houver permissão."""
    candidates = _candidate_app_dirs()
    for candidate in candidates:
        if create:
            if _is_dir_writable(candidate):
                return candidate
        elif candidate.exists() and os.access(candidate, os.R_OK):
            return candidate
    return candidates[-1]


def get_default_config_path(create_dir: bool = False) -> Path:
    """Retorna o caminho padrão do arquivo config.json."""
    for candidate in _candidate_app_dirs():
        cfg_file = candidate / "config.json"
        if cfg_file.exists():
            return cfg_file
    return get_app_data_dir(create=create_dir) / "config.json"


@dataclass
class OrganizerConfig:
    """Configuração de regras e preferências do organizador."""

    categories: dict[str, list[str]] = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_CATEGORIES.items()}
    )
    include_others: bool = True
    others_folder: str = OTHERS_CATEGORY
    ignore_hidden: bool = True
    ignored_extensions: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORED_EXTENSIONS))
    ignored_names: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORED_NAMES))
    theme: str = "dark"

    @classmethod
    def default(cls) -> OrganizerConfig:
        """Cria uma configuração padrão nova."""
        return cls()

    def build_extension_map(self) -> dict[str, str]:
        """Constrói mapa O(1) de extensão normalizada para nome da categoria."""
        mapping: dict[str, str] = {}
        for category, extensions in self.categories.items():
            folder_name = category.strip()
            if not folder_name:
                continue
            for ext in extensions:
                norm = normalize_extension(ext)
                if norm and norm not in mapping:
                    mapping[norm] = folder_name
        return mapping

    def is_ignored_name(self, filename: str) -> bool:
        """Verifica se o arquivo deve ser ignorado por nome ou extensão temporária."""
        lower_name = filename.lower()
        if lower_name in {n.lower() for n in self.ignored_names}:
            return True
        ignored_exts = {normalize_extension(e) for e in self.ignored_extensions}
        return Path(lower_name).suffix in ignored_exts

    def classify_extension(self, filename: str) -> str | None:
        """Retorna a categoria de destino de um nome de arquivo ou None se ignorado."""
        if self.is_ignored_name(filename):
            return None

        path = Path(filename)
        ext_map = self.build_extension_map()

        suffixes = [s.lower() for s in path.suffixes]
        if len(suffixes) >= 2:
            compound = "".join(suffixes[-2:])
            if compound in ext_map:
                return ext_map[compound]

        single = path.suffix.lower()
        if single and single in ext_map:
            return ext_map[single]

        if self.include_others and self.others_folder.strip():
            return self.others_folder.strip()
        return None

    def all_category_names(self) -> list[str]:
        """Retorna todos os nomes de categorias na ordem configurada."""
        names = list(self.categories.keys())
        if self.include_others and self.others_folder not in names:
            names.append(self.others_folder)
        return names

    def to_dict(self) -> dict[str, Any]:
        """Serializa a configuração para dicionário compatível com JSON."""
        normalized_categories: dict[str, list[str]] = {}
        for category, extensions in self.categories.items():
            clean_exts = []
            seen = set()
            for ext in extensions:
                norm = normalize_extension(ext)
                if norm and norm not in seen:
                    seen.add(norm)
                    clean_exts.append(norm)
            normalized_categories[category.strip()] = clean_exts

        return {
            "categories": normalized_categories,
            "include_others": self.include_others,
            "others_folder": self.others_folder,
            "ignore_hidden": self.ignore_hidden,
            "ignored_extensions": [
                normalize_extension(e) for e in self.ignored_extensions if normalize_extension(e)
            ],
            "ignored_names": [n.strip().lower() for n in self.ignored_names if n.strip()],
            "theme": self.theme if self.theme in {"dark", "light"} else "dark",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrganizerConfig:
        """Reconstrói a configuração a partir de um dicionário validado."""
        if not isinstance(data, dict):
            raise ConfigError("O arquivo de configuração deve ser um objeto JSON.")

        raw_categories = data.get("categories", DEFAULT_CATEGORIES)
        if not isinstance(raw_categories, dict):
            raise ConfigError("O campo 'categories' deve ser um objeto mapeando pastas para extensões.")

        categories: dict[str, list[str]] = {}
        for folder_name, exts in raw_categories.items():
            if not isinstance(folder_name, str) or not isinstance(exts, list):
                raise ConfigError(f"Categoria inválida na configuração: {folder_name!r}")
            categories[folder_name.strip()] = [
                normalize_extension(str(e)) for e in exts if normalize_extension(str(e))
            ]

        theme = str(data.get("theme", "dark")).lower()
        if theme not in {"dark", "light"}:
            theme = "dark"

        return cls(
            categories=categories,
            include_others=bool(data.get("include_others", True)),
            others_folder=str(data.get("others_folder", OTHERS_CATEGORY)).strip() or OTHERS_CATEGORY,
            ignore_hidden=bool(data.get("ignore_hidden", True)),
            ignored_extensions=[
                normalize_extension(str(e))
                for e in data.get("ignored_extensions", DEFAULT_IGNORED_EXTENSIONS)
                if normalize_extension(str(e))
            ],
            ignored_names=[
                str(n).strip().lower()
                for n in data.get("ignored_names", DEFAULT_IGNORED_NAMES)
                if str(n).strip()
            ],
            theme=theme,
        )


def load_config(config_path: Path | None = None) -> OrganizerConfig:
    """Carrega config.json do caminho informado ou usa o padrão se não existir."""
    path = config_path or get_default_config_path()
    if not path.exists():
        return OrganizerConfig.default()

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Não foi possível ler a configuração em {path}: {exc}") from exc

    return OrganizerConfig.from_dict(data)


def save_config(config: OrganizerConfig, config_path: Path | None = None) -> Path:
    """Salva a configuração em disco em formato JSON legível."""
    path = config_path or get_default_config_path(create_dir=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def reset_config(config_path: Path | None = None) -> OrganizerConfig:
    """Restaura a configuração padrão e a grava em disco."""
    cfg = OrganizerConfig.default()
    save_config(cfg, config_path)
    return cfg
