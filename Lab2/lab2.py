import math
from typing import List, Tuple, Optional

Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]

# ==========================================
# Вхідні дані: варіант 18
# ==========================================
POINTS_3D: List[Point3D] = [
    (211, 129, 180),  # P1
    (480, 441, 101),  # P2
    (313, 244, 273),  # P3
    (174, 400, 418),  # P4
]

Z_SLICE = 256.0


# ==========================================
# Допоміжні функції
# ==========================================
def dist2(a: Point2D, b: Point2D) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def polyline_length(polyline: List[Point2D], closed: bool = True) -> float:
    if len(polyline) < 2:
        return 0.0

    total = 0.0
    for i in range(len(polyline) - 1):
        total += dist2(polyline[i], polyline[i + 1])

    if closed and len(polyline) > 2:
        total += dist2(polyline[-1], polyline[0])

    return total


def ensure_closed(polyline: List[Point2D], eps: float = 1e-6) -> List[Point2D]:
    if not polyline:
        return polyline
    if dist2(polyline[0], polyline[-1]) > eps:
        return polyline + [polyline[0]]
    return polyline


def polygon_area(poly: List[Point2D]) -> float:
    if len(poly) < 3:
        return 0.0

    pts = poly[:]
    if dist2(pts[0], pts[-1]) > 1e-9:
        pts.append(pts[0])

    s = 0.0
    for i in range(len(pts) - 1):
        s += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return abs(s) * 0.5


def point_in_polygon(point: Point2D, polygon: List[Point2D]) -> bool:
    """
    Алгоритм ray casting.
    """
    if len(polygon) < 3:
        return False

    pts = polygon[:]
    if dist2(pts[0], pts[-1]) > 1e-9:
        pts.append(pts[0])

    x, y = point
    inside = False

    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]

        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / ((y2 - y1) + 1e-12) + x1
        )
        if intersects:
            inside = not inside

    return inside


def chaikin_closed(polyline: List[Point2D], iterations: int = 2) -> List[Point2D]:
    """
    Згладжування замкненого контуру алгоритмом Чайкіна.
    """
    if len(polyline) < 4:
        return polyline

    pts = polyline[:]
    if dist2(pts[0], pts[-1]) < 1e-9:
        pts = pts[:-1]

    for _ in range(iterations):
        new_pts = []
        n = len(pts)
        for i in range(n):
            p = pts[i]
            q = pts[(i + 1) % n]

            q1 = (0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1])
            q2 = (0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1])

            new_pts.append(q1)
            new_pts.append(q2)

        pts = new_pts

    pts.append(pts[0])
    return pts


# ==========================================
# Поля двох моделей
# ==========================================
def metaballs_field(x: float, y: float, z: float, centers: List[Point3D], radius: float) -> float:
    """
    Поле метакульок:
        F = sum( R^2 / (d^2 + eps) )
    """
    eps = 1e-6
    value = 0.0

    for cx, cy, cz in centers:
        dx = x - cx
        dy = y - cy
        dz = z - cz
        d2 = dx * dx + dy * dy + dz * dz
        value += (radius * radius) / (d2 + eps)

    return value


def metaballs_scalar_field(x: float, y: float) -> float:
    radius = 220.0
    return metaballs_field(x, y, Z_SLICE, POINTS_3D, radius)


def lemniscate_scalar_field(x: float, y: float) -> float:
    """
    Стабільна логарифмічна форма багатофокусної лемніскати:
        L(x,y) = sum( log( sqrt(d_i^2 + alpha^2) ) )

    Ізолінії L = const є багатофокусними лемніскатами.
    """
    alpha = 90.0
    value = 0.0

    for cx, cy, cz in POINTS_3D:
        dx = x - cx
        dy = y - cy
        dz = Z_SLICE - cz
        d2 = dx * dx + dy * dy + dz * dz
        value += 0.5 * math.log(d2 + alpha * alpha)

    return value


# ==========================================
# Marching Squares
# ==========================================
# Кути клітинки:
# p0 = нижній лівий
# p1 = нижній правий
# p2 = верхній правий
# p3 = верхній лівий
#
# Ребра:
# 0: p0-p1
# 1: p1-p2
# 2: p2-p3
# 3: p3-p0

