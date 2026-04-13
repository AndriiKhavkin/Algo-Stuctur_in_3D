from typing import List, Tuple

Point = Tuple[float, float]


# =========================
# Вхідні дані: варіант 18
# =========================
POINTS: List[Point] = [
    (437, 153),  # P1
    (244, 167),  # P2
    (438, 380),  # P3
    (65, 429),   # P4
    (349, 109)   # P5
]


# =========================
# Базові операції з точками
# =========================
def add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def mul(a: Point, k: float) -> Point:
    return (a[0] * k, a[1] * k)


# =========================
# Обчислення дотичних
# =========================
def compute_tangents(points: List[Point], scale: float = 1.0) -> List[Point]:
    """
    Обчислення дотичних векторів у вузлах замкненої кривої.

    Формула:
        T_i = scale * (P_{i+1} - P_{i-1}) / 2

    scale керує довжиною дотичних векторів.
    """
    n = len(points)
    tangents = []

    for i in range(n):
        p_prev = points[(i - 1) % n]
        p_next = points[(i + 1) % n]
        tangent = mul(sub(p_next, p_prev), 0.5 * scale)
        tangents.append(tangent)

    return tangents


# =========================
# Кубічна крива Ерміта
# =========================
def hermite_point(p0: Point, p1: Point, t0: Point, t1: Point, u: float) -> Point:
    """
    Обчислює точку кубічної кривої Ерміта для параметра u in [0, 1].
    """
    h00 = 2 * u**3 - 3 * u**2 + 1
    h10 = u**3 - 2 * u**2 + u
    h01 = -2 * u**3 + 3 * u**2
    h11 = u**3 - u**2

    x = h00 * p0[0] + h10 * t0[0] + h01 * p1[0] + h11 * t1[0]
    y = h00 * p0[1] + h10 * t0[1] + h01 * p1[1] + h11 * t1[1]
    return (x, y)


def hermite_to_bezier(
    p0: Point,
    p1: Point,
    t0: Point,
    t1: Point
) -> Tuple[Point, Point, Point, Point]:
    """
    Перетворення кубічної кривої Ерміта у кубічну Безьє.

    Для SVG це зручно, бо можна використати команду:
        C x1,y1 x2,y2 x3,y3
    """
    b0 = p0
    b1 = add(p0, mul(t0, 1.0 / 3.0))
    b2 = sub(p1, mul(t1, 1.0 / 3.0))
    b3 = p1
    return b0, b1, b2, b3


# =========================
# Семплювання кривої
# =========================
def sample_curve(
    points: List[Point],
    tangents: List[Point],
    samples_per_segment: int = 100
) -> List[Point]:
    """
    Повертає набір точок уздовж усієї замкненої кривої.
    Це потрібно для оцінки реальних меж кривої перед масштабуванням у SVG.
    """
    sampled = []
    n = len(points)

    for i in range(n):
        p0 = points[i]
        p1 = points[(i + 1) % n]
        t0 = tangents[i]
        t1 = tangents[(i + 1) % n]

        for s in range(samples_per_segment + 1):
            u = s / samples_per_segment
            sampled.append(hermite_point(p0, p1, t0, t1, u))

    return sampled


# =========================
# Масштабування під полотно
# =========================
def compute_svg_transform(
    points_to_fit: List[Point],
    canvas_size: int = 1600,
    padding: int = 120
) -> Tuple[float, float, float]:
    """
    Обчислює scale та translate так, щоб фігура максимально заповнила полотно
    з однаковими відступами.
    """
    xs = [p[0] for p in points_to_fit]
    ys = [p[1] for p in points_to_fit]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = max_x - min_x
    height = max_y - min_y

    if width == 0:
        width = 1
    if height == 0:
        height = 1

    available_w = canvas_size - 2 * padding
    available_h = canvas_size - 2 * padding

    scale = min(available_w / width, available_h / height)

    scaled_w = width * scale
    scaled_h = height * scale

    tx = (canvas_size - scaled_w) / 2 - min_x * scale
    ty = (canvas_size - scaled_h) / 2 - min_y * scale

    return scale, tx, ty


