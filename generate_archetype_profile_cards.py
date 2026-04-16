from __future__ import annotations

import argparse
from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
FACES_DIR_MALE = ROOT / "assets" / "arche_cartoon"
FACES_DIR_FEMALE = ROOT / "assets" / "arche_cartoon"
FACES_DIR_PERSON_ICONS = ROOT / "assets" / "person_icons"
FONTS_DIR = ROOT / "assets" / "fonts"
OUT_DIR_MALE = ROOT / "assets" / "archetype_profile_cards_male"
OUT_DIR_FEMALE = ROOT / "assets" / "archetype_profile_cards_female"

CANVAS_W = 1024
CANVAS_H = 335
BASELINE_Y = 240
MAX_PEAK = 205  # 100% -> 205 px (stała skala dla wszystkich kart)
CHART_X0 = 356
CHART_X1 = 960
BAR_SIGMA_PX = 39.0

METRICS = ("Empatia", "Sprawczość", "Niezależność", "Racjonalność", "Kreatywność")

ARCHETYPES: dict[str, dict[str, object]] = {
    "Opiekun": {
        "values": (95, 60, 20, 60, 25),
        "color": "#42A5F5",
    },
    "Kochanek": {
        "values": (85, 45, 25, 30, 60),
        "color": "#90CAF9",
    },
    "Błazen": {
        "values": (50, 45, 45, 20, 90),
        "color": "#EF5350",
    },
    "Buntownik": {
        "values": (20, 60, 95, 25, 85),
        "color": "#C62828",
    },
    "Odkrywca": {
        "values": (30, 55, 90, 45, 80),
        "color": "#8E0000",
    },
    "Twórca": {
        "values": (35, 75, 80, 40, 95),
        "color": "#5E35B1",
    },
    "Bohater": {
        "values": (30, 95, 75, 40, 40),
        "color": "#7E57C2",
    },
    "Czarodziej": {
        "values": (45, 65, 70, 80, 90),
        "color": "#B39DDB",
    },
    "Mędrzec": {
        "values": (20, 70, 80, 95, 30),
        "color": "#1B5E20",
    },
    "Władca": {
        "values": (25, 90, 70, 75, 25),
        "color": "#43A047",
    },
    "Niewinny": {
        "values": (75, 30, 30, 50, 50),
        "color": "#81C784",
    },
    "Towarzysz": {
        "values": (85, 60, 25, 45, 20),
        "color": "#1565C0",
    },
}

ARCHETYPE_FILENAME_SLUG: dict[str, str] = {
    "Opiekun": "opiekun",
    "Kochanek": "kochanek",
    "Błazen": "blazen",
    "Buntownik": "buntownik",
    "Odkrywca": "odkrywca",
    "Twórca": "tworca",
    "Bohater": "bohater",
    "Czarodziej": "czarodziej",
    "Mędrzec": "medrzec",
    "Władca": "wladca",
    "Niewinny": "niewinny",
    "Towarzysz": "towarzysz",
}

FEMININE_TITLES: dict[str, str] = {
    "Władca": "Władczyni",
    "Bohater": "Bohaterka",
    "Mędrzec": "Mędrczyni",
    "Opiekun": "Opiekunka",
    "Kochanek": "Kochanka",
    "Błazen": "Komiczka",
    "Twórca": "Twórczyni",
    "Odkrywca": "Odkrywczyni",
    "Czarodziej": "Czarodziejka",
    "Towarzysz": "Towarzyszka",
    "Niewinny": "Niewinna",
    "Buntownik": "Buntowniczka",
}


def _fit_into_canvas_rgba(img: Image.Image, canvas_size: int = 768, padding: int = 46) -> Image.Image:
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    max_w = canvas_size - 2 * padding
    max_h = canvas_size - 2 * padding
    ratio = min(max_w / img.width, max_h / img.height)
    nw = max(1, int(round(img.width * ratio)))
    nh = max(1, int(round(img.height * ratio)))
    scaled = img.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = (canvas_size - nw) // 2
    oy = (canvas_size - nh) // 2
    canvas.alpha_composite(scaled, (ox, oy))
    return canvas


