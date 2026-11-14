"""Primitive ASCII signal sensing and four-connected component analysis."""
from collections import deque


PERCEPTION_VERSION = "ascii_components_4_v1"


def validate_field(field):
    if not isinstance(field, str) or not field:
        raise ValueError("Field must be a non-empty string")
    rows = field.splitlines()
    if not rows or not rows[0]:
        raise ValueError("Field rows must be non-empty")
    if any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Field must be rectangular")
    if any(not 32 <= ord(char) <= 126 for row in rows for char in row):
        raise ValueError("Field must contain printable ASCII characters only")
    return rows


def _component_holes(cells, rows):
    min_x = min(x for x, _ in cells)
    max_x = max(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    max_y = max(y for _, y in cells)
    occupied = set(cells)
    # Only explicit background is empty; cells carrying another signal are obstacles.
    empty = {(x, y) for y in range(min_y, max_y + 1)
             for x in range(min_x, max_x + 1)
             if (x, y) not in occupied and rows[y][x] == "."}
    exterior = set()
    queue = deque()
    for x, y in empty:
        if x in (min_x, max_x) or y in (min_y, max_y):
            exterior.add((x, y))
            queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if neighbor in empty and neighbor not in exterior:
                exterior.add(neighbor)
                queue.append(neighbor)
    holes = empty - exterior
    return sorted([list(point) for point in holes], key=lambda point: (point[1], point[0]))


def extract_components(field):
    """Extract exact-signal four-connected components; coordinates are [x, y]."""
    rows = validate_field(field)
    height, width = len(rows), len(rows[0])
    seen = set()
    components = []
    for y in range(height):
        for x in range(width):
            signal = rows[y][x]
            if signal == "." or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            cells = []
            while queue:
                cx, cy = queue.popleft()
                cells.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if (0 <= nx < width and 0 <= ny < height and
                            (nx, ny) not in seen and rows[ny][nx] == signal):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            cells.sort(key=lambda point: (point[1], point[0]))
            xs = [point[0] for point in cells]
            ys = [point[1] for point in cells]
            min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
            box_width, box_height = max_x - min_x + 1, max_y - min_y + 1
            holes = _component_holes(cells, rows)
            boundary = {(min_x + dx, min_y + dy)
                        for dx in range(box_width) for dy in range(box_height)
                        if dx in (0, box_width - 1) or dy in (0, box_height - 1)}
            features = {
                "cell_count": len(cells), "width": box_width, "height": box_height,
                "fills_bbox": len(cells) == box_width * box_height,
                "rectangular_frame": (box_width > 2 and box_height > 2 and
                                      occupied_boundary(cells, boundary)),
                "hole_count": len(holes),
            }
            components.append({
                "id": f"component_{len(components) + 1}", "signal": signal,
                "cells": [list(point) for point in cells], "cell_count": len(cells),
                "bounding_box": {"min_x": min_x, "min_y": min_y,
                                 "max_x": max_x, "max_y": max_y},
                "width": box_width, "height": box_height,
                "center": {"x": sum(xs) / len(xs), "y": sum(ys) / len(ys)},
                "holes": {"count": len(holes), "cells": holes,
                          "method": "4-connected background cells enclosed inside component bounding box"},
                "features": features,
            })
    return components


def occupied_boundary(cells, boundary):
    return boundary.issubset(set(cells))


def component_relations(components):
    relations = []
    for index, left in enumerate(components):
        a = left["bounding_box"]
        ca = left["center"]
        for right in components[index + 1:]:
            b = right["bounding_box"]
            cb = right["center"]
            dx, dy = cb["x"] - ca["x"], cb["y"] - ca["y"]
            relations.append({
                "from": left["id"], "to": right["id"],
                "left_of": a["max_x"] < b["min_x"], "right_of": a["min_x"] > b["max_x"],
                "above": a["max_y"] < b["min_y"], "below": a["min_y"] > b["max_y"],
                "horizontal_projection_overlap": not (a["max_x"] < b["min_x"] or b["max_x"] < a["min_x"]),
                "vertical_projection_overlap": not (a["max_y"] < b["min_y"] or b["max_y"] < a["min_y"]),
                "center_distance": (dx * dx + dy * dy) ** 0.5,
            })
    return relations