MS_TABLE = {
    0: [],
    1: [(3, 0)],
    2: [(0, 1)],
    3: [(3, 1)],
    4: [(1, 2)],
    5: [(3, 2), (0, 1)],
    6: [(0, 2)],
    7: [(3, 2)],
    8: [(2, 3)],
    9: [(0, 2)],
    10: [(0, 3), (1, 2)],
    11: [(1, 2)],
    12: [(1, 3)],
    13: [(0, 1)],
    14: [(3, 0)],
    15: [],
}


def interpolate_iso(p1: Point2D, p2: Point2D, v1: float, v2: float, iso: float) -> Point2D:
    eps = 1e-12
    if abs(v2 - v1) < eps:
        return ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5)

    t = (iso - v1) / (v2 - v1)
    t = max(0.0, min(1.0, t))
    return (
        p1[0] + t * (p2[0] - p1[0]),
        p1[1] + t * (p2[1] - p1[1]),
    )


def edge_point(
    edge_id: int,
    p0: Point2D, p1: Point2D, p2: Point2D, p3: Point2D,
    v0: float, v1: float, v2: float, v3: float,
    iso: float
) -> Point2D:
    if edge_id == 0:
        return interpolate_iso(p0, p1, v0, v1, iso)
    if edge_id == 1:
        return interpolate_iso(p1, p2, v1, v2, iso)
    if edge_id == 2:
        return interpolate_iso(p2, p3, v2, v3, iso)
    if edge_id == 3:
        return interpolate_iso(p3, p0, v3, v0, iso)
    raise ValueError("Invalid edge id")


def asymptotic_decider(v0: float, v1: float, v2: float, v3: float, iso: float) -> bool:
    center = 0.25 * (v0 + v1 + v2 + v3)
    return center > iso


def generate_grid(
    field_func,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    nx: int = 260,
    ny: int = 260
):
    xs = [x_min + i * (x_max - x_min) / nx for i in range(nx + 1)]
    ys = [y_min + j * (y_max - y_min) / ny for j in range(ny + 1)]
    values = [[field_func(x, y) for x in xs] for y in ys]
    return xs, ys, values


def contour_segments_from_grid(xs, ys, values, iso: float) -> List[Tuple[Point2D, Point2D]]:
    ny = len(ys) - 1
    nx = len(xs) - 1
    segments = []

    for j in range(ny):
        for i in range(nx):
            p0 = (xs[i], ys[j])
            p1 = (xs[i + 1], ys[j])
            p2 = (xs[i + 1], ys[j + 1])
            p3 = (xs[i], ys[j + 1])

            v0 = values[j][i]
            v1 = values[j][i + 1]
            v2 = values[j + 1][i + 1]
            v3 = values[j + 1][i]

            state = 0
            if v0 > iso:
                state |= 1
            if v1 > iso:
                state |= 2
            if v2 > iso:
                state |= 4
            if v3 > iso:
                state |= 8

            cases = MS_TABLE[state]
            if not cases:
                continue

            if state in (5, 10):
                decider = asymptotic_decider(v0, v1, v2, v3, iso)
                if state == 5:
                    cases = [(3, 0), (1, 2)] if decider else [(3, 2), (0, 1)]
                else:
                    cases = [(0, 1), (2, 3)] if decider else [(0, 3), (1, 2)]

            for e1, e2 in cases:
                a = edge_point(e1, p0, p1, p2, p3, v0, v1, v2, v3, iso)
                b = edge_point(e2, p0, p1, p2, p3, v0, v1, v2, v3, iso)
                segments.append((a, b))

    return segments


# ==========================================
# Збирання сегментів у контури
# ==========================================
def point_key(p: Point2D, digits: int = 4) -> Tuple[float, float]:
    return (round(p[0], digits), round(p[1], digits))