def _pencil_sketch_rgba(source: Image.Image) -> Image.Image:
    src = source.convert("RGBA")
    alpha = np.asarray(src.getchannel("A"), dtype=np.uint8)
    rgb = src.convert("RGB")
    gray = np.asarray(rgb.convert("L"), dtype=np.float32)

    inv = 255.0 - gray
    inv_blur = np.asarray(Image.fromarray(inv.astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(radius=12)), dtype=np.float32)
    dodge = gray * 255.0 / np.maximum(1.0, 255.0 - inv_blur)
    dodge = np.clip(dodge, 0, 255)

    edges_raw = np.asarray(Image.fromarray(gray.astype(np.uint8), "L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    edges = np.clip(edges_raw * 1.45, 0, 255)
    sketch = np.clip(dodge * 0.64 + gray * 0.36, 0, 255)
    sketch = np.clip(sketch - edges * 0.22 + 14.0, 0, 255)

    sketch_img = Image.fromarray(sketch.astype(np.uint8), "L")
    sketch_img = ImageOps.autocontrast(sketch_img, cutoff=1)
    sketch_img = sketch_img.filter(ImageFilter.UnsharpMask(radius=1.4, percent=165, threshold=2))
    sketch_arr = np.asarray(sketch_img, dtype=np.uint8)

    # Delikatna "mgiełka" wokół postaci dla klimatu zbliżonego do arche_cartoon.
    aura_alpha = Image.fromarray(alpha, "L").filter(ImageFilter.MaxFilter(size=17)).filter(ImageFilter.GaussianBlur(radius=8))
    aura = Image.new("RGBA", src.size, (180, 180, 180, 0))
    aura.putalpha(aura_alpha.point(lambda v: int(v * 0.12)))

    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    out.alpha_composite(aura)
    sketch_rgba = Image.merge(
        "RGBA",
        (
            Image.fromarray(sketch_arr, "L"),
            Image.fromarray(sketch_arr, "L"),
            Image.fromarray(sketch_arr, "L"),
            Image.fromarray(alpha, "L"),
        ),
    )
    out.alpha_composite(sketch_rgba)
    return out


def _build_female_face_from_icon(src_icon_path: Path, dst_face_path: Path) -> None:
    src = Image.open(src_icon_path).convert("RGBA")
    alpha = src.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise ValueError(f"Pusta alfa dla pliku: {src_icon_path}")

    src = src.crop(bbox)
    # Zostawiamy górne ~58%, żeby uzyskać wyraźne popiersie zamiast pełnej sylwetki.
    upper_h = max(1, int(round(src.height * 0.58)))
    src = src.crop((0, 0, src.width, upper_h))

    # Dociśnij poziomy kadr do "głowa + ramiona", żeby uniknąć pełnych rąk.
    trim_left = int(round(src.width * 0.18))
    trim_right = int(round(src.width * 0.18))
    src = src.crop((trim_left, 0, max(trim_left + 2, src.width - trim_right), src.height))

    normalized = _fit_into_canvas_rgba(src, canvas_size=768, padding=34)
    sketch = _pencil_sketch_rgba(normalized)
    dst_face_path.parent.mkdir(parents=True, exist_ok=True)
    sketch.save(dst_face_path, "PNG", optimize=True)


def ensure_female_faces(force: bool = False) -> None:
    FACES_DIR_FEMALE.mkdir(parents=True, exist_ok=True)
    for name, slug in ARCHETYPE_FILENAME_SLUG.items():
        src = FACES_DIR_PERSON_ICONS / f"{slug}_K.png"
        if not src.exists():
            raise FileNotFoundError(f"Brak źródłowej ikony żeńskiej: {src}")
        dst = FACES_DIR_FEMALE / f"{name}.png"
        if force or not dst.exists():
            _build_female_face_from_icon(src, dst)


def face_path_for_archetype(name: str, gender_code: str) -> Path:
    if gender_code.upper() == "K":
        female_direct = FACES_DIR_FEMALE / f"{name}_K.png"
        if female_direct.exists():
            return female_direct
        female_fallback = FACES_DIR_FEMALE / f"{name}.png"
        if female_fallback.exists():
            return female_fallback

    male_direct = FACES_DIR_MALE / f"{name}.png"
    if male_direct.exists():
        return male_direct

    raise FileNotFoundError(f"Brak grafiki twarzy dla archetypu: {name} ({gender_code})")


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def hex_to_rgb(color_hex: str) -> tuple[int, int, int]:
    color_hex = color_hex.strip().lstrip("#")
    return tuple(int(color_hex[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def mix_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = clamp(t, 0.0, 1.0)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore[return-value]


def darken(rgb: tuple[int, int, int], amount: float = 0.22) -> tuple[int, int, int]:
    return mix_rgb(rgb, (0, 0, 0), amount)


def lighten(rgb: tuple[int, int, int], amount: float = 0.25) -> tuple[int, int, int]:
    return mix_rgb(rgb, (255, 255, 255), amount)


def font(path_candidates: list[Path], size: int) -> ImageFont.ImageFont:
    for candidate in path_candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def text_width_with_tracking(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_obj: ImageFont.ImageFont,
    tracking_px: float = 0.0,
) -> float:
    if not text:
        return 0.0
    total = 0.0
    for idx, ch in enumerate(text):
        bb = draw.textbbox((0, 0), ch, font=font_obj)
        total += float(bb[2] - bb[0])
        if idx < len(text) - 1:
            total += tracking_px
    return total


def draw_text_with_tracking(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font_obj: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    tracking_px: float = 0.0,
) -> None:
    x, y = xy
    for idx, ch in enumerate(text):
        draw.text((x, y), ch, font=font_obj, fill=fill)
        bb = draw.textbbox((0, 0), ch, font=font_obj)
        x += float(bb[2] - bb[0])
        if idx < len(text) - 1:
            x += tracking_px


def detect_checker_colors(rgb_arr: np.ndarray) -> list[tuple[int, int, int]]:
    h, w, _ = rgb_arr.shape
    s = min(120, h // 5, w // 5)
    corners = np.concatenate(
        (
            rgb_arr[:s, :s].reshape(-1, 3),
            rgb_arr[:s, -s:].reshape(-1, 3),
            rgb_arr[-s:, :s].reshape(-1, 3),
            rgb_arr[-s:, -s:].reshape(-1, 3),
        ),
        axis=0,
    )
    quant = (corners // 4) * 4
    cnt = Counter(map(tuple, quant.tolist()))
    top = [c for c, _ in cnt.most_common(8)]
    if not top:
        return [(255, 255, 255)]

    selected: list[tuple[int, int, int]] = []
    for color in top:
        if not selected:
            selected.append(color)
            continue
        if min(np.linalg.norm(np.array(color) - np.array(sv)) for sv in selected) >= 26:
            selected.append(color)
        if len(selected) == 2:
            break
    return selected or [top[0]]


def flood_fill_background(candidate_bg: np.ndarray) -> np.ndarray:
    h, w = candidate_bg.shape
    bg = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    def push(y: int, x: int) -> None:
        if candidate_bg[y, x] and not bg[y, x]:
            bg[y, x] = True
            q.append((y, x))

    for x in range(w):
        push(0, x)
        push(h - 1, x)
    for y in range(h):
        push(y, 0)
        push(y, w - 1)

    while q:
        y, x = q.popleft()
        if y > 0:
            push(y - 1, x)
        if y + 1 < h:
            push(y + 1, x)
        if x > 0:
            push(y, x - 1)
        if x + 1 < w:
            push(y, x + 1)

    return bg


def cleanup_nontransparent_face(img: Image.Image) -> Image.Image:
    rgb = np.asarray(img.convert("RGB"), dtype=np.int16)
    colors = detect_checker_colors(rgb.astype(np.uint8))

    dists = []
    for c in colors:
        c_arr = np.array(c, dtype=np.int16)
        d = np.sqrt(np.sum((rgb - c_arr) ** 2, axis=2))
        dists.append(d)
    min_dist = np.min(np.stack(dists, axis=2), axis=2)

    channel_span = rgb.max(axis=2) - rgb.min(axis=2)
    neutral = channel_span <= 14
    candidate = (min_dist <= 26.0) & neutral
    bg = flood_fill_background(candidate)

    alpha = np.where(bg, 0, 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(radius=1.25))
    r, g, b = img.convert("RGB").split()
    return Image.merge("RGBA", (r, g, b, alpha_img))


def prepare_face(face_path: Path) -> Image.Image:
    img = Image.open(face_path).convert("RGBA")
    alpha = img.getchannel("A")
    extrema = alpha.getextrema()
    if extrema == (255, 255):
        img = cleanup_nontransparent_face(img)
        alpha = img.getchannel("A")

    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)
    return img


def hump_mask(
    width: int,
    height: int,
    points: list[tuple[float, float]],
    baseline: float,
) -> Image.Image:
    poly = list(points)
    poly.extend([(float(points[-1][0]), float(baseline)), (float(points[0][0]), float(baseline))])
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(poly, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=0.8))


def hump_curve_points(
    width: int,
    height: int,
    center_x: float,
    peak_height: float,
    sigma: float,
    baseline: float,
) -> list[tuple[float, float]]:
    x = np.linspace(center_x - 3.1 * sigma, center_x + 3.1 * sigma, 520)
    y = baseline - peak_height * np.exp(-0.5 * ((x - center_x) / sigma) ** 2)
    x = np.clip(x, 0, width - 1)
    y = np.clip(y, 0, height - 1)
    return [(float(px), float(py)) for px, py in zip(x, y)]


def gradient_fill(
    size: tuple[int, int],
    base_rgb: tuple[int, int, int],
    baseline: int,
    max_peak: int,
    alpha_top: int = 210,
    alpha_bottom: int = 140,
) -> Image.Image:
    w, h = size
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    top = darken(base_rgb, 0.12)
    mid = base_rgb
    bottom = mix_rgb(base_rgb, (255, 255, 255), 0.12)

    for y in range(h):
        t = clamp((baseline - y) / float(max_peak), 0.0, 1.0)
        if t > 0.6:
            local_t = (t - 0.6) / 0.4
            rgb = mix_rgb(mid, top, local_t)
            a = int(round(alpha_top * (0.92 + 0.08 * local_t)))
        else:
            local_t = t / 0.6
            rgb = mix_rgb(bottom, mid, local_t)
            a = int(round(alpha_bottom + (alpha_top - alpha_bottom) * local_t))
        arr[y, :, 0] = rgb[0]
        arr[y, :, 1] = rgb[1]
        arr[y, :, 2] = rgb[2]
        arr[y, :, 3] = a
    return Image.fromarray(arr)


def draw_archetype_panel(
    name: str,
    values: tuple[int, ...],
    color_hex: str,
    face_path: Path,
    display_name: str | None = None,
    theme_variant: str = "light",
) -> Image.Image:
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    color_rgb = hex_to_rgb(color_hex)
    is_dark = str(theme_variant or "light").lower() == "dark"

    fill_rgb = color_rgb
    stroke_rgb = lighten(color_rgb, 0.14) if is_dark else darken(color_rgb, 0.22)
    title_fill = (238, 242, 248, 255) if is_dark else (20, 20, 20, 255)
    value_fill = (245, 248, 252, 255) if is_dark else (28, 28, 28, 255)
    label_fill = (222, 230, 240, 255) if is_dark else (40, 40, 40, 255)
    baseline_alpha = 132 if is_dark else 92
    contour_alpha = 162 if is_dark else 125
    tail_alpha = 128 if is_dark else 100

    # Portret po lewej
    face = prepare_face(face_path)
    max_face_w = 290
    max_face_h = 250
    ratio = min(max_face_w / face.width, max_face_h / face.height)
    face = face.resize((int(face.width * ratio), int(face.height * ratio)), Image.Resampling.LANCZOS)
    fx = 160 - face.width // 2
    fy = 14 + max(0, (max_face_h - face.height) // 3)
    canvas.alpha_composite(face, (fx, fy))

    # Nazwa archetypu
    title_font = font(
        [
            FONTS_DIR / "LibreBaskerville-Bold.ttf",
            ROOT / "DejaVuSans-Bold.ttf",
        ],
        size=38,
    )
    shown_name = str(display_name or name)
    title_bbox = draw.textbbox((0, 0), shown_name, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    face_bottom = fy + face.height
    # Nazwa zawsze pod portretem, z wyraźnym odstępem i bez obcinania dołu.
    title_y = min(CANVAS_H - title_h - 6, face_bottom + -1)
    draw.text((160 - title_w // 2, int(title_y)), shown_name, fill=title_fill, font=title_font)

    # Delikatna linia bazowa wykresu
    draw.line((CHART_X0 - 8, BASELINE_Y, CHART_X1 + 8, BASELINE_Y), fill=(*stroke_rgb, baseline_alpha), width=2)

    chart_width = CHART_X1 - CHART_X0
    step = chart_width / len(values)
    sigma = BAR_SIGMA_PX
    gradient = gradient_fill(
        (CANVAS_W, CANVAS_H),
        fill_rgb,
        BASELINE_Y,
        MAX_PEAK,
        alpha_top=212,
        alpha_bottom=168,
    )

    label_font = font(
        [
            FONTS_DIR / "BarlowCondensed-Medium.ttf",
            FONTS_DIR / "BarlowCondensed-Regular.ttf",
            FONTS_DIR / "BarlowCondensed-Bold.ttf",
            FONTS_DIR / "RobotoCondensed-Bold.ttf",
            FONTS_DIR / "PTSans-Bold.ttf",
            FONTS_DIR / "solitas-normal-medium.otf",
            ROOT / "DejaVuSans.ttf",
        ],
        size=22,
    )
    value_font = font(
        [
            FONTS_DIR / "BarlowCondensed-Medium.ttf",
            FONTS_DIR / "BarlowCondensed-Regular.ttf",
            FONTS_DIR / "BarlowCondensed-Bold.ttf",
            FONTS_DIR / "RobotoCondensed-Bold.ttf",
            FONTS_DIR / "PTSans-Bold.ttf",
            FONTS_DIR / "solitas-normal-medium.otf",
            ROOT / "DejaVuSans.ttf",
        ],
        size=28,
    )
    tracking = 0.0

    for i, value in enumerate(values):
        cx = CHART_X0 + step * (i + 0.5)
        peak = (value / 100.0) * MAX_PEAK

        curve = hump_curve_points(
            CANVAS_W,
            CANVAS_H,
            center_x=cx,
            peak_height=peak,
            sigma=sigma,
            baseline=BASELINE_Y,
        )
        mask = hump_mask(CANVAS_W, CANVAS_H, curve, baseline=BASELINE_Y)
        hump = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        hump.paste(gradient, (0, 0), mask=mask)
        canvas.alpha_composite(hump)

        # Subtelny kontur górnej krawędzi fali
        draw.line(curve, fill=(*stroke_rgb, contour_alpha), width=2)
        draw.line([(curve[0][0] - 7, BASELINE_Y), (curve[0][0], BASELINE_Y)], fill=(*stroke_rgb, tail_alpha), width=2)
        draw.line([(curve[-1][0], BASELINE_Y), (curve[-1][0] + 7, BASELINE_Y)], fill=(*stroke_rgb, tail_alpha), width=2)

        value_txt = f"{int(value)}%"
        vb = draw.textbbox((0, 0), value_txt, font=value_font)
        vw = text_width_with_tracking(draw, value_txt, value_font, tracking_px=tracking)
        vh = vb[3] - vb[1]
        vy = int(BASELINE_Y - peak - vh - 18)
        draw_text_with_tracking(
            draw,
            (float(cx - vw / 2), float(vy)),
            value_txt,
            value_font,
            value_fill,
            tracking_px=tracking,
        )

        metric = METRICS[i]
        mw = text_width_with_tracking(draw, metric, label_font, tracking_px=tracking)
        draw_text_with_tracking(
            draw,
            (float(cx - mw / 2), float(BASELINE_Y + 9)),
            metric,
            label_font,
            label_fill,
            tracking_px=tracking,
        )

    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate archetype profile cards.")
    parser.add_argument("--only", type=str, default="", help="Generate only one archetype by exact name.")
    parser.add_argument(
        "--gender",
        type=str.upper,
        default="BOTH",
        choices=["M", "K", "BOTH"],
        help="M = męskie, K = żeńskie, BOTH = generuj oba zestawy jednym uruchomieniem (domyślnie BOTH)",
    )
    parser.add_argument(
        "--theme",
        type=str.upper,
        default="BOTH",
        choices=["LIGHT", "DARK", "BOTH"],
        help="LIGHT = standard, DARK = wariant pod ciemny motyw, BOTH = oba warianty (domyślnie BOTH)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="",
        help="Opcjonalna ścieżka wyjściowa; domyślnie zależna od --gender.",
    )
    parser.add_argument(
        "--rebuild-female-faces",
        action="store_true",
        help="Wymuś przebudowę pomocniczych szkiców żeńskich.",
    )
    args = parser.parse_args()

    gender_codes = ["M", "K"] if args.gender == "BOTH" else [args.gender]
    theme_variants = ["light", "dark"] if args.theme == "BOTH" else [args.theme.lower()]

    if args.rebuild_female_faces and "K" in gender_codes:
        ensure_female_faces(force=True)

    items = list(ARCHETYPES.items())
    if args.only:
        items = [(k, v) for k, v in items if k == args.only]
        if not items:
            raise ValueError(f"Nie znaleziono archetypu: {args.only}")

    for gender_code in gender_codes:
        if args.out_dir:
            base = Path(args.out_dir)
            out_dir = base if len(gender_codes) == 1 else (base / ("male" if gender_code == "M" else "female"))
        else:
            out_dir = OUT_DIR_FEMALE if gender_code == "K" else OUT_DIR_MALE
        out_dir.mkdir(parents=True, exist_ok=True)

        for arche_name, config in items:
            values = config["values"]  # type: ignore[assignment]
            color = str(config["color"])
            face_path = face_path_for_archetype(arche_name, gender_code=gender_code)
            display_name = FEMININE_TITLES.get(arche_name, arche_name) if gender_code == "K" else arche_name

            for theme_variant in theme_variants:
                panel = draw_archetype_panel(
                    arche_name,
                    values,
                    color,
                    face_path=face_path,
                    display_name=display_name,
                    theme_variant=theme_variant,
                )
                suffix = "_dark" if theme_variant == "dark" else ""
                out = out_dir / f"{arche_name}{suffix}.png"
                panel.save(out, "PNG", optimize=True)
                print(f"[OK] [{gender_code}/{theme_variant.upper()}] {out}")


if __name__ == "__main__":
    main()
