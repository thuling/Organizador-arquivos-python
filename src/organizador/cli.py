"""Interface de linha de comando (CLI) e ponto de entrada para a GUI."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from organizador import APP_DISPLAY_NAME, __version__
from organizador.config import ConfigError, load_config
from organizador.core import apply_plan, format_size, plan_organization
from organizador.history import undo_last
from organizador.watcher import FolderWatcher


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos da CLI."""
    parser = argparse.ArgumentParser(
        prog="organizador",
        description=f"{APP_DISPLAY_NAME} — organize pastas por extensão com segurança.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Caminho da pasta a organizar (atalho posicional).",
    )
    parser.add_argument(
        "-p",
        "--path",
        dest="path_opt",
        help="Caminho da pasta a organizar.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra a pré-visualização sem mover nenhum arquivo.",
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="Desfaz a última organização registrada para a pasta (ou a mais recente).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Monitora a pasta em tempo real e organiza novos arquivos automaticamente.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Caminho para um arquivo config.json personalizado.",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=None,
        help="Caminho para um arquivo history.json personalizado.",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Lista de categorias separadas por vírgula para incluir.",
    )
    parser.add_argument(
        "--no-others",
        action="store_true",
        help="Não move extensões desconhecidas para a pasta 'Outros'.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre a interface gráfica.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _resolve_target_path(args: argparse.Namespace) -> Path | None:
    raw = args.path_opt or args.target
    return Path(raw).expanduser() if raw else None


def _run_undo(folder: Path | None, history_path: Path | None) -> int:
    result = undo_last(folder=folder, history_path=history_path)
    if result is None:
        print("Nenhuma organização anterior encontrada para desfazer.")
        return 0

    print(f"Arquivos restaurados: {len(result.restored)}")
    for src_now, orig in result.restored:
        print(f"  <- {src_now.name} restaurado para {orig}")
    if result.skipped_missing:
        print(f"Arquivos não encontrados (já movidos/removidos): {len(result.skipped_missing)}")
    if result.removed_dirs:
        print(f"Pastas vazias removidas: {len(result.removed_dirs)}")
    if result.errors:
        print(f"Erros ao restaurar: {len(result.errors)}", file=sys.stderr)
        for path, err in result.errors:
            print(f"  ! {path}: {err}", file=sys.stderr)
        return 1
    return 0


def _run_watch(
    folder: Path,
    config_path: Path | None,
    history_path: Path | None,
    enabled_categories: set[str] | None,
    no_others: bool,
) -> int:
    cfg = load_config(config_path)
    if no_others:
        cfg.include_others = False

    def _on_auto(res) -> None:
        for src, dst, cat in res.moved:
            print(f"[Auto] {src.name} -> {cat}/{dst.name}")
        for src, err in res.failed:
            print(f"[Erro] {src.name}: {err}", file=sys.stderr)

    watcher = FolderWatcher(
        folder=folder,
        config=cfg,
        enabled_categories=enabled_categories,
        history_path=history_path,
        on_organized=_on_auto,
    )
    watcher.start()
    print(f"Monitorando '{folder}'... Pressione Ctrl+C para encerrar.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nEncerrando monitoramento...")
    finally:
        watcher.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    """Executa a CLI ou abre a GUI quando chamado sem parâmetros."""
    raw_args = sys.argv[1:] if argv is None else argv
    if not raw_args:
        from organizador.gui.main_window import launch_gui

        return launch_gui()

    parser = build_parser()
    args = parser.parse_args(raw_args)
    target_path = _resolve_target_path(args)

    if args.gui:
        from organizador.gui.main_window import launch_gui

        return launch_gui(
            initial_folder=target_path,
            config_path=args.config,
            history_path=args.history,
        )

    if args.undo:
        return _run_undo(folder=target_path, history_path=args.history)

    if target_path is None:
        parser.print_help()
        return 2

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Erro na configuração: {exc}", file=sys.stderr)
        return 1

    if args.no_others:
        cfg.include_others = False

    enabled_categories: set[str] | None = None
    if args.categories:
        enabled_categories = {c.strip() for c in args.categories.split(",") if c.strip()}

    if not target_path.exists() or not target_path.is_dir():
        print(f"Erro: pasta não encontrada: {target_path}", file=sys.stderr)
        return 1

    if args.watch:
        return _run_watch(
            folder=target_path,
            config_path=args.config,
            history_path=args.history,
            enabled_categories=enabled_categories,
            no_others=args.no_others,
        )

    plan = plan_organization(
        folder=target_path,
        config=cfg,
        enabled_categories=enabled_categories,
    )

    if args.dry_run:
        print(
            f"Pré-visualização para '{target_path}': "
            f"{len(plan.moves)} arquivo(s) ({format_size(plan.total_bytes)})"
        )
        for move in plan.moves:
            suffix = " (renomeado por colisão)" if move.renamed else ""
            print(f"  {move.source.name} -> {move.category}/{move.destination.name}{suffix}")
        return 0

    if not plan.moves:
        print("Nenhum arquivo pendente para organizar nesta pasta.")
        return 0

    result = apply_plan(plan, dry_run=False, history_path=args.history)
    print(f"Organização concluída em '{target_path}': {len(result.moved)} arquivo(s) movido(s).")
    for src, dst, cat in result.moved:
        print(f"  {src.name} -> {cat}/{dst.name}")

    if result.failed:
        print(f"Falhas ({len(result.failed)}):", file=sys.stderr)
        for src, err in result.failed:
            print(f"  ! {src.name}: {err}", file=sys.stderr)
        return 1
    return 0