def build_polylines(segments: List[Tuple[Point2D, Point2D]]) -> List[List[Point2D]]:
    unused = segments[:]
    polylines = []

    while unused:
        a, b = unused.pop()
        poly = [a, b]

        changed = True
        while changed:
            changed = False
            start_key = point_key(poly[0])
            end_key = point_key(poly[-1])

            for idx, (u, v) in enumerate(unused):
                uk = point_key(u)
                vk = point_key(v)

                if uk == end_key:
                    poly.append(v)
                    unused.pop(idx)
                    changed = True
                    break
                if vk == end_key:
                    poly.append(u)
                    unused.pop(idx)
                    changed = True
                    break
                if vk == start_key:
                    poly.insert(0, u)
                    unused.pop(idx)
                    changed = True
                    break
                if uk == start_key:
                    poly.insert(0, v)
                    unused.pop(idx)
                    changed = True
                    break

        polylines.append(poly)

    return polylines


def extract_closed_contours(
    polylines: List[List[Point2D]],
    closure_tol: float
) -> List[List[Point2D]]:
    closed = []
    for poly in polylines:
        if len(poly) < 4:
            continue
        if dist2(poly[0], poly[-1]) <= closure_tol:
            closed.append(ensure_closed(poly))
    return closed


def choose_single_contour(
    contours: List[List[Point2D]],
    reference_point: Point2D
) -> Optional[List[Point2D]]:
    if not contours:
        return None

    containing = [c for c in contours if point_in_polygon(reference_point, c)]
    if containing:
        containing.sort(key=polygon_area, reverse=True)
        return containing[0]

    contours.sort(key=polygon_area, reverse=True)
    return contours[0]


# ==========================================
# Підбір ізорівня
# ==========================================
def flatten_grid(values) -> List[float]:
    flat = []
    for row in values:
        flat.extend(row)
    return flat


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = int(p * (len(s) - 1))
    return s[idx]


def auto_find_single_closed_contour(
    field_func,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    reference_point: Point2D,
    nx: int = 160,
    ny: int = 160
) -> Tuple[List[Point2D], float]:
    xs, ys, values = generate_grid(field_func, x_min, x_max, y_min, y_max, nx=nx, ny=ny)
    flat = flatten_grid(values)

    dx = (x_max - x_min) / nx
    dy = (y_max - y_min) / ny
    closure_tol = 2.2 * math.hypot(dx, dy)

    # Беремо значно менше кандидатів, щоб не вбити продуктивність
    candidate_percentiles = [
        0.20, 0.25, 0.30, 0.35, 0.40,
        0.45, 0.50, 0.55, 0.60, 0.65,
        0.70, 0.75, 0.80
    ]
    candidates = [percentile(flat, p) for p in candidate_percentiles]

    best_contour = None
    best_iso = None
    best_score = -1.0

    for iso in candidates:
        segments = contour_segments_from_grid(xs, ys, values, iso)
        if not segments:
            continue

        polylines = build_polylines(segments)
        closed = extract_closed_contours(polylines, closure_tol=closure_tol)

        if not closed:
            continue

        contour = choose_single_contour(closed, reference_point)
        if contour is None:
            continue

        area = polygon_area(contour)

        # Додатково відсікаємо підозріло маленькі уламки
        if area < 500.0:
            continue

        if area > best_score:
            best_score = area
            best_contour = contour
            best_iso = iso

    if best_contour is None:
        raise RuntimeError("Не вдалося знайти замкнений контур для підібраних ізорівнів.")

    return best_contour, best_iso