# =========================
# Генерація SVG
# =========================
def generate_svg(
    points: List[Point],
    tangent_scale: float,
    filename: str = "lab1_variant18.svg",
    canvas_size: int = 1600,
    padding: int = 120,
    show_grid: bool = True,
    show_title: bool = True
) -> None:
    """
    Генерує SVG-файл із замкненою C1-неперервною кривою.
    """
    tangents = compute_tangents(points, tangent_scale)
    n = len(points)

    sampled_curve = sample_curve(points, tangents, samples_per_segment=120)
    fit_points = sampled_curve + points

    svg_scale, tx, ty = compute_svg_transform(
        fit_points,
        canvas_size=canvas_size,
        padding=padding
    )

    # Формування SVG path
    path_parts = []
    x0, y0 = points[0]
    path_parts.append(f"M {x0},{y0}")

    for i in range(n):
        p0 = points[i]
        p1 = points[(i + 1) % n]
        t0 = tangents[i]
        t1 = tangents[(i + 1) % n]

        _, b1, b2, b3 = hermite_to_bezier(p0, p1, t0, t1)
        path_parts.append(
            f"C {b1[0]:.2f},{b1[1]:.2f} {b2[0]:.2f},{b2[1]:.2f} {b3[0]:.2f},{b3[1]:.2f}"
        )

    path_parts.append("Z")
    path_d = " ".join(path_parts)

    # Сітка
    grid_lines = []
    if show_grid:
        step = 100
        for x in range(0, canvas_size + 1, step):
            grid_lines.append(
                f'<line x1="{x}" y1="0" x2="{x}" y2="{canvas_size}" stroke="#e8e8e8" stroke-width="1"/>'
            )
        for y in range(0, canvas_size + 1, step):
            grid_lines.append(
                f'<line x1="0" y1="{y}" x2="{canvas_size}" y2="{y}" stroke="#e8e8e8" stroke-width="1"/>'
            )

    # Точки і підписи
    # Радіус, шрифт і товщини підлаштовуємо під масштаб, щоб після transform все виглядало нормально
    point_radius = 10 / svg_scale
    point_stroke = 3 / svg_scale
    font_size = 28 / svg_scale
    label_dx = 18 / svg_scale
    label_dy = -18 / svg_scale

    point_circles = []
    point_labels = []

    for i, (x, y) in enumerate(points, start=1):
        point_circles.append(
            f'<circle cx="{x}" cy="{y}" r="{point_radius:.4f}" fill="#d62828" stroke="white" stroke-width="{point_stroke:.4f}" />'
        )
        point_labels.append(
            f'<text x="{x + label_dx:.4f}" y="{y + label_dy:.4f}" '
            f'font-size="{font_size:.4f}" font-family="Arial" fill="#222">P{i}</text>'
        )

    title_block = ""
    if show_title:
        title_block = f'''
    <text x="60" y="80"
          font-size="42"
          font-family="Arial"
          fill="#222">
        Замкнена C1-неперервна кубічна крива (варіант 18, scale = {tangent_scale})
    </text>
'''

    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{canvas_size}" height="{canvas_size}"
     viewBox="0 0 {canvas_size} {canvas_size}"
     xmlns="http://www.w3.org/2000/svg">

    <rect width="100%" height="100%" fill="#fcfcfc"/>
    {"".join(grid_lines)}
    <rect x="20" y="20" width="{canvas_size - 40}" height="{canvas_size - 40}"
          fill="none" stroke="#bdbdbd" stroke-width="2"/>{title_block}

    <g transform="translate({tx:.4f},{ty:.4f}) scale({svg_scale:.4f})">
        <path
            d="{path_d}"
            fill="none"
            stroke="#111"
            stroke-width="{4 / svg_scale:.4f}" />
        {"".join(point_circles)}
        {"".join(point_labels)}
    </g>

</svg>
'''

    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"SVG-файл збережено: {filename}")


# =========================
# Основна функція
# =========================
def main():
    # Один основний файл
    generate_svg(
        points=POINTS,
        tangent_scale=1.0,
        filename="lab1_variant18.svg",
        canvas_size=1600,
        padding=120,
        show_grid=True,
        show_title=True
    )

    # Файли для експерименту
    generate_svg(
        points=POINTS,
        tangent_scale=0.25,
        filename="lab1_variant18_small.svg",
        canvas_size=1600,
        padding=120,
        show_grid=True,
        show_title=True
    )

    generate_svg(
        points=POINTS,
        tangent_scale=2.0,
        filename="lab1_variant18_large.svg",
        canvas_size=1600,
        padding=120,
        show_grid=True,
        show_title=True
    )


if __name__ == "__main__":
    main()