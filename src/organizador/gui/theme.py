"""Tokens visuais e folha de estilo QSS para temas Escuro e Claro."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    """Conjunto completo de cores de um tema da interface."""

    name: str
    bg_window: str
    bg_surface: str
    bg_elevated: str
    bg_hover: str
    bg_input: str
    border: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_soft: str


DARK_PALETTE = ThemePalette(
    name="dark",
    bg_window="#0B0F17",
    bg_surface="#131926",
    bg_elevated="#1A2233",
    bg_hover="#232D42",
    bg_input="#0F141F",
    border="#252F44",
    border_strong="#364461",
    text_primary="#F1F5F9",
    text_secondary="#94A3B8",
    text_muted="#64748B",
    accent="#3B82F6",
    accent_hover="#2563EB",
    accent_soft="rgba(59, 130, 246, 0.16)",
    success="#10B981",
    success_soft="rgba(16, 185, 129, 0.15)",
    warning="#F59E0B",
    warning_soft="rgba(245, 158, 11, 0.15)",
    danger="#EF4444",
    danger_soft="rgba(239, 68, 68, 0.15)",
)

LIGHT_PALETTE = ThemePalette(
    name="light",
    bg_window="#F3F6FB",
    bg_surface="#FFFFFF",
    bg_elevated="#F8FAFC",
    bg_hover="#EDF2F9",
    bg_input="#F8FAFC",
    border="#E2E8F0",
    border_strong="#CBD5E1",
    text_primary="#0F172A",
    text_secondary="#475569",
    text_muted="#64748B",
    accent="#2563EB",
    accent_hover="#1D4ED8",
    accent_soft="rgba(37, 99, 235, 0.10)",
    success="#059669",
    success_soft="rgba(5, 150, 105, 0.11)",
    warning="#D97706",
    warning_soft="rgba(217, 119, 6, 0.11)",
    danger="#DC2626",
    danger_soft="rgba(220, 38, 38, 0.10)",
)

CATEGORY_COLORS: dict[str, str] = {
    "Imagens": "#38BDF8",
    "Documentos": "#3B82F6",
    "Áudios e Vídeos": "#A855F7",
    "Compactados": "#F59E0B",
    "Executáveis": "#F43F5E",
    "Código e Dados": "#10B981",
    "Outros": "#64748B",
}


def get_palette(theme_name: str) -> ThemePalette:
    """Retorna a paleta correspondente ao nome do tema."""
    return LIGHT_PALETTE if theme_name == "light" else DARK_PALETTE


def get_category_color(category: str) -> str:
    """Retorna a cor semântica de destaque para uma categoria."""
    if category in CATEGORY_COLORS:
        return CATEGORY_COLORS[category]
    fallback = ("#06B6D4", "#8B5CF6", "#EC4899", "#14B8A6", "#F97316")
    return fallback[sum(ord(ch) for ch in category) % len(fallback)]


def build_stylesheet(palette: ThemePalette) -> str:
    """Gera a folha de estilo QSS completa para a janela principal e diálogos."""
    p = palette
    return f"""
    QMainWindow, QDialog {{
        background-color: {p.bg_window};
        color: {p.text_primary};
        font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
    }}

    QWidget {{
        color: {p.text_primary};
        font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", sans-serif;
    }}

    QLabel {{
        background: transparent;
    }}

    QLabel#AppTitle {{
        font-size: 18px;
        font-weight: 700;
        color: {p.text_primary};
    }}

    QLabel#AppSubtitle {{
        font-size: 12px;
        color: {p.text_secondary};
    }}

    QLabel#SectionTitle {{
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.4px;
        color: {p.text_secondary};
    }}

    QLabel#FolderPathLabel {{
        font-family: "Cascadia Mono", "Consolas", monospace;
        font-size: 12px;
        color: {p.text_primary};
        background-color: {p.bg_input};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 6px 10px;
    }}

    QLabel#StatsBadge {{
        font-size: 12px;
        font-weight: 600;
        color: {p.accent};
        background-color: {p.accent_soft};
        border-radius: 10px;
        padding: 4px 10px;
    }}

    QLabel#WatchStatusBadge {{
        font-size: 11px;
        font-weight: 600;
        color: {p.text_secondary};
        background-color: {p.bg_elevated};
        border: 1px solid {p.border};
        border-radius: 9px;
        padding: 3px 9px;
    }}

    QLabel#WatchStatusBadge[active="true"] {{
        color: {p.success};
        background-color: {p.success_soft};
        border: 1px solid {p.success};
    }}

    QFrame#Card {{
        background-color: {p.bg_surface};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}

    QFrame#DropZone {{
        background-color: {p.bg_surface};
        border: 1.5px dashed {p.border_strong};
        border-radius: 14px;
    }}

    QFrame#DropZone[dragging="true"] {{
        background-color: {p.accent_soft};
        border: 2px dashed {p.accent};
    }}

    QFrame#ToastBanner {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border_strong};
        border-radius: 10px;
    }}

    QFrame#ToastBanner[tone="success"] {{
        background-color: {p.success_soft};
        border: 1px solid {p.success};
    }}

    QFrame#ToastBanner[tone="warning"] {{
        background-color: {p.warning_soft};
        border: 1px solid {p.warning};
    }}

    QFrame#ToastBanner[tone="error"] {{
        background-color: {p.danger_soft};
        border: 1px solid {p.danger};
    }}

    QPushButton {{
        background-color: {p.bg_elevated};
        color: {p.text_primary};
        border: 1px solid {p.border};
        border-radius: 9px;
        padding: 7px 14px;
        font-size: 13px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background-color: {p.bg_hover};
        border-color: {p.border_strong};
    }}

    QPushButton:pressed {{
        background-color: {p.bg_input};
    }}

    QPushButton:disabled {{
        color: {p.text_muted};
        background-color: {p.bg_elevated};
        border-color: {p.border};
    }}

    QPushButton#PrimaryButton {{
        background-color: {p.accent};
        color: #FFFFFF;
        border: 1px solid {p.accent};
        padding: 9px 18px;
        font-weight: 700;
    }}

    QPushButton#PrimaryButton:hover {{
        background-color: {p.accent_hover};
        border-color: {p.accent_hover};
    }}

    QPushButton#PrimaryButton:disabled {{
        background-color: {p.bg_elevated};
        color: {p.text_muted};
        border-color: {p.border};
    }}

    QPushButton#GhostButton {{
        background-color: transparent;
        border: 1px solid transparent;
        color: {p.text_secondary};
        padding: 6px 10px;
    }}

    QPushButton#GhostButton:hover {{
        background-color: {p.bg_hover};
        color: {p.text_primary};
        border-color: {p.border};
    }}

    QPushButton#QuickFolderChip {{
        background-color: {p.bg_elevated};
        color: {p.text_secondary};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
    }}

    QPushButton#QuickFolderChip:hover {{
        background-color: {p.bg_hover};
        color: {p.text_primary};
        border-color: {p.accent};
    }}

    QPushButton#CategoryPill {{
        background-color: {p.bg_elevated};
        color: {p.text_secondary};
        border: 1px solid {p.border};
        border-radius: 13px;
        min-height: 22px;
        padding: 4px 12px;
        font-size: 12px;
        font-weight: 600;
    }}

    QPushButton#CategoryPill:hover {{
        background-color: {p.bg_hover};
        color: {p.text_primary};
    }}

    QPushButton#CategoryPill:checked {{
        background-color: {p.accent_soft};
        color: {p.text_primary};
        border: 1px solid {p.accent};
    }}

    QLineEdit, QPlainTextEdit, QListWidget {{
        background-color: {p.bg_input};
        color: {p.text_primary};
        border: 1px solid {p.border};
        border-radius: 9px;
        padding: 7px 11px;
        selection-background-color: {p.accent};
    }}

    QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus {{
        border-color: {p.accent};
    }}

    QListWidget {{
        padding: 6px;
        outline: 0;
    }}

    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 7px;
        margin-bottom: 2px;
    }}

    QListWidget::item:hover {{
        background-color: {p.bg_hover};
    }}

    QListWidget::item:selected {{
        background-color: {p.accent_soft};
        color: {p.text_primary};
        font-weight: 700;
    }}

    QTableWidget {{
        background-color: {p.bg_surface};
        alternate-background-color: {p.bg_elevated};
        color: {p.text_primary};
        border: 1px solid {p.border};
        border-radius: 10px;
        gridline-color: transparent;
        selection-background-color: {p.accent_soft};
        selection-color: {p.text_primary};
        outline: 0;
    }}

    QTableWidget::item {{
        padding: 8px 10px;
        border-bottom: 1px solid {p.border};
    }}

    QHeaderView::section {{
        background-color: {p.bg_elevated};
        color: {p.text_secondary};
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        padding: 8px 10px;
        border: none;
        border-bottom: 1px solid {p.border};
    }}

    QProgressBar {{
        background-color: {p.bg_elevated};
        border: none;
        border-radius: 3px;
        max-height: 6px;
        min-height: 6px;
        text-align: center;
    }}

    QProgressBar::chunk {{
        background-color: {p.accent};
        border-radius: 3px;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 4px 0;
    }}

    QScrollBar::handle:vertical {{
        background: {p.border_strong};
        border-radius: 4px;
        min-height: 28px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {p.text_muted};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
        height: 0px;
    }}

    QMenu {{
        background-color: {p.bg_surface};
        color: {p.text_primary};
        border: 1px solid {p.border_strong};
        border-radius: 8px;
        padding: 6px;
    }}

    QMenu::item {{
        padding: 6px 16px;
        border-radius: 6px;
    }}

    QMenu::item:selected {{
        background-color: {p.accent_soft};
        color: {p.text_primary};
    }}
    """