# ==========================================
# SVG
# ==========================================
def compute_bounds(points: List[Point2D]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def svg_transform(
    points: List[Point2D],
    canvas_size: int = 1600,
    padding: int = 120
) -> Tuple[float, float, float]:
    min_x, max_x, min_y, max_y = compute_bounds(points)
    w = max_x - min_x
    h = max_y - min_y

    if w == 0:
        w = 1
    if h == 0:
        h = 1

    scale = min((canvas_size - 2 * padding) / w, (canvas_size - 2 * padding) / h)
    tx = (canvas_size - w * scale) / 2 - min_x * scale
    ty = (canvas_size - h * scale) / 2 - min_y * scale

    return scale, tx, ty


def polyline_to_svg_path(polyline: List[Point2D]) -> str:
    if not polyline:
        return ""

    parts = [f"M {polyline[0][0]:.3f},{polyline[0][1]:.3f}"]
    for p in polyline[1:]:
        parts.append(f"L {p[0]:.3f},{p[1]:.3f}")
    parts.append("Z")
    return " ".join(parts)


def save_svg(
    contour: List[Point2D],
    filename: str,
    title: str,
    centers_2d: List[Point2D],
    canvas_size: int = 1600,
    padding: int = 120
) -> None:
    fit_points = contour + centers_2d
    scale, tx, ty = svg_transform(fit_points, canvas_size=canvas_size, padding=padding)

    path_d = polyline_to_svg_path(contour)

    grid = []
    step = 100
    for x in range(0, canvas_size + 1, step):
        grid.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{canvas_size}" stroke="#e8e8e8" stroke-width="1"/>')
    for y in range(0, canvas_size + 1, step):
        grid.append(f'<line x1="0" y1="{y}" x2="{canvas_size}" y2="{y}" stroke="#e8e8e8" stroke-width="1"/>')

    point_radius = 10 / scale
    point_stroke = 3 / scale
    font_size = 26 / scale
    label_dx = 16 / scale
    label_dy = -16 / scale

    points_svg = []
    for i, (x, y) in enumerate(centers_2d, start=1):
        points_svg.append(
            f'<circle cx="{x}" cy="{y}" r="{point_radius:.4f}" fill="#d62828" stroke="white" stroke-width="{point_stroke:.4f}" />'
        )
        points_svg.append(
            f'<text x="{x + label_dx:.4f}" y="{y + label_dy:.4f}" font-size="{font_size:.4f}" font-family="Arial" fill="#222">P{i}</text>'
        )

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{canvas_size}" height="{canvas_size}"
     viewBox="0 0 {canvas_size} {canvas_size}"
     xmlns="http://www.w3.org/2000/svg">

    <rect width="100%" height="100%" fill="#fcfcfc"/>
    {"".join(grid)}
    <rect x="20" y="20" width="{canvas_size - 40}" height="{canvas_size - 40}"
          fill="none" stroke="#bdbdbd" stroke-width="2"/>

    <text x="60" y="80" font-size="40" font-family="Arial" fill="#222">
        {title}
    </text>

    <g transform="translate({tx:.4f},{ty:.4f}) scale({scale:.4f})">
        <path d="{path_d}"
              fill="none"
              stroke="#111"
              stroke-width="{4 / scale:.4f}" />
        {"".join(points_svg)}
    </g>

</svg>
'''
    with open(filename, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"SVG-файл збережено: {filename}")


# ==========================================
# Основна логіка
# ==========================================
def main():
    centers_2d = [(p[0], p[1]) for p in POINTS_3D]

    xs = [p[0] for p in centers_2d]
    ys = [p[1] for p in centers_2d]

    margin = 180.0
    x_min = max(0.0, min(xs) - margin)
    x_max = min(512.0, max(xs) + margin)
    y_min = max(0.0, min(ys) - margin)
    y_max = min(512.0, max(ys) + margin)

    reference_point = (
        sum(x for x, _ in centers_2d) / len(centers_2d),
        sum(y for _, y in centers_2d) / len(centers_2d),
    )

    # Метакульки
    meta_contour, meta_iso = auto_find_single_closed_contour(
        field_func=metaballs_scalar_field,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        reference_point=reference_point,
        nx=160,
        ny=160
    )

    meta_contour = chaikin_closed(meta_contour, iterations=2)

    save_svg(
        contour=meta_contour,
        filename="lab2_metaballs_variant18.svg",
        title=f"Metaballs slice at z = 256 (variant 18, iso = {meta_iso:.4f})",
        centers_2d=centers_2d
    )

    # Багатофокусна лемніската
    lemni_contour, lemni_iso = auto_find_single_closed_contour(
        field_func=lemniscate_scalar_field,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        reference_point=reference_point,
        nx=160,
        ny=160
    )

    lemni_contour = chaikin_closed(lemni_contour, iterations=2)

    save_svg(
        contour=lemni_contour,
        filename="lab2_lemniscate_variant18.svg",
        title=f"Multifocal lemniscate slice at z = 256 (variant 18, iso = {lemni_iso:.4f})",
        centers_2d=centers_2d
    )


if __name__ == "__main__":
    main()