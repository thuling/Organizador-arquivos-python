"""Gera os ícones assets/app.png e assets/app.ico em múltiplas resoluções."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def create_app_icon(size: int = 512) -> Image.Image:
    """Desenha um ícone geométrico moderno de pasta organizada em alta resolução."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(size * 0.06)
    radius = int(size * 0.22)

    # Fundo squircle azul-marinho profundo com borda sutil
    bg_box = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(bg_box, radius=radius, fill=(17, 24, 39, 255))

    # Borda sutil integrada ao squircle
    inner_margin = margin + int(size * 0.015)
    draw.rounded_rectangle(
        [inner_margin, inner_margin, size - inner_margin, size - inner_margin],
        radius=int(radius * 0.94),
        outline=(42, 65, 110, 255),
        width=max(2, int(size * 0.01)),
    )

    # Parte traseira da pasta (azul cobalto escuro)
    fx0, fy0 = int(size * 0.17), int(size * 0.24)
    fx1, fy1 = int(size * 0.83), int(size * 0.78)
    tab_w = int(size * 0.28)
    tab_h = int(size * 0.10)
    r_folder = int(size * 0.065)

    draw.rounded_rectangle(
        [fx0, fy0, fx0 + tab_w, fy0 + tab_h + r_folder],
        radius=int(r_folder * 0.75),
        fill=(37, 99, 235, 255),
    )
    draw.rounded_rectangle(
        [fx0, fy0 + int(tab_h * 0.6), fx1, fy1],
        radius=r_folder,
        fill=(37, 99, 235, 255),
    )

    # Três cartões coloridos saindo da pasta (simbolizando categorias organizadas)
    cards = [
        (0.24, 0.30, 0.56, 0.58, (16, 185, 129, 255)),  # esmeralda
        (0.35, 0.26, 0.67, 0.56, (245, 158, 11, 255)),  # âmbar
        (0.46, 0.32, 0.76, 0.60, (241, 245, 249, 255)),  # branco gelo
    ]
    for cx0, cy0, cx1, cy1, color in cards:
        draw.rounded_rectangle(
            [int(size * cx0), int(size * cy0), int(size * cx1), int(size * cy1)],
            radius=int(size * 0.04),
            fill=color,
        )

    # Frente da pasta (azul vibrante luminoso)
    front_top = int(size * 0.42)
    draw.rounded_rectangle(
        [fx0, front_top, fx1, fy1],
        radius=r_folder,
        fill=(59, 130, 246, 255),
    )

    # Detalhe minimalista de barra de destaque no corpo da pasta
    bar_x0 = int(size * 0.26)
    bar_x1 = int(size * 0.48)
    bar_y0 = int(size * 0.65)
    bar_y1 = int(size * 0.69)
    draw.rounded_rectangle(
        [bar_x0, bar_y0, bar_x1, bar_y1],
        radius=max(2, int(size * 0.02)),
        fill=(191, 219, 254, 210),
    )

    return img


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    assets_dir = root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    icon_512 = create_app_icon(512)
    png_path = assets_dir / "app.png"
    ico_path = assets_dir / "app.ico"

    icon_512.save(png_path, format="PNG")
    icon_512.save(
        ico_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"Ícones gerados: {png_path} e {ico_path}")


if __name__ == "__main__":
    main()
