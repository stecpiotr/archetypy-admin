from __future__ import annotations

import argparse
from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
FACES_DIR = ROOT / "assets" / "arche_cartoon"
FONTS_DIR = ROOT / "assets" / "fonts"
OUT_DIR = ROOT / "assets" / "archetype_profile_cards_male"

CANVAS_W = 1024
CANVAS_H = 335
BASELINE_Y = 232
MAX_PEAK = 190  # 100% -> 190 px (stała skala dla wszystkich kart)
CHART_X0 = 350
CHART_X1 = 990

METRICS = ("Empatia", "Umiejętności", "Niezależność", "Mądrość", "Kreatywność")

ARCHETYPES: dict[str, dict[str, object]] = {
    "Opiekun": {
        "values": (95, 50, 20, 65, 25),
        "color": "#1E88E5",
    },
    "Kochanek": {
        "values": (85, 45, 25, 35, 60),
        "color": "#81D4FA",
    },
    "Błazen": {
        "values": (50, 50, 45, 25, 90),
        "color": "#FB8C00",
    },
    "Buntownik": {
        "values": (20, 55, 95, 30, 85),
        "color": "#C62828",
    },
    "Odkrywca": {
        "values": (30, 60, 90, 45, 80),
        "color": "#2E7D32",
    },
    "Twórca": {
        "values": (35, 80, 80, 40, 95),
        "color": "#AB47BC",
    },
    "Bohater": {
        "values": (30, 95, 75, 45, 40),
        "color": "#EF5350",
    },
    "Czarodziej": {
        "values": (45, 65, 70, 80, 90),
        "color": "#1565C0",
    },
    "Mędrzec": {
        "values": (20, 80, 80, 95, 30),
        "color": "#7B1FA2",
    },
    "Władca": {
        "values": (25, 85, 70, 75, 25),
        "color": "#E53935",
    },
    "Niewinny": {
        "values": (75, 25, 30, 20, 50),
        "color": "#66BB6A",
    },
    "Towarzysz": {
        "values": (85, 60, 25, 45, 20),
        "color": "#42A5F5",
    },
}


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


def draw_archetype_panel(name: str, values: tuple[int, ...], color_hex: str) -> Image.Image:
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    color_rgb = hex_to_rgb(color_hex)
    fill_rgb = darken(color_rgb, 0.18)
    stroke_rgb = darken(color_rgb, 0.31)

    # Portret po lewej
    face = prepare_face(FACES_DIR / f"{name}.png")
    max_face_w = 290
    max_face_h = 250
    ratio = min(max_face_w / face.width, max_face_h / face.height)
    face = face.resize((int(face.width * ratio), int(face.height * ratio)), Image.Resampling.LANCZOS)
    fx = 160 - face.width // 2
    fy = 6 + max(0, (max_face_h - face.height) // 3)
    canvas.alpha_composite(face, (fx, fy))

    # Nazwa archetypu
    title_font = font(
        [
            FONTS_DIR / "LibreBaskerville-SemiBold.ttf",
            ROOT / "DejaVuSans-Bold.ttf",
        ],
        size=47,
    )
    title_bbox = draw.textbbox((0, 0), name, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text((160 - title_w // 2, 250), name, fill=(20, 20, 20, 255), font=title_font)

    # Delikatna linia bazowa wykresu
    draw.line((CHART_X0, BASELINE_Y, CHART_X1, BASELINE_Y), fill=(*stroke_rgb, 92), width=2)

    chart_width = CHART_X1 - CHART_X0
    step = chart_width / len(values)
    sigma = step * 0.24
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
            FONTS_DIR / "solitas-normal-medium.otf",
            ROOT / "DejaVuSans.ttf",
        ],
        size=21,
    )
    value_font = font(
        [
            FONTS_DIR / "solitas-normal-medium.otf",
            ROOT / "DejaVuSans.ttf",
        ],
        size=28,
    )

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
        draw.line(curve, fill=(*stroke_rgb, 125), width=2)

        value_txt = f"{int(value)}%"
        vb = draw.textbbox((0, 0), value_txt, font=value_font)
        vw = vb[2] - vb[0]
        vh = vb[3] - vb[1]
        vy = int(BASELINE_Y - peak - vh - 18)
        draw.text((int(cx - vw / 2), vy), value_txt, fill=(28, 28, 28, 255), font=value_font)

        metric = METRICS[i]
        mb = draw.textbbox((0, 0), metric, font=label_font)
        mw = mb[2] - mb[0]
        draw.text((int(cx - mw / 2), BASELINE_Y + 9), metric, fill=(40, 40, 40, 255), font=label_font)

    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate archetype profile cards.")
    parser.add_argument("--only", type=str, default="", help="Generate only one archetype by exact name.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = list(ARCHETYPES.items())
    if args.only:
        items = [(k, v) for k, v in items if k == args.only]
        if not items:
            raise ValueError(f"Nie znaleziono archetypu: {args.only}")

    for arche_name, config in items:
        values = config["values"]  # type: ignore[assignment]
        color = str(config["color"])
        panel = draw_archetype_panel(arche_name, values, color)
        out = OUT_DIR / f"{arche_name}.png"
        panel.save(out, "PNG", optimize=True)
        print(f"[OK] {out}")


if __name__ == "__main__":
    main()
