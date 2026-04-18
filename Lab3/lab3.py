import math
import time
from typing import List, Tuple, Dict, Optional
from collections import deque

Point = Tuple[float, float]
Segment = Tuple[Point, Point]


# =========================================================
# 1. Raster generation
# =========================================================

def point_in_rotated_ellipse(
    x: float,
    y: float,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    angle_deg: float
) -> bool:
    angle = math.radians(angle_deg)
    ca = math.cos(angle)
    sa = math.sin(angle)

    dx = x - cx
    dy = y - cy

    xr = dx * ca + dy * sa
    yr = -dx * sa + dy * ca

    return (xr * xr) / (rx * rx) + (yr * yr) / (ry * ry) <= 1.0


def point_in_triangle(px: float, py: float, a: Point, b: Point, c: Point) -> bool:
    def sign(p1: Point, p2: Point, p3: Point) -> float:
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    p = (px, py)
    d1 = sign(p, a, b)
    d2 = sign(p, b, c)
    d3 = sign(p, c, a)

    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

    return not (has_neg and has_pos)


def generate_orca_raster(width: int = 30, height: int = 25) -> List[List[int]]:
    """
    30x25 raster with a dark orca silhouette on a light background.
    Background = 220
    Orca body = 30
    """

    pattern = [
        "000000000000000001110000000000",
        "000000000000000011110000000000",
        "000000000000000111100000000000",
        "000000000000001111100000000000",
        "000000000000001111100000000000",
        "000000000111111111100000000000",
        "000011111111111111100000000000",
        "000111111111111111110000000000",
        "011111111111111111111100000000",
        "011111111111111111111110000000",
        "111111111111111111111111000000",
        "111111111111111111111111100000",
        "111111111111111111111111100000",
        "011111111111111111111111110000",
        "000111111111111111111111111000",
        "000001111111111111111111111000",
        "000000011111111111111111111000",
        "000000000111111111111111111000",
        "000000000001111111111111111100",
        "000000000000000000001111111100",
        "000000000000000000000111111100",
        "000000000000000000000011111110",
        "000000000000000000000011111111",
        "000000000000000000000011100111",
        "000000000000000000000011000011",
    ]

    if width != 30 or height != 25:
        raise ValueError("This raster template is designed exactly for 30x25.")

    raster = []
    for row in pattern:
        raster_row = []
        for ch in row:
            if ch == "1":
                raster_row.append(30)   # dark body
            else:
                raster_row.append(220)  # light background
        raster.append(raster_row)

    return raster

def raster_to_dark_mask(raster: List[List[int]], level: float = 128) -> List[List[bool]]:
    """
    True = dark object (orca), False = light background
    """
    h = len(raster)
    w = len(raster[0])
    return [[raster[j][i] <= level for i in range(w)] for j in range(h)]


def largest_connected_component(mask: List[List[bool]]) -> List[List[bool]]:
    h = len(mask)
    w = len(mask[0])
    visited = [[False] * w for _ in range(h)]

    best_cells = []

    for j in range(h):
        for i in range(w):
            if mask[j][i] and not visited[j][i]:
                q = deque()
                q.append((i, j))
                visited[j][i] = True
                cells = []

                while q:
                    x, y = q.popleft()
                    cells.append((x, y))

                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            if mask[ny][nx] and not visited[ny][nx]:
                                visited[ny][nx] = True
                                q.append((nx, ny))

                if len(cells) > len(best_cells):
                    best_cells = cells

    result = [[False] * w for _ in range(h)]
    for x, y in best_cells:
        result[y][x] = True

    return result


