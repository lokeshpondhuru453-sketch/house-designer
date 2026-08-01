import re
from schemas import Requirements


def get_count(text: str, word: str, default: int = 0) -> int:
    """
    Find counts such as:
    3 bedrooms
    3-bedroom
    2 bathrooms
    """
    patterns = [
        rf"(\d+)\s*[- ]?\s*{word}s?",
        rf"(\d+)\s+{word}s?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return default


def parse_text_to_json(text: str) -> dict:
    text = text.lower()

    rooms = []

    # Detect number of bedrooms and bathrooms
    bedrooms = get_count(text, "bedroom", 1)
    bathrooms = get_count(text, "bathroom", 1)

    # Living room
    if "living room" in text or "living_room" in text:
        rooms.append({
            "name": "living_room",
            "w": 6,
            "h": 5,
        })

    # Kitchen
    if "kitchen" in text:
        rooms.append({
            "name": "kitchen",
            "w": 4,
            "h": 4,
        })

    # Bedrooms
    for i in range(1, bedrooms + 1):
        rooms.append({
            "name": f"bedroom_{i}",
            "w": 4,
            "h": 4,
        })

    # Bathrooms
    for i in range(1, bathrooms + 1):
        rooms.append({
            "name": f"bathroom_{i}",
            "w": 3,
            "h": 3,
        })

    # Optional dining room
    if "dining room" in text or "dining area" in text:
        rooms.append({
            "name": "dining_room",
            "w": 4,
            "h": 4,
        })

    # Optional study
    if "study" in text or "office" in text:
        rooms.append({
            "name": "study",
            "w": 3.5,
            "h": 3.5,
        })

    # Basic style detection
    style = "modern"

    for possible_style in [
        "traditional",
        "minimalist",
        "contemporary",
        "luxury",
        "modern",
    ]:
        if possible_style in text:
            style = possible_style
            break

    # Basic adjacency rules
    adjacency = []

    room_names = {room["name"] for room in rooms}

    if "living_room" in room_names and "kitchen" in room_names:
        adjacency.append({
            "a": "living_room",
            "b": "kitchen",
        })

    for i in range(1, bedrooms + 1):
        bedroom = f"bedroom_{i}"

        if bedroom in room_names and "living_room" in room_names:
            adjacency.append({
                "a": "living_room",
                "b": bedroom,
            })

    data = {
        "style": style,

        "plot": {
            "width": 20,
            "length": 30,
        },

        "rooms": rooms,

        "entrance_side": "north",

        "adjacency": adjacency,
    }

    return Requirements(**data).model_dump()