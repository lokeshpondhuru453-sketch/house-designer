from schemas import Requirements
from shapely.geometry import Polygon

MIN_ROOM_SIZES = {
    "bedroom": 9.0,
    "bathroom": 3.0,
    "kitchen": 6.0,
    "living_room": 12.0,
}

def check_total_area(req: Requirements) -> bool:
    plot_area = req.plot.width * req.plot.length
    room_area = sum(r.w * r.h for r in req.rooms)
    return room_area <= 0.85 * plot_area

def check_min_sizes(req: Requirements) -> bool:
    for r in req.rooms:
        area = r.w * r.h
        base = next((k for k in MIN_ROOM_SIZES if k in r.name), None)
        if base and area < MIN_ROOM_SIZES[base]:
            return False
    return True

def check_room_overlap(layout: dict) -> bool:
    polys = [Polygon(r["polygon"]) for r in layout["rooms"]]
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            if polys[i].intersects(polys[j]) and not polys[i].touches(polys[j]):
                return True
    return False

def validate_requirements(req: Requirements) -> dict:
    errors = []
    if not check_total_area(req):
        errors.append("Total room area exceeds 85% of plot area.")
    if not check_min_sizes(req):
        errors.append("One or more rooms are below minimum size.")
    return {"valid": len(errors) == 0, "errors": errors}