def exterior_background(mask: List[List[bool]]) -> List[List[bool]]:
    """
    Returns True for light-background cells connected to the image border.
    Holes inside the object are NOT marked as exterior.
    """
    h = len(mask)
    w = len(mask[0])

    ext = [[False] * w for _ in range(h)]
    q = deque()

    def try_push(x: int, y: int):
        if 0 <= x < w and 0 <= y < h and not mask[y][x] and not ext[y][x]:
            ext[y][x] = True
            q.append((x, y))

    for i in range(w):
        try_push(i, 0)
        try_push(i, h - 1)

    for j in range(h):
        try_push(0, j)
        try_push(w - 1, j)

    while q:
        x, y = q.popleft()
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            try_push(x + dx, y + dy)

    return ext


def extract_outer_boundary(mask: List[List[bool]]) -> List[Point]:
    """
    Extracts only the OUTER boundary of the largest dark component.
    Boundary is returned as a closed polyline in grid coordinates.
    """
    h = len(mask)
    w = len(mask[0])

    obj = largest_connected_component(mask)
    ext = exterior_background(obj)

    edges = []

    for j in range(h):
        for i in range(w):
            if not obj[j][i]:
                continue

            # If neighbor is exterior background, this side belongs to the OUTER boundary

            # top
            if j == 0 or ext[j - 1][i]:
                edges.append(((i, j), (i + 1, j)))

            # right
            if i == w - 1 or ext[j][i + 1]:
                edges.append(((i + 1, j), (i + 1, j + 1)))

            # bottom
            if j == h - 1 or ext[j + 1][i]:
                edges.append(((i + 1, j + 1), (i, j + 1)))

            # left
            if i == 0 or ext[j][i - 1]:
                edges.append(((i, j + 1), (i, j)))

    if not edges:
        return []

    outgoing = {}
    for a, b in edges:
        outgoing.setdefault(a, []).append(b)

    start = min(outgoing.keys(), key=lambda p: (p[1], p[0]))
    contour = [start]
    current = start

    visited = set()

    while True:
        if current not in outgoing:
            break

        candidates = outgoing[current]
        next_point = None

        for cand in candidates:
            ek = (current, cand)
            if ek not in visited:
                next_point = cand
                visited.add(ek)
                break

        if next_point is None:
            break

        contour.append(next_point)
        current = next_point

        if current == start:
            break

    if len(contour) >= 2 and contour[0] != contour[-1]:
        contour.append(contour[0])

    return [(float(x), float(y)) for x, y in contour]

# =========================================================
# 2. Marching Squares
# =========================================================

def interpolate_edge(p1: Point, p2: Point, v1: float, v2: float, level: float) -> Point:
    if abs(v2 - v1) < 1e-12:
        return ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5)

    t = (level - v1) / (v2 - v1)
    t = max(0.0, min(1.0, t))
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))


