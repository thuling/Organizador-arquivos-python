"""Widgets customizados para a interface em PySide6."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from organizador.config import OrganizerConfig
from organizador.gui.icons import svg_icon
from organizador.gui.theme import ThemePalette, get_category_color


def make_dot_icon(color_hex: str, diameter: int = 10) -> QIcon:
    """Cria um pequeno ícone circular colorido para indicar categorias."""
    scale = 2
    px = diameter * scale
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, px - 2, px - 2)
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)


class FlowLayout(QLayout):
    """Layout responsivo que quebra widgets automaticamente para a linha seguinte."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 8) -> None:
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(left, top, -right, -bottom)
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self._items:
            widget_size = item.sizeHint()
            next_x = x + widget_size.width() + self._spacing
            if next_x - self._spacing > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + self._spacing
                next_x = x + widget_size.width() + self._spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), widget_size))

            x = next_x
            line_height = max(line_height, widget_size.height())

        return y + line_height - rect.y() + bottom


class ToggleSwitch(QCheckBox):
    """Switch deslizante moderno para substituir checkboxes padrão."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(42, 24)
        self._accent = QColor("#3B82F6")
        self._track_off = QColor("#334155")
        self._thumb = QColor("#FFFFFF")

    def set_palette_colors(self, accent: str, track_off: str) -> None:
        self._accent = QColor(accent)
        self._track_off = QColor(track_off)
        self.update()

    def hitButton(self, pos: QPoint) -> bool:
        return self.contentsRect().contains(pos)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        track_color = self._accent if self.isChecked() else self._track_off
        if not self.isEnabled():
            track_color = track_color.darker(135)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(0, 1, rect.width(), rect.height() - 2, 11, 11)

        thumb_x = rect.width() - 20 if self.isChecked() else 3
        painter.setBrush(self._thumb)
        painter.setPen(QPen(QColor(0, 0, 0, 28), 1))
        painter.drawEllipse(thumb_x, 3, 18, 18)
        painter.end()


class CategoryPill(QPushButton):
    """Chip interativo para ativar/desativar categoria e exibir contagem."""

    def __init__(self, category: str, count: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.category = category
        self._count = count
        self.setObjectName("CategoryPill")
        self.setCheckable(True)
        self.setChecked(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(make_dot_icon(get_category_color(category), diameter=9))
        self.setIconSize(QSize(10, 10))
        self.set_count(count)

    def set_count(self, count: int) -> None:
        self._count = count
        self.setText(f"{self.category} ({count})")


class DropZoneCard(QFrame):
    """Cartão de seleção e drag-and-drop de pasta com atalhos rápidos."""

    folder_dropped = Signal(Path)
    browse_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setProperty("dragging", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.icon_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title_label = QLabel("Arraste uma pasta aqui ou escolha no computador")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        title_row.addWidget(self.title_label)

        self.stats_badge = QLabel("Nenhuma pasta selecionada")
        self.stats_badge.setObjectName("StatsBadge")
        title_row.addWidget(self.stats_badge)
        title_row.addStretch()
        info_col.addLayout(title_row)

        self.path_label = QLabel("Dica: solte uma pasta do Explorador de Arquivos nesta área")
        self.path_label.setObjectName("FolderPathLabel")
        self.path_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info_col.addWidget(self.path_label)

        top_row.addLayout(info_col, stretch=1)

        self.browse_button = QPushButton("Escolher pasta")
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self.browse_requested.emit)
        top_row.addWidget(self.browse_button)

        layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        shortcuts_label = QLabel("Atalhos:")
        shortcuts_label.setObjectName("SectionTitle")
        bottom_row.addWidget(shortcuts_label)

        self.quick_buttons: list[tuple[QPushButton, Path]] = []
        home = Path.home()
        candidates = [
            ("Downloads", home / "Downloads"),
            ("Documentos", home / "Documents"),
            ("Área de Trabalho", home / "Desktop"),
            ("Imagens", home / "Pictures"),
        ]
        for label, folder in candidates:
            if folder.exists() and folder.is_dir():
                btn = QPushButton(label)
                btn.setObjectName("QuickFolderChip")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _checked=False, p=folder: self.folder_dropped.emit(p))
                bottom_row.addWidget(btn)
                self.quick_buttons.append((btn, folder))

        bottom_row.addStretch()

        self.watch_status_badge = QLabel("Monitor inativo")
        self.watch_status_badge.setObjectName("WatchStatusBadge")
        self.watch_status_badge.setProperty("active", False)
        bottom_row.addWidget(self.watch_status_badge)

        watch_label = QLabel("Monitorar em tempo real")
        watch_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        bottom_row.addWidget(watch_label)

        self.watch_switch = ToggleSwitch()
        bottom_row.addWidget(self.watch_switch)

        layout.addLayout(bottom_row)

    def apply_palette(self, palette: ThemePalette) -> None:
        self.icon_label.setPixmap(svg_icon("upload", palette.accent, 22).pixmap(22, 22))
        self.icon_label.setStyleSheet(
            f"background-color: {palette.accent_soft}; border-radius: 10px;"
        )
        self.browse_button.setIcon(svg_icon("folder_plus", palette.text_primary, 16))
        self.watch_switch.set_palette_colors(palette.success, palette.border_strong)

    def set_folder_info(self, folder: Path | None, summary: str) -> None:
        if folder is None:
            self.title_label.setText("Arraste uma pasta aqui ou escolha no computador")
            self.path_label.setText("Dica: solte uma pasta do Explorador de Arquivos nesta área")
            self.stats_badge.setText("Aguardando pasta")
        else:
            self.title_label.setText(folder.name or str(folder))
            self.path_label.setText(str(folder))
            self.stats_badge.setText(summary)

    def set_watch_active(self, active: bool) -> None:
        self.watch_status_badge.setText("Monitor ativo" if active else "Monitor inativo")
        self.watch_status_badge.setProperty("active", active)
        self.watch_status_badge.style().unpolish(self.watch_status_badge)
        self.watch_status_badge.style().polish(self.watch_status_badge)

    def _set_dragging(self, dragging: bool) -> None:
        if self.property("dragging") != dragging:
            self.setProperty("dragging", dragging)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local = Path(url.toLocalFile())
                if local.exists() and local.is_dir():
                    event.acceptProposedAction()
                    self._set_dragging(True)
                    return
        event.ignore()

    def dragLeaveEvent(self, _event) -> None:
        self._set_dragging(False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_dragging(False)
        for url in event.mimeData().urls():
            local = Path(url.toLocalFile())
            if local.exists() and local.is_dir():
                self.folder_dropped.emit(local)
                event.acceptProposedAction()
                return
        event.ignore()


class ConfigDialog(QDialog):
    """Diálogo visual para editar categorias, extensões e preferências."""

    def __init__(self, config: OrganizerConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Regras de Organização")
        self.setMinimumSize(760, 490)
        self.resize(780, 500)

        self._working_categories: dict[str, list[str]] = {
            k: list(v) for k, v in config.categories.items()
        }
        self._current_category: str | None = None
        self._result_config: OrganizerConfig | None = None
        self._base_config = config

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        header = QLabel("Personalize pastas de destino e extensões")
        header.setStyleSheet("font-size: 16px; font-weight: 700;")
        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(14)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)
        left_title = QLabel("CATEGORIAS")
        left_title.setObjectName("SectionTitle")
        left_col.addWidget(left_title)

        self.cat_list = QListWidget()
        self.cat_list.currentTextChanged.connect(self._on_category_selected)
        left_col.addWidget(self.cat_list, stretch=1)

        cat_actions = QHBoxLayout()
        self.add_cat_btn = QPushButton("+ Nova")
        self.add_cat_btn.clicked.connect(self._add_category)
        self.remove_cat_btn = QPushButton("Remover")
        self.remove_cat_btn.clicked.connect(self._remove_category)
        cat_actions.addWidget(self.add_cat_btn)
        cat_actions.addWidget(self.remove_cat_btn)
        left_col.addLayout(cat_actions)

        body.addLayout(left_col, stretch=1)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        name_lbl = QLabel("NOME DA PASTA")
        name_lbl.setObjectName("SectionTitle")
        right_col.addWidget(name_lbl)

        self.name_input = QLineEdit()
        self.name_input.editingFinished.connect(self._rename_current_category)
        right_col.addWidget(self.name_input)

        ext_lbl = QLabel("EXTENSÕES (SEPARADAS POR VÍRGULA)")
        ext_lbl.setObjectName("SectionTitle")
        right_col.addWidget(ext_lbl)

        self.ext_input = QPlainTextEdit()
        self.ext_input.setPlaceholderText(".jpg, .png, .webp")
        self.ext_input.textChanged.connect(self._update_current_extensions)
        right_col.addWidget(self.ext_input, stretch=1)

        self.include_others_chk = QCheckBox("Mover extensões desconhecidas para 'Outros'")
        self.include_others_chk.setChecked(config.include_others)
        right_col.addWidget(self.include_others_chk)

        self.ignore_hidden_chk = QCheckBox("Ignorar arquivos ocultos (iniciados por '.')")
        self.ignore_hidden_chk.setChecked(config.ignore_hidden)
        right_col.addWidget(self.ignore_hidden_chk)

        body.addLayout(right_col, stretch=2)
        root.addLayout(body, stretch=1)

        footer = QHBoxLayout()
        self.reset_btn = QPushButton("Restaurar padrão")
        self.reset_btn.clicked.connect(self._restore_defaults)
        footer.addWidget(self.reset_btn)
        footer.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Salvar regras")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._accept_and_save)

        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)
        root.addLayout(footer)

        self._reload_list()

    def result_config(self) -> OrganizerConfig | None:
        return self._result_config

    def _reload_list(self, select_name: str | None = None) -> None:
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        for name in self._working_categories:
            self.cat_list.addItem(name)
        self.cat_list.blockSignals(False)

        if self.cat_list.count() > 0:
            row = 0
            if select_name and select_name in self._working_categories:
                row = list(self._working_categories.keys()).index(select_name)
            self.cat_list.setCurrentRow(row)
        else:
            self._current_category = None
            self.name_input.clear()
            self.ext_input.clear()

    def _on_category_selected(self, name: str) -> None:
        if not name or name not in self._working_categories:
            return
        self._current_category = name
        self.name_input.blockSignals(True)
        self.name_input.setText(name)
        self.name_input.blockSignals(False)

        self.ext_input.blockSignals(True)
        self.ext_input.setPlainText(", ".join(self._working_categories[name]))
        self.ext_input.blockSignals(False)

    def _rename_current_category(self) -> None:
        if not self._current_category:
            return
        new_name = self.name_input.text().strip()
        if not new_name or new_name == self._current_category:
            return
        if new_name in self._working_categories:
            QMessageBox.warning(self, "Nome duplicado", f"A categoria '{new_name}' já existe.")
            self.name_input.setText(self._current_category)
            return

        rebuilt: dict[str, list[str]] = {}
        for k, v in self._working_categories.items():
            rebuilt[new_name if k == self._current_category else k] = v
        self._working_categories = rebuilt
        self._current_category = new_name
        self._reload_list(select_name=new_name)

    def _update_current_extensions(self) -> None:
        if not self._current_category:
            return
        raw = self.ext_input.toPlainText()
        parts = [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]
        self._working_categories[self._current_category] = parts

    def _add_category(self) -> None:
        name, ok = QInputDialog.getText(self, "Nova categoria", "Nome da pasta destino:")
        clean = name.strip()
        if not ok or not clean:
            return
        if clean in self._working_categories:
            QMessageBox.warning(self, "Categoria existente", f"'{clean}' já está cadastrada.")
            return
        self._working_categories[clean] = []
        self._reload_list(select_name=clean)

    def _remove_category(self) -> None:
        if not self._current_category:
            return
        if len(self._working_categories) <= 1:
            QMessageBox.information(self, "Aviso", "Mantenha pelo menos uma categoria ativa.")
            return
        del self._working_categories[self._current_category]
        self._reload_list()

    def _restore_defaults(self) -> None:
        defaults = OrganizerConfig.default()
        self._working_categories = {k: list(v) for k, v in defaults.categories.items()}
        self.include_others_chk.setChecked(defaults.include_others)
        self.ignore_hidden_chk.setChecked(defaults.ignore_hidden)
        self._reload_list()

    def _accept_and_save(self) -> None:
        self._rename_current_category()
        self._update_current_extensions()
        candidate = OrganizerConfig.from_dict(
            {
                **self._base_config.to_dict(),
                "categories": self._working_categories,
                "include_others": self.include_others_chk.isChecked(),
                "ignore_hidden": self.ignore_hidden_chk.isChecked(),
            }
        )
        self._result_config = candidate
        self.accept()
