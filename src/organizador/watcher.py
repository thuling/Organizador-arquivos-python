"""Monitoramento em tempo real de pastas com watchdog e debounce."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from organizador.config import OrganizerConfig
from organizador.core import OrganizationResult, apply_plan, plan_organization


class _FolderEventHandler(FileSystemEventHandler):
    """Handler de eventos do watchdog com debounce por caminho."""

    def __init__(self, owner: FolderWatcher) -> None:
        super().__init__()
        self._owner = owner

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._owner.schedule_path(Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory and hasattr(event, "dest_path"):
            self._owner.schedule_path(Path(event.dest_path))


class FolderWatcher:
    """Observa uma pasta e organiza novos arquivos automaticamente."""

    def __init__(
        self,
        folder: Path,
        config: OrganizerConfig | None = None,
        enabled_categories: set[str] | None = None,
        history_path: Path | None = None,
        debounce_seconds: float = 1.2,
        on_organized: Callable[[OrganizationResult], None] | None = None,
    ) -> None:
        self.folder = Path(folder)
        if not self.folder.exists() or not self.folder.is_dir():
            raise FileNotFoundError(f"Pasta não encontrada para monitoramento: {self.folder}")

        self.config = config or OrganizerConfig.default()
        self.enabled_categories = enabled_categories
        self.history_path = history_path
        self.debounce_seconds = debounce_seconds
        self.on_organized = on_organized

        self._lock = threading.Lock()
        self._timers: dict[Path, threading.Timer] = {}
        self._observer: Observer | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def update_rules(
        self,
        config: OrganizerConfig | None = None,
        enabled_categories: set[str] | None = None,
    ) -> None:
        """Atualiza regras em tempo de execução sem reiniciar o observador."""
        with self._lock:
            if config is not None:
                self.config = config
            self.enabled_categories = enabled_categories

    def start(self) -> None:
        """Inicia o monitoramento da pasta."""
        with self._lock:
            if self._running:
                return
            handler = _FolderEventHandler(self)
            observer = Observer()
            observer.schedule(handler, str(self.folder), recursive=False)
            observer.start()
            self._observer = observer
            self._running = True

    def stop(self) -> None:
        """Cancela timers pendentes e encerra o observador."""
        with self._lock:
            self._running = False
            timers = list(self._timers.values())
            self._timers.clear()
            observer = self._observer
            self._observer = None

        for timer in timers:
            timer.cancel()

        if observer is not None:
            observer.stop()
            observer.join(timeout=3.0)

    def schedule_path(self, file_path: Path) -> None:
        """Agenda organização de um arquivo recém-criado com debounce."""
        resolved_folder = self.folder.resolve()
        try:
            if file_path.parent.resolve() != resolved_folder:
                return
        except OSError:
            return

        with self._lock:
            if not self._running:
                return
            existing = self._timers.pop(file_path, None)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(
                self.debounce_seconds,
                self._process_file,
                args=(file_path,),
            )
            timer.daemon = True
            self._timers[file_path] = timer
            timer.start()

    def _process_file(self, file_path: Path) -> None:
        with self._lock:
            self._timers.pop(file_path, None)
            if not self._running or not file_path.exists() or not file_path.is_file():
                return
            cfg = self.config
            enabled = set(self.enabled_categories) if self.enabled_categories is not None else None

        try:
            plan = plan_organization(
                folder=self.folder,
                config=cfg,
                enabled_categories=enabled,
                only_files=[file_path],
            )
            if not plan.moves:
                return
            result = apply_plan(plan, dry_run=False, history_path=self.history_path)
        except OSError:
            return

        if (result.moved or result.failed) and self.on_organized is not None:
            self.on_organized(result)