def marching_squares_segments(raster: List[List[int]], level: float = 128) -> List[Segment]:
    """
    Coordinates:
      pixel centers are at integer coordinates (i, j).
      cell corners use raster[j][i].
    Cell corners:
      p00 = (i, j)       top-left
      p10 = (i+1, j)     top-right
      p11 = (i+1, j+1)   bottom-right
      p01 = (i, j+1)     bottom-left
    Edge indices:
      0 = top    (p00-p10)
      1 = right  (p10-p11)
      2 = bottom (p01-p11)
      3 = left   (p00-p01)
    """
    h = len(raster)
    w = len(raster[0])

    segments: List[Segment] = []

    for j in range(h - 1):
        for i in range(w - 1):
            v00 = raster[j][i]
            v10 = raster[j][i + 1]
            v11 = raster[j + 1][i + 1]
            v01 = raster[j + 1][i]

            p00 = (float(i), float(j))
            p10 = (float(i + 1), float(j))
            p11 = (float(i + 1), float(j + 1))
            p01 = (float(i), float(j + 1))

            b0 = 1 if v00 <= level else 0
            b1 = 1 if v10 <= level else 0
            b2 = 1 if v11 <= level else 0
            b3 = 1 if v01 <= level else 0

            case = b0 | (b1 << 1) | (b2 << 2) | (b3 << 3)

            if case == 0 or case == 15:
                continue

            edge_points: Dict[int, Point] = {}

            # Top
            if b0 != b1:
                edge_points[0] = interpolate_edge(p00, p10, v00, v10, level)
            # Right
            if b1 != b2:
                edge_points[1] = interpolate_edge(p10, p11, v10, v11, level)
            # Bottom
            if b3 != b2:
                edge_points[2] = interpolate_edge(p01, p11, v01, v11, level)
            # Left
            if b0 != b3:
                edge_points[3] = interpolate_edge(p00, p01, v00, v01, level)

            # Standard cases
            simple_cases = {
                1:  [(3, 0)],
                2:  [(0, 1)],
                3:  [(3, 1)],
                4:  [(1, 2)],
                6:  [(0, 2)],
                7:  [(3, 2)],
                8:  [(2, 3)],
                9:  [(0, 2)],
                11: [(1, 2)],
                12: [(3, 1)],
                13: [(0, 1)],
                14: [(3, 0)],
            }

            if case in simple_cases:
                for e1, e2 in simple_cases[case]:
                    segments.append((edge_points[e1], edge_points[e2]))
                continue

            # Ambiguous cases: 5 and 10
            center = (v00 + v10 + v11 + v01) / 4.0
            if case == 5:
                if center >= level:
                    pairs = [(3, 2), (0, 1)]
                else:
                    pairs = [(3, 0), (1, 2)]
            elif case == 10:
                if center >= level:
                    pairs = [(3, 0), (1, 2)]
                else:
                    pairs = [(0, 1), (2, 3)]
            else:
                pairs = []

            for e1, e2 in pairs:
                segments.append((edge_points[e1], edge_points[e2]))

    return segments


# =========================================================
# 3. Segment stitching into polylines
# =========================================================

def round_point(p: Point, digits: int = 6) -> Point:
    return (round(p[0], digits), round(p[1], digits))


def stitch_segments(segments: List[Segment]) -> List[List[Point]]:
    """
    Joins contour segments into polylines/closed contours.
    """
    adjacency: Dict[Point, List[Point]] = {}

    for a, b in segments:
        aa = round_point(a)
        bb = round_point(b)
        adjacency.setdefault(aa, []).append(bb)
        adjacency.setdefault(bb, []).append(aa)

    visited_edges = set()
    contours: List[List[Point]] = []

    def edge_key(p1: Point, p2: Point):
        return tuple(sorted((p1, p2)))

    for start in adjacency:
        for nxt in adjacency[start]:
            ek = edge_key(start, nxt)
            if ek in visited_edges:
                continue

            contour = [start]
            prev = None
            curr = start
            next_point = nxt

            while True:
                visited_edges.add(edge_key(curr, next_point))
                contour.append(next_point)

                prev, curr = curr, next_point
                neighbors = adjacency[curr]

                candidates = [p for p in neighbors if edge_key(curr, p) not in visited_edges]

                if not candidates:
                    break

                if len(candidates) == 1:
                    next_point = candidates[0]
                else:
                    # Prefer the candidate that is not just going backward
                    best = candidates[0]
                    if prev is not None:
                        vx = curr[0] - prev[0]
                        vy = curr[1] - prev[1]

                        best_score = -1e18
                        for c in candidates:
                            wx = c[0] - curr[0]
                            wy = c[1] - curr[1]
                            score = vx * wx + vy * wy
                            if score > best_score:
                                best_score = score
                                best = c
                    next_point = best

                if next_point == contour[0]:
                    visited_edges.add(edge_key(curr, next_point))
                    contour.append(next_point)
                    break

            if len(contour) >= 4:
                contours.append(contour)

    # Deduplicate very similar contours
    unique = []
    seen = set()
    for c in contours:
        key = tuple(c)
        rev = tuple(reversed(c))
        if key not in seen and rev not in seen:
            seen.add(key)
            unique.append(c)

    return unique


