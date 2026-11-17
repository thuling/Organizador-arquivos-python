"""Renderizador de ícones vetoriais SVG inline para PySide6."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_SVG_PATHS: dict[str, str] = {
    "folder": (
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
    ),
    "folder_plus": (
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
        '<line x1="12" y1="11" x2="12" y2="17"/>'
        '<line x1="9" y1="14" x2="15" y2="14"/>'
    ),
    "play": '<polygon points="6 4 20 12 6 20 6 4"/>',
    "sparkles": (
        '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z"/>'
        '<path d="M19 3v4"/><path d="M21 5h-4"/>'
        '<path d="M5 17v4"/><path d="M7 19H3"/>'
    ),
    "undo": (
        '<path d="M3 7v6h6"/>'
        '<path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/>'
    ),
    "refresh": (
        '<polyline points="23 4 23 10 17 10"/>'
        '<polyline points="1 20 1 14 7 14"/>'
        '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"/>'
        '<path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"/>'
    ),
    "sliders": (
        '<line x1="4" y1="21" x2="4" y2="14"/>'
        '<line x1="4" y1="10" x2="4" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="12"/>'
        '<line x1="12" y1="8" x2="12" y2="3"/>'
        '<line x1="20" y1="21" x2="20" y2="16"/>'
        '<line x1="20" y1="12" x2="20" y2="3"/>'
        '<line x1="1" y1="14" x2="7" y2="14"/>'
        '<line x1="9" y1="8" x2="15" y2="8"/>'
        '<line x1="17" y1="16" x2="23" y2="16"/>'
    ),
    "sun": (
        '<circle cx="12" cy="12" r="4"/>'
        '<line x1="12" y1="2" x2="12" y2="4"/>'
        '<line x1="12" y1="20" x2="12" y2="22"/>'
        '<line x1="4.93" y1="4.93" x2="6.34" y2="6.34"/>'
        '<line x1="17.66" y1="17.66" x2="19.07" y2="19.07"/>'
        '<line x1="2" y1="12" x2="4" y2="12"/>'
        '<line x1="20" y1="12" x2="22" y2="12"/>'
        '<line x1="4.93" y1="19.07" x2="6.34" y2="17.66"/>'
        '<line x1="17.66" y1="6.34" x2="19.07" y2="4.93"/>'
    ),
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "terminal": (
        '<polyline points="4 17 10 11 4 5"/>'
        '<line x1="12" y1="19" x2="20" y2="19"/>'
    ),
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "search": (
        '<circle cx="11" cy="11" r="8"/>'
        '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
    ),
    "upload": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="17 8 12 3 7 8"/>'
        '<line x1="12" y1="3" x2="12" y2="15"/>'
    ),
}


def render_svg_pixmap(name: str, color: str, size: int = 18) -> QPixmap:
    """Renderiza um ícone SVG inline com nitidez HiDPI."""
    body = _SVG_PATHS.get(name, _SVG_PATHS["folder"])
    svg_markup = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    )
    scale = 2
    px = size * scale
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(QByteArray(svg_markup.encode("utf-8")))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    return pixmap


def svg_icon(name: str, color: str, size: int = 18) -> QIcon:
    """Cria um QIcon a partir de um SVG inline."""
    return QIcon(render_svg_pixmap(name, color, size))
