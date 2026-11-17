"""Janela principal do Organizador de Arquivos em PySide6."""

from __future__ import annotations

import contextlib
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from organizador import APP_DISPLAY_NAME, __version__
from organizador.config import (
    ConfigError,
    OrganizerConfig,
    load_config,
    save_config,
)
from organizador.core import (
    OrganizationPlan,
    OrganizationResult,
    apply_plan,
    format_size,
    plan_organization,
)
from organizador.gui.icons import svg_icon
from organizador.gui.theme import build_stylesheet, get_category_color, get_palette
from organizador.gui.widgets import (
    CategoryPill,
    ConfigDialog,
    DropZoneCard,
    FlowLayout,
    make_dot_icon,
)
from organizador.history import get_latest_batch, undo_last
from organizador.watcher import FolderWatcher


def get_resource_path(relative_path: str) -> Path:
    """Resolve caminho de assets tanto em dev quanto empacotado via PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[3]
    return base / relative_path


class OrganizeWorker(QThread):
    """Worker assíncrono para executar a organização sem travar a interface."""

    progress = Signal(int, int)
    completed = Signal(object)

    def __init__(self, plan: OrganizationPlan, history_path: Path | None) -> None:
        super().__init__()
        self._plan = plan
        self._history_path = history_path

    def run(self) -> None:
        result = apply_plan(
            plan=self._plan,
            dry_run=False,
            history_path=self._history_path,
            progress_callback=lambda current, total, _m: self.progress.emit(current, total),
        )
        self.completed.emit(result)


class MainWindow(QMainWindow):
    """Janela principal do Organizador de Arquivos."""

    auto_organized_signal = Signal(object)

    def __init__(
        self,
        initial_folder: Path | None = None,
        config_path: Path | None = None,
        history_path: Path | None = None,
        enable_tray: bool = True,
        sync_worker: bool = False,
    ) -> None:
        super().__init__()
        self.config_path = config_path
        self.history_path = history_path
        self.enable_tray = enable_tray
        self.sync_worker = sync_worker

        self.current_folder: Path | None = None
        self.current_plan: OrganizationPlan | None = None
        self.category_pills: dict[str, CategoryPill] = {}
        self._worker: OrganizeWorker | None = None
        self._watcher: FolderWatcher | None = None
        self._tray_icon: QSystemTrayIcon | None = None
        self._force_quit = False

        try:
            self.config = load_config(self.config_path)
            config_warning = None
        except ConfigError as exc:
            self.config = OrganizerConfig.default()
            config_warning = str(exc)

        self.setWindowTitle(f"{APP_DISPLAY_NAME} · v{__version__}")
        self.setMinimumSize(940, 680)
        self.resize(1040, 760)

        self._app_icon = self._load_app_icon()
        if not self._app_icon.isNull():
            self.setWindowIcon(self._app_icon)

        self.auto_organized_signal.connect(self._handle_auto_organized)

        self._build_ui()
        self._apply_theme()
        self._rebuild_category_pills()
        self._setup_tray()
        self._refresh_undo_state()

        if config_warning:
            self._show_toast(
                f"Configuração inválida; usando padrão ({config_warning})",
                tone="warning",
            )

        if initial_folder is not None:
            self.set_folder(initial_folder)

    def _load_app_icon(self) -> QIcon:
        ico = get_resource_path("assets/app.ico")
        png = get_resource_path("assets/app.png")
        if ico.exists():
            return QIcon(str(ico))
        if png.exists():
            return QIcon(str(png))
        return svg_icon("sparkles", "#3B82F6", 24)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        # 1. Header
        header = QHBoxLayout()
        header.setSpacing(12)

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(36, 36)
        if not self._app_icon.isNull():
            self.logo_label.setPixmap(self._app_icon.pixmap(36, 36))
        header.addWidget(self.logo_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_lbl = QLabel(APP_DISPLAY_NAME)
        title_lbl.setObjectName("AppTitle")
        subtitle_lbl = QLabel("Prévia segura, desfazer instantâneo e monitoramento em tempo real")
        subtitle_lbl.setObjectName("AppSubtitle")
        title_col.addWidget(title_lbl)
        title_col.addWidget(subtitle_lbl)
        header.addLayout(title_col)
        header.addStretch()

        self.log_toggle_btn = QPushButton("Atividades")
        self.log_toggle_btn.setObjectName("GhostButton")
        self.log_toggle_btn.setCheckable(True)
        self.log_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_toggle_btn.toggled.connect(self._toggle_activity_drawer)
        header.addWidget(self.log_toggle_btn)

        self.rules_button = QPushButton("Regras")
        self.rules_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rules_button.clicked.connect(self._open_rules_dialog)
        header.addWidget(self.rules_button)

        self.theme_button = QPushButton("Tema claro")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_button)

        root.addLayout(header)

        # 2. DropZone Card
        self.drop_card = DropZoneCard()
        self.drop_card.folder_dropped.connect(self.set_folder)
        self.drop_card.browse_requested.connect(self.choose_folder)
        self.drop_card.watch_switch.toggled.connect(self._on_watch_toggled)
        root.addWidget(self.drop_card)

        # 3. Category Pills Card
        cat_card = QFrame()
        cat_card.setObjectName("Card")
        cat_layout = QVBoxLayout(cat_card)
        cat_layout.setContentsMargins(16, 12, 16, 14)
        cat_layout.setSpacing(10)

        cat_header = QHBoxLayout()
        cat_title = QLabel("CATEGORIAS ATIVAS")
        cat_title.setObjectName("SectionTitle")
        cat_header.addWidget(cat_title)
        cat_header.addStretch()

        self.select_all_btn = QPushButton("Marcar todas")
        self.select_all_btn.setObjectName("GhostButton")
        self.select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_btn.clicked.connect(lambda: self._set_all_categories(True))
        cat_header.addWidget(self.select_all_btn)

        self.clear_all_btn = QPushButton("Limpar")
        self.clear_all_btn.setObjectName("GhostButton")
        self.clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_all_btn.clicked.connect(lambda: self._set_all_categories(False))
        cat_header.addWidget(self.clear_all_btn)

        cat_layout.addLayout(cat_header)

        self.pills_container = QWidget()
        self.pills_flow = FlowLayout(self.pills_container, margin=0, spacing=8)
        cat_layout.addWidget(self.pills_container)

        root.addWidget(cat_card)

        # 4. Preview Card (Empty state / Table)
        preview_card = QFrame()
        preview_card.setObjectName("Card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 14, 16, 14)
        preview_layout.setSpacing(10)

        preview_header = QHBoxLayout()
        preview_title = QLabel("PRÉ-VISUALIZAÇÃO ANTES DE MOVER (DRY-RUN)")
        preview_title.setObjectName("SectionTitle")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar arquivo ou extensão...")
        self.search_input.setMaximumWidth(260)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._render_preview_rows)
        preview_header.addWidget(self.search_input)

        preview_layout.addLayout(preview_header)

        self.preview_stack = QStackedWidget()

        # Empty State Page
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(8)
        self.empty_icon = QLabel()
        self.empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title = QLabel("Escolha ou arraste uma pasta para visualizar")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.empty_subtitle = QLabel(
            "Nenhum arquivo será movido até você clicar em 'Organizar agora'."
        )
        self.empty_subtitle.setObjectName("AppSubtitle")
        self.empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_icon)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_subtitle)
        self.preview_stack.addWidget(empty_page)

        # Table Page
        self.preview_table = QTableWidget(0, 4)
        self.preview_table.setHorizontalHeaderLabels(
            ["Arquivo", "Pasta destino", "Tamanho", "Status"]
        )
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setShowGrid(False)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.verticalHeader().setDefaultSectionSize(36)

        hdr = self.preview_table.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        if size_hdr := self.preview_table.horizontalHeaderItem(2):
            size_hdr.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.preview_stack.addWidget(self.preview_table)
        preview_layout.addWidget(self.preview_stack, stretch=1)

        root.addWidget(preview_card, stretch=1)

        # 5. Collapsible Activity Log
        self.activity_card = QFrame()
        self.activity_card.setObjectName("Card")
        self.activity_card.setVisible(False)
        act_layout = QVBoxLayout(self.activity_card)
        act_layout.setContentsMargins(14, 10, 14, 12)
        act_layout.setSpacing(6)
        act_title = QLabel("HISTÓRICO DA SESSÃO")
        act_title.setObjectName("SectionTitle")
        act_layout.addWidget(act_title)

        self.activity_log = QPlainTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(110)
        act_layout.addWidget(self.activity_log)
        root.addWidget(self.activity_card)

        # 6. Toast / Feedback Banner
        self.toast_banner = QFrame()
        self.toast_banner.setObjectName("ToastBanner")
        self.toast_banner.setProperty("tone", "info")
        self.toast_banner.setVisible(False)
        toast_layout = QHBoxLayout(self.toast_banner)
        toast_layout.setContentsMargins(14, 9, 12, 9)
        self.toast_label = QLabel("")
        self.toast_label.setStyleSheet("font-weight: 600;")
        toast_layout.addWidget(self.toast_label, stretch=1)
        toast_close = QPushButton("Fechar")
        toast_close.setObjectName("GhostButton")
        toast_close.clicked.connect(lambda: self.toast_banner.setVisible(False))
        toast_layout.addWidget(toast_close)
        root.addWidget(self.toast_banner)

        # 7. Progress + Action Footer
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.undo_button = QPushButton("Desfazer última")
        self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_button.clicked.connect(self.undo_last_action)
        footer.addWidget(self.undo_button)

        footer.addStretch()

        self.refresh_button = QPushButton("Atualizar prévia")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.clicked.connect(self.refresh_preview)
        self.refresh_button.setEnabled(False)
        footer.addWidget(self.refresh_button)

        self.organize_button = QPushButton("Organizar agora")
        self.organize_button.setObjectName("PrimaryButton")
        self.organize_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.organize_button.clicked.connect(self.organize_now)
        self.organize_button.setEnabled(False)
        footer.addWidget(self.organize_button)

        root.addLayout(footer)

    def _apply_theme(self) -> None:
        palette = get_palette(self.config.theme)
        self.setStyleSheet(build_stylesheet(palette))

        is_dark = palette.name == "dark"
        self.theme_button.setText("Tema claro" if is_dark else "Tema escuro")
        self.theme_button.setIcon(svg_icon("sun" if is_dark else "moon", palette.text_primary, 16))
        self.rules_button.setIcon(svg_icon("sliders", palette.text_primary, 16))
        self.log_toggle_btn.setIcon(svg_icon("terminal", palette.text_secondary, 16))
        self.undo_button.setIcon(svg_icon("undo", palette.text_primary, 16))
        self.refresh_button.setIcon(svg_icon("refresh", palette.text_primary, 16))
        self.organize_button.setIcon(svg_icon("sparkles", "#FFFFFF", 16))
        self.empty_icon.setPixmap(svg_icon("folder", palette.text_muted, 44).pixmap(44, 44))
        self.drop_card.apply_palette(palette)

    def toggle_theme(self) -> None:
        self.config.theme = "light" if self.config.theme == "dark" else "dark"
        self._apply_theme()
        with contextlib.suppress(OSError):
            save_config(self.config, self.config_path)

    def _setup_tray(self) -> None:
        if not self.enable_tray or not QSystemTrayIcon.isSystemTrayAvailable():
            return

        tray = QSystemTrayIcon(self._app_icon, self)
        tray.setToolTip(APP_DISPLAY_NAME)

        menu = QMenu(self)
        open_act = QAction("Abrir Organizador", self)
        open_act.triggered.connect(self._restore_from_tray)
        menu.addAction(open_act)

        self._tray_pause_act = QAction("Pausar monitoramento", self)
        self._tray_pause_act.setEnabled(False)
        self._tray_pause_act.triggered.connect(
            lambda: self.drop_card.watch_switch.setChecked(False)
        )
        menu.addAction(self._tray_pause_act)

        menu.addSeparator()
        quit_act = QAction("Sair", self)
        quit_act.triggered.connect(self._quit_app)
        menu.addAction(quit_act)

        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self._tray_icon = tray

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self) -> None:
        self._force_quit = True
        self._stop_watcher()
        if self._tray_icon is not None:
            self._tray_icon.hide()
        self.close()

    def _rebuild_category_pills(self) -> None:
        previously_checked = {
            name: pill.isChecked() for name, pill in self.category_pills.items()
        }
        while self.pills_flow.count():
            item = self.pills_flow.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        self.category_pills.clear()
        for cat in self.config.all_category_names():
            pill = CategoryPill(cat, count=0)
            if cat in previously_checked:
                pill.setChecked(previously_checked[cat])
            pill.toggled.connect(self._on_category_toggled)
            self.pills_flow.addWidget(pill)
            self.category_pills[cat] = pill

    def _on_category_toggled(self, _checked: bool) -> None:
        self.refresh_preview()
        if self._watcher is not None:
            self._watcher.update_rules(
                config=self.config,
                enabled_categories=self._enabled_categories(),
            )

    def _set_all_categories(self, checked: bool) -> None:
        for pill in self.category_pills.values():
            pill.blockSignals(True)
            pill.setChecked(checked)
            pill.blockSignals(False)
        self._on_category_toggled(checked)

    def _enabled_categories(self) -> set[str]:
        return {name for name, pill in self.category_pills.items() if pill.isChecked()}

    def choose_folder(self) -> None:
        start_dir = str(self.current_folder or Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Escolha a pasta para organizar",
            start_dir,
        )
        if selected:
            self.set_folder(Path(selected))

    def set_folder(self, folder: Path) -> None:
        target = Path(folder)
        if not target.exists() or not target.is_dir():
            self._show_toast(f"Pasta não encontrada: {target}", tone="error")
            return

        was_watching = self._watcher is not None and self._watcher.is_running
        if was_watching:
            self._stop_watcher()

        self.current_folder = target
        self.refresh_button.setEnabled(True)
        self.refresh_preview()
        self._refresh_undo_state()

        if was_watching:
            self._start_watcher()

    def refresh_preview(self) -> None:
        if self.current_folder is None:
            self.preview_stack.setCurrentIndex(0)
            self.organize_button.setEnabled(False)
            self.organize_button.setText("Organizar agora")
            self.drop_card.set_folder_info(None, "")
            return

        full_plan = plan_organization(self.current_folder, config=self.config)
        for cat, pill in self.category_pills.items():
            pill.set_count(full_plan.category_counts.get(cat, 0))

        enabled = self._enabled_categories()
        filtered_plan = plan_organization(
            self.current_folder,
            config=self.config,
            enabled_categories=enabled,
        )
        self.current_plan = filtered_plan

        count = len(filtered_plan.moves)
        if count > 0:
            summary = f"{count} arquivo(s) · {format_size(filtered_plan.total_bytes)}"
            self.organize_button.setEnabled(True)
            self.organize_button.setText(f"Organizar {count} arquivo(s)")
        else:
            summary = "Pasta organizada"
            self.organize_button.setEnabled(False)
            self.organize_button.setText("Organizar agora")

        self.drop_card.set_folder_info(self.current_folder, summary)
        self._render_preview_rows()

    def _render_preview_rows(self) -> None:
        if self.current_plan is None or not self.current_plan.moves:
            self.preview_table.setRowCount(0)
            if self.current_folder is not None:
                self.empty_title.setText("Tudo organizado por aqui!")
                self.empty_subtitle.setText(
                    "Nenhum arquivo pendente corresponde às categorias selecionadas."
                )
            else:
                self.empty_title.setText("Escolha ou arraste uma pasta para visualizar")
                self.empty_subtitle.setText(
                    "Nenhum arquivo será movido até você clicar em 'Organizar agora'."
                )
            self.preview_stack.setCurrentIndex(0)
            return

        query = self.search_input.text().strip().lower()
        moves = [
            m
            for m in self.current_plan.moves
            if not query
            or query in m.source.name.lower()
            or query in m.category.lower()
        ]

        if not moves:
            self.preview_table.setRowCount(0)
            self.empty_title.setText("Nenhum arquivo encontrado no filtro")
            self.empty_subtitle.setText("Limpe a busca para visualizar os arquivos pendentes.")
            self.preview_stack.setCurrentIndex(0)
            return

        self.preview_stack.setCurrentIndex(1)
        self.preview_table.setRowCount(len(moves))

        palette = get_palette(self.config.theme)
        for row, move in enumerate(moves):
            name_item = QTableWidgetItem(move.source.name)
            name_item.setToolTip(str(move.source))

            dest_text = f"{move.category}/{move.destination.name}"
            dest_item = QTableWidgetItem(dest_text)
            dest_item.setIcon(make_dot_icon(get_category_color(move.category), diameter=9))

            size_item = QTableWidgetItem(format_size(move.size_bytes))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if move.renamed:
                status_item = QTableWidgetItem("Renomeado (colisão)")
                status_item.setForeground(QColor(palette.warning))
            else:
                status_item = QTableWidgetItem("Pronto para mover")
                status_item.setForeground(QColor(palette.success))

            self.preview_table.setItem(row, 0, name_item)
            self.preview_table.setItem(row, 1, dest_item)
            self.preview_table.setItem(row, 2, size_item)
            self.preview_table.setItem(row, 3, status_item)

    def organize_now(self) -> None:
        if self.current_plan is None or not self.current_plan.moves:
            return
        if self._worker is not None and self._worker.isRunning():
            return

        if self.sync_worker:
            result = apply_plan(
                plan=self.current_plan,
                dry_run=False,
                history_path=self.history_path,
            )
            self._on_organize_finished(result)
            return

        self._set_busy(True, total=len(self.current_plan.moves))
        self._worker = OrganizeWorker(self.current_plan, self.history_path)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.completed.connect(self._on_organize_finished)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_worker_progress(self, current: int, total: int) -> None:
        self.progress_bar.setMaximum(max(1, total))
        self.progress_bar.setValue(current)

    def _on_organize_finished(self, result: OrganizationResult) -> None:
        self._worker = None
        self._set_busy(False)
        self.refresh_preview()
        self._refresh_undo_state()

        moved_count = len(result.moved)
        failed_count = len(result.failed)

        for src, dst, cat in result.moved:
            self._append_log(f"Movido: {src.name} -> {cat}/{dst.name}")
        for src, err in result.failed:
            self._append_log(f"ERRO: {src.name} ({err})")

        if failed_count == 0 and moved_count > 0:
            self._show_toast(
                f"{moved_count} arquivo(s) organizado(s) com sucesso!",
                tone="success",
            )
        elif failed_count > 0:
            self._show_toast(
                f"{moved_count} movido(s), {failed_count} falha(s) (verifique Atividades).",
                tone="warning",
            )

    def undo_last_action(self) -> None:
        result = undo_last(folder=self.current_folder, history_path=self.history_path)
        if result is None:
            self._show_toast("Não há organização anterior para desfazer.", tone="warning")
            self._refresh_undo_state()
            return

        restored_count = len(result.restored)
        self._append_log(f"Desfeito: {restored_count} arquivo(s) restaurado(s).")
        if result.errors:
            for path, err in result.errors:
                self._append_log(f"ERRO ao desfazer {path.name}: {err}")
            self._show_toast(
                f"{restored_count} restaurado(s), {len(result.errors)} erro(s).",
                tone="warning",
            )
        else:
            self._show_toast(
                f"Organização desfeita: {restored_count} arquivo(s) restaurado(s).",
                tone="success",
            )

        self.refresh_preview()
        self._refresh_undo_state()

    def _refresh_undo_state(self) -> None:
        batch = get_latest_batch(folder=self.current_folder, history_path=self.history_path)
        if batch is None:
            self.undo_button.setEnabled(False)
            self.undo_button.setText("Desfazer última")
        else:
            self.undo_button.setEnabled(True)
            self.undo_button.setText(f"Desfazer última ({len(batch.moves)})")

    def _open_rules_dialog(self) -> None:
        dialog = ConfigDialog(self.config, parent=self)
        dialog.setStyleSheet(self.styleSheet())
        if dialog.exec() == ConfigDialog.DialogCode.Accepted:
            updated = dialog.result_config()
            if updated is not None:
                self.config = updated
                try:
                    save_config(self.config, self.config_path)
                except OSError as exc:
                    self._show_toast(f"Erro ao salvar config.json: {exc}", tone="error")
                self._rebuild_category_pills()
                self.refresh_preview()
                if self._watcher is not None:
                    self._watcher.update_rules(
                        config=self.config,
                        enabled_categories=self._enabled_categories(),
                    )
                self._show_toast("Regras atualizadas e salvas.", tone="success")

    def _on_watch_toggled(self, checked: bool) -> None:
        if checked:
            if self.current_folder is None:
                self.drop_card.watch_switch.blockSignals(True)
                self.drop_card.watch_switch.setChecked(False)
                self.drop_card.watch_switch.blockSignals(False)
                self._show_toast(
                    "Escolha uma pasta antes de ativar o monitoramento.",
                    tone="warning",
                )
                return
            self._start_watcher()
        else:
            self._stop_watcher()

    def _start_watcher(self) -> None:
        if self.current_folder is None:
            return
        self._stop_watcher()
        try:
            watcher = FolderWatcher(
                folder=self.current_folder,
                config=self.config,
                enabled_categories=self._enabled_categories(),
                history_path=self.history_path,
                on_organized=lambda res: self.auto_organized_signal.emit(res),
            )
            watcher.start()
            self._watcher = watcher
            self.drop_card.set_watch_active(True)
            if self._tray_icon is not None:
                self._tray_pause_act.setEnabled(True)
            self._append_log(f"Monitoramento ativo em: {self.current_folder}")
            self._show_toast("Monitoramento em tempo real ativado.", tone="success")
        except OSError as exc:
            self.drop_card.watch_switch.setChecked(False)
            self._show_toast(f"Falha ao iniciar monitoramento: {exc}", tone="error")

    def _stop_watcher(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None
            self._append_log("Monitoramento pausado.")
        self.drop_card.set_watch_active(False)
        if self._tray_icon is not None:
            self._tray_pause_act.setEnabled(False)

    def _handle_auto_organized(self, result: OrganizationResult) -> None:
        for src, dst, cat in result.moved:
            self._append_log(f"[Auto] {src.name} -> {cat}/{dst.name}")
        for src, err in result.failed:
            self._append_log(f"[Auto ERRO] {src.name}: {err}")

        if result.moved:
            self.refresh_preview()
            self._refresh_undo_state()
            if self._tray_icon is not None and not self.isVisible():
                self._tray_icon.showMessage(
                    APP_DISPLAY_NAME,
                    f"{len(result.moved)} novo(s) arquivo(s) organizado(s) automaticamente.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000,
                )

    def _toggle_activity_drawer(self, visible: bool) -> None:
        self.activity_card.setVisible(visible)

    def _append_log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.appendPlainText(f"[{stamp}] {message}")

    def _show_toast(self, message: str, tone: str = "info") -> None:
        self.toast_label.setText(message)
        self.toast_banner.setProperty("tone", tone)
        self.toast_banner.style().unpolish(self.toast_banner)
        self.toast_banner.style().polish(self.toast_banner)
        self.toast_banner.setVisible(True)

    def _set_busy(self, busy: bool, total: int = 1) -> None:
        self.progress_bar.setVisible(busy)
        self.progress_bar.setMaximum(max(1, total))
        self.progress_bar.setValue(0)
        self.organize_button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy and self.current_folder is not None)
        self.undo_button.setEnabled(not busy)
        self.rules_button.setEnabled(not busy)

    def closeEvent(self, event) -> None:
        if (
            not self._force_quit
            and self._watcher is not None
            and self._watcher.is_running
            and self._tray_icon is not None
        ):
            event.ignore()
            self.hide()
            self._tray_icon.showMessage(
                APP_DISPLAY_NAME,
                "Continuo monitorando sua pasta na bandeja do sistema.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
            return

        self._stop_watcher()
        if self._tray_icon is not None:
            self._tray_icon.hide()
        super().closeEvent(event)


def launch_gui(
    initial_folder: Path | None = None,
    config_path: Path | None = None,
    history_path: Path | None = None,
) -> int:
    """Inicializa a aplicação Qt e exibe a janela principal."""
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)

    window = MainWindow(
        initial_folder=initial_folder,
        config_path=config_path,
        history_path=history_path,
    )
    window.show()
    if owns_app:
        return app.exec()
    return 0