def contour_length(poly: List[Point]) -> float:
    total = 0.0
    for i in range(1, len(poly)):
        dx = poly[i][0] - poly[i - 1][0]
        dy = poly[i][1] - poly[i - 1][1]
        total += math.hypot(dx, dy)
    return total


def polygon_area(poly: List[Point]) -> float:
    if len(poly) < 3:
        return 0.0
    pts = poly[:-1] if poly[0] == poly[-1] else poly
    area = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def choose_main_contour(contours: List[List[Point]], raster: List[List[int]], level: float = 128) -> Optional[List[Point]]:
    if not contours:
        return None

    closed = [c for c in contours if len(c) >= 4 and c[0] == c[-1]]
    if not closed:
        closed = contours[:]

    dark_candidates = []
    for c in closed:
        mean_val = contour_mean_value(c, raster)
        area = abs(polygon_area(c))

        # We want contours whose interior is dark (object), not light holes
        if mean_val < level:
            dark_candidates.append((area, mean_val, c))

    if dark_candidates:
        dark_candidates.sort(key=lambda item: item[0], reverse=True)
        return dark_candidates[0][2]

    # fallback: largest contour
    return max(closed, key=lambda c: abs(polygon_area(c)))


# =========================================================
# 4. Smoothing and conversion to Bezier
# =========================================================

def chaikin_closed(poly: List[Point], iterations: int = 2) -> List[Point]:
    pts = poly[:-1] if poly[0] == poly[-1] else poly[:]
    for _ in range(iterations):
        new_pts = []
        n = len(pts)
        for i in range(n):
            p0 = pts[i]
            p1 = pts[(i + 1) % n]
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_pts.extend([q, r])
        pts = new_pts
    pts.append(pts[0])
    return pts


def closed_catmull_rom_to_bezier(poly: List[Point], tension: float = 1.0) -> List[Tuple[Point, Point, Point, Point]]:
    """
    Converts a closed polyline to cubic Bezier segments.
    Returns list of segments: (P0, C1, C2, P1)
    """
    pts = poly[:-1] if poly[0] == poly[-1] else poly[:]
    n = len(pts)
    result = []

    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]

        c1 = (
            p1[0] + (p2[0] - p0[0]) * (tension / 6.0),
            p1[1] + (p2[1] - p0[1]) * (tension / 6.0),
        )
        c2 = (
            p2[0] - (p3[0] - p1[0]) * (tension / 6.0),
            p2[1] - (p3[1] - p1[1]) * (tension / 6.0),
        )

        result.append((p1, c1, c2, p2))

    return result


# =========================================================
# 5. SVG output
# =========================================================

def svg_header(width: int, height: int, viewbox: Tuple[float, float, float, float]) -> str:
    vx, vy, vw, vh = viewbox
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="{vx} {vy} {vw} {vh}">\n'
    )


