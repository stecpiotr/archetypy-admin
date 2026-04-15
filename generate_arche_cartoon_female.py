from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "assets" / "person_icons"
OUT_DIR = ROOT / "assets" / "arche_cartoon"

CANVAS_SIZE = (1024, 1024)

ARCHETYPE_SLUG_TO_NAME: dict[str, str] = {
    "blazen": "Błazen",
    "bohater": "Bohater",
    "buntownik": "Buntownik",
    "czarodziej": "Czarodziej",
    "kochanek": "Kochanek",
    "medrzec": "Mędrzec",
    "niewinny": "Niewinny",
    "odkrywca": "Odkrywca",
    "opiekun": "Opiekun",
    "towarzysz": "Towarzysz",
    "tworca": "Twórca",
    "wladca": "Władca",
}


def _bbox_from_alpha(alpha: Image.Image) -> tuple[int, int, int, int]:
    bbox = alpha.getbbox()
    if not bbox:
        return (0, 0, alpha.width, alpha.height)
    return bbox


def _crop_upper_portrait(img: Image.Image) -> Image.Image:
    alpha = img.getchannel("A")
    x0, y0, x1, y1 = _bbox_from_alpha(alpha)
    w = x1 - x0
    h = y1 - y0

    # Kadr bust/half-bust: więcej twarzy i ramion, mniej nóg.
    top = max(0, int(y0 - 0.03 * h))
    bottom = min(img.height, int(y0 + 0.68 * h))
    left = max(0, int(x0 - 0.16 * w))
    right = min(img.width, int(x1 + 0.16 * w))

    cropped = img.crop((left, top, right, bottom))

    # Dodatkowe docięcie pionowe, jeśli postać jest nadal zbyt "wysoka".
    c_alpha = cropped.getchannel("A")
    cx0, cy0, cx1, cy1 = _bbox_from_alpha(c_alpha)
    cw = cx1 - cx0
    ch = cy1 - cy0
    if ch > 1.25 * cw:
        ny1 = min(cropped.height, int(cy0 + 1.18 * cw))
        cropped = cropped.crop((0, 0, cropped.width, ny1))

    return cropped


def _stylize_to_pencil(img: Image.Image, seed: int) -> Image.Image:
    rgb = img.convert("RGB")
    alpha = img.getchannel("A")

    gray = ImageOps.grayscale(rgb)
    arr = np.asarray(gray, dtype=np.float32)

    # Efekt "pencil sketch": dodge blend.
    inv = 255.0 - arr
    blur = np.asarray(
        Image.fromarray(inv.astype(np.uint8), mode="L").filter(ImageFilter.GaussianBlur(radius=10.0)),
        dtype=np.float32,
    )
    dodge = np.clip(arr * 255.0 / np.maximum(255.0 - blur, 1.0), 0.0, 255.0)

    # Podkreślenie linii i faktury.
    edges = Image.fromarray(dodge.astype(np.uint8), mode="L").filter(ImageFilter.FIND_EDGES)
    edges_arr = np.asarray(edges, dtype=np.float32)
    ink = np.clip(255.0 - edges_arr * 1.08, 0.0, 255.0)
    merged = np.clip(dodge * 0.80 + ink * 0.20, 0.0, 255.0)

    # Delikatny "papierowy" szum.
    rng = np.random.default_rng(seed)
    noise = rng.normal(loc=0.0, scale=4.3, size=merged.shape).astype(np.float32)
    merged = np.clip(merged + noise, 0.0, 255.0).astype(np.uint8)

    pencil = Image.fromarray(merged, mode="L")
    pencil = ImageEnhance.Contrast(pencil).enhance(1.32)
    pencil = ImageEnhance.Sharpness(pencil).enhance(1.42)

    # Składanie RGBA + miękki rant.
    soft_alpha = alpha.filter(ImageFilter.GaussianBlur(radius=1.05))
    return Image.merge("RGBA", (pencil, pencil, pencil, soft_alpha))


def _place_on_canvas(stylized: Image.Image, seed: int) -> Image.Image:
    canvas = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    rng = np.random.default_rng(seed)

    # Bardzo podobny fill do męskich portretów.
    max_w = int(CANVAS_SIZE[0] * 0.96)
    max_h = int(CANVAS_SIZE[1] * 0.95)
    scale = min(max_w / stylized.width, max_h / stylized.height)
    resized = stylized.resize(
        (max(1, int(stylized.width * scale)), max(1, int(stylized.height * scale))),
        Image.Resampling.LANCZOS,
    )

    # Minimalny jitter, aby uniknąć identycznej geometrii kadru.
    jitter_x = int(rng.integers(-18, 19))
    jitter_y = int(rng.integers(-10, 21))
    x = (CANVAS_SIZE[0] - resized.width) // 2 + jitter_x
    y = 26 + jitter_y

    canvas.alpha_composite(resized, (x, y))

    # Delikatna mgiełka wokół obiektu jak w oryginalnych assetach.
    alpha = canvas.getchannel("A")
    halo = alpha.filter(ImageFilter.GaussianBlur(radius=12))
    halo = ImageEnhance.Brightness(halo).enhance(0.42)
    halo_rgba = Image.merge("RGBA", (halo, halo, halo, halo))
    out = Image.alpha_composite(halo_rgba, canvas)
    return out


def generate_one(slug: str, display_name: str) -> Path:
    src = SRC_DIR / f"{slug}_K.png"
    if not src.exists():
        raise FileNotFoundError(f"Brak pliku źródłowego: {src}")

    seed = sum(ord(c) for c in slug) % (2**32)
    img = Image.open(src).convert("RGBA")
    cropped = _crop_upper_portrait(img)
    stylized = _stylize_to_pencil(cropped, seed=seed)
    final = _place_on_canvas(stylized, seed=seed)

    out_path = OUT_DIR / f"{display_name}_K.png"
    final.save(out_path, "PNG", optimize=True)
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for slug, display_name in ARCHETYPE_SLUG_TO_NAME.items():
        out = generate_one(slug, display_name)
        generated.append(out)
        print(f"[OK] {out}")

    print(f"\nWygenerowano {len(generated)} grafik żeńskich archetypów.")


if __name__ == "__main__":
    main()