def save_svg(
    filename: str,
    raster: List[List[int]],
    bezier_segments: List[Tuple[Point, Point, Point, Point]],
    cell_size: int = 22,
    margin: int = 20
) -> None:
    h = len(raster)
    w = len(raster[0])

    svg_w = margin * 2 + w * cell_size
    svg_h = margin * 2 + h * cell_size

    parts = []
    parts.append(svg_header(svg_w, svg_h, (0, 0, svg_w, svg_h)))

    parts.append(f'<rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="white"/>\n')

    # raster
    for j in range(h):
        for i in range(w):
            v = raster[j][i]
            gray = max(0, min(255, int(v)))
            x = margin + i * cell_size
            y = margin + j * cell_size
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                f'fill="rgb({gray},{gray},{gray})" stroke="none"/>\n'
            )

    # grid
    for i in range(w + 1):
        x = margin + i * cell_size
        parts.append(
            f'<line x1="{x}" y1="{margin}" x2="{x}" y2="{margin + h * cell_size}" '
            f'stroke="#b8b8b8" stroke-width="0.8"/>\n'
        )

    for j in range(h + 1):
        y = margin + j * cell_size
        parts.append(
            f'<line x1="{margin}" y1="{y}" x2="{margin + w * cell_size}" y2="{y}" '
            f'stroke="#b8b8b8" stroke-width="0.8"/>\n'
        )

    parts.append(
        f'<text x="{margin}" y="{margin - 6}" font-size="14" font-family="Arial" '
        f'fill="black">Vectorization of 30x25 raster, iso-level r = 128</text>\n'
    )

    # only final smooth bezier curve
    if bezier_segments:
        p0 = bezier_segments[0][0]
        d = [f'M {margin + p0[0] * cell_size:.3f} {margin + p0[1] * cell_size:.3f}']
        for seg in bezier_segments:
            _, c1, c2, p1 = seg
            d.append(
                f'C {margin + c1[0] * cell_size:.3f} {margin + c1[1] * cell_size:.3f}, '
                f'{margin + c2[0] * cell_size:.3f} {margin + c2[1] * cell_size:.3f}, '
                f'{margin + p1[0] * cell_size:.3f} {margin + p1[1] * cell_size:.3f}'
            )
        d.append('Z')

        parts.append(
            f'<path d="{" ".join(d)}" fill="none" stroke="#1aa6a6" stroke-width="3.0" '
            f'stroke-linecap="round" stroke-linejoin="round"/>\n'
        )

    parts.append('</svg>\n')

    with open(filename, "w", encoding="utf-8") as f:
        f.write("".join(parts))


# =========================================================
# 6. Scaling experiment
# =========================================================

def upscale_nearest(raster: List[List[int]], factor: int) -> List[List[int]]:
    h = len(raster)
    w = len(raster[0])
    out = [[0 for _ in range(w * factor)] for _ in range(h * factor)]

    for j in range(h * factor):
        for i in range(w * factor):
            out[j][i] = raster[j // factor][i // factor]

    return out


def estimate_memory_bytes(raster: List[List[int]], segments: List[Segment], contour: Optional[List[Point]]) -> int:
    """
    Rough educational estimate, not exact Python object memory.
    """
    h = len(raster)
    w = len(raster[0])

    raster_mem = h * w * 8  # assume ~8 bytes per scalar as rough estimate
    seg_mem = len(segments) * 4 * 8  # 2 points * 2 coords * 8 bytes
    contour_mem = (len(contour) if contour else 0) * 2 * 8

    return raster_mem + seg_mem + contour_mem


def run_scaling_experiment(base_raster: List[List[int]], level: float = 128) -> None:
    print("\nScaling experiment:")
    print(f"{'Scale':>6} | {'Size':>10} | {'Time (ms)':>12} | {'Contour pts':>11} | {'Mem est (KB)':>12}")
    print("-" * 62)

    for factor in [1, 2, 4, 8]:
        raster = upscale_nearest(base_raster, factor) if factor > 1 else base_raster

        t0 = time.perf_counter()

        mask = raster_to_dark_mask(raster, level)
        contour = extract_outer_boundary(mask)

        t1 = time.perf_counter()

        mem_est = estimate_memory_bytes(raster, [], contour)
        size_str = f"{len(raster[0])}x{len(raster)}"
        contour_pts = len(contour) if contour else 0

        print(
            f"{factor:>6} | {size_str:>10} | {(t1 - t0) * 1000:>12.3f} | "
            f"{contour_pts:>11} | {mem_est / 1024:>12.2f}"
        )

def point_in_polygon(pt: Point, poly: List[Point]) -> bool:
    x, y = pt
    inside = False

    pts = poly[:-1] if poly[0] == poly[-1] else poly
    n = len(pts)

    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]

        intersects = ((y1 > y) != (y2 > y))
        if intersects:
            xinters = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
            if x < xinters:
                inside = not inside

    return inside


def contour_mean_value(poly: List[Point], raster: List[List[int]]) -> float:
    """
    Average raster value inside a contour.
    Lower value => darker interior.
    """
    h = len(raster)
    w = len(raster[0])

    pts = poly[:-1] if poly[0] == poly[-1] else poly
    min_x = max(0, int(math.floor(min(p[0] for p in pts))))
    max_x = min(w - 1, int(math.ceil(max(p[0] for p in pts))))
    min_y = max(0, int(math.floor(min(p[1] for p in pts))))
    max_y = min(h - 1, int(math.ceil(max(p[1] for p in pts))))

    total = 0.0
    count = 0

    for j in range(min_y, max_y + 1):
        for i in range(min_x, max_x + 1):
            # sample at cell center
            sample = (i + 0.5, j + 0.5)
            if point_in_polygon(sample, poly):
                total += raster[j][i]
                count += 1

    if count == 0:
        return 255.0

    return total / count

def simplify_polyline(poly: List[Point], step: int = 3) -> List[Point]:
    """
    Downsample closed contour: keep every N-th point.
    This removes the pixel stair effect before smoothing.
    """
    if len(poly) < 6:
        return poly[:]

    closed = poly[0] == poly[-1]
    pts = poly[:-1] if closed else poly[:]

    result = pts[::step]

    if len(result) < 4:
        result = pts[:]

    if closed:
        if result[0] != result[-1]:
            result.append(result[0])

    return result

def laplacian_smooth_closed(poly: List[Point], iterations: int = 3, alpha: float = 0.5) -> List[Point]:
    """
    Smooth closed contour by averaging each point with its neighbors.
    """
    if len(poly) < 4:
        return poly[:]

    pts = poly[:-1] if poly[0] == poly[-1] else poly[:]

    for _ in range(iterations):
        new_pts = []
        n = len(pts)
        for i in range(n):
            p_prev = pts[(i - 1) % n]
            p = pts[i]
            p_next = pts[(i + 1) % n]

            avg_x = 0.5 * (p_prev[0] + p_next[0])
            avg_y = 0.5 * (p_prev[1] + p_next[1])

            new_x = (1 - alpha) * p[0] + alpha * avg_x
            new_y = (1 - alpha) * p[1] + alpha * avg_y

            new_pts.append((new_x, new_y))

        pts = new_pts

    pts.append(pts[0])
    return pts

# =========================================================
# 7. Main pipeline
# =========================================================

def build_vectorized_orca_svg():
    width = 30
    height = 25
    level = 128

    raster = generate_orca_raster(width, height)

    # Debug/reference
    segments = marching_squares_segments(raster, level)
    contours = stitch_segments(segments)

    # Outer silhouette extraction
    mask = raster_to_dark_mask(raster, level)
    main_contour = extract_outer_boundary(mask)

    if not main_contour or len(main_contour) < 4:
        raise RuntimeError("No outer contour was extracted.")

    # Stronger contour cleanup
    simplified = simplify_polyline(main_contour, step=4)
    smoothed_1 = chaikin_closed(simplified, iterations=3)
    smoothed_2 = laplacian_smooth_closed(smoothed_1, iterations=4, alpha=0.45)

    bezier = closed_catmull_rom_to_bezier(smoothed_2, tension=0.35)

    save_svg(
        "lab3_orca_vectorized.svg",
        raster,
        bezier,
        cell_size=22,
        margin=20
    )

    print("Done.")
    print(f"Segments found (Marching Squares): {len(segments)}")
    print(f"Contours found (Marching Squares): {len(contours)}")
    print(f"Outer contour points: {len(main_contour)}")
    print(f"Simplified contour points: {len(simplified)}")
    print(f"Final smoothed contour points: {len(smoothed_2)}")
    print("SVG saved to: lab3_orca_vectorized.svg")

    run_scaling_experiment(raster, level=level)


if __name__ == "__main__":
    build_vectorized_orca_svg()