def generate_layout(req: dict) -> dict:
    """
    Generate a compact orthogonal floor plan.

    Main goals:
    - Every requested room is represented when space allows.
    - Rooms are arranged in rows with exact shared boundaries.
    - Living room acts as the central room.
    - Bedrooms are placed above the living room.
    - Bathrooms are placed below the living room.
    - Kitchen is attached to the right side of the living room.
    - Coordinates are rounded so shared walls match exactly.
    """

    plot_w = float(req["plot"]["width"])
    plot_l = float(req["plot"]["length"])
    requested_rooms = req["rooms"]

    margin = 0.5
    rooms = []

    living = None
    kitchen = None
    bedrooms = []
    bathrooms = []
    others = []

    # =========================================================
    # CLASSIFY ROOMS
    # =========================================================

    for room in requested_rooms:
        name = room["name"].lower()

        if "living" in name:
            living = room

        elif "kitchen" in name:
            kitchen = room

        elif "bedroom" in name:
            bedrooms.append(room)

        elif "bathroom" in name:
            bathrooms.append(room)

        else:
            others.append(room)

    # =========================================================
    # HELPER
    # =========================================================

    def add_room(room, x, y, w=None, h=None):
        if room is None:
            return False

        if w is None:
            w = float(room["w"])

        if h is None:
            h = float(room["h"])

        x = round(float(x), 3)
        y = round(float(y), 3)
        w = round(float(w), 3)
        h = round(float(h), 3)

        if w <= 0 or h <= 0:
            return False

        # Validate plot boundary.
        if (
            x < margin - 0.001
            or y < margin - 0.001
            or x + w > plot_w - margin + 0.001
            or y + h > plot_l - margin + 0.001
        ):
            print(
                f"WARNING: Could not place {room['name']} "
                f"at ({x}, {y}) size ({w}, {h})"
            )
            return False

        polygon = [
    [x, y],
    [round(x + w, 3), y],
    [round(x + w, 3), round(y + h, 3)],
    [x, round(y + h, 3)],
    [x, y],
]

        rooms.append(
            {
                "name": room["name"],
                "polygon": polygon,
                "w": w,
                "h": h,
            }
        )

        return True

    # =========================================================
    # DIMENSIONS
    # =========================================================

    if living is None:
        raise ValueError(
            "A living room is required to generate the layout."
        )

    living_w = float(living["w"])
    living_h = float(living["h"])

    kitchen_w = (
        float(kitchen["w"])
        if kitchen
        else 0.0
    )

    kitchen_h = (
        float(kitchen["h"])
        if kitchen
        else 0.0
    )

    bedroom_total_w = sum(
        float(room["w"])
        for room in bedrooms
    )

    bedroom_max_h = max(
        (
            float(room["h"])
            for room in bedrooms
        ),
        default=0.0,
    )

    bathroom_total_w = sum(
        float(room["w"])
        for room in bathrooms
    )

    bathroom_max_h = max(
        (
            float(room["h"])
            for room in bathrooms
        ),
        default=0.0,
    )

    # =========================================================
    # HOUSE SIZE
    # =========================================================

    middle_width = (
        living_w + kitchen_w
        if kitchen
        else living_w
    )

    house_width = max(
        middle_width,
        bedroom_total_w,
        bathroom_total_w,
        living_w,
    )

    house_height = (
        bedroom_max_h
        + max(living_h, kitchen_h)
        + bathroom_max_h
    )

    available_width = plot_w - 2 * margin
    available_height = plot_l - 2 * margin

    if house_width > available_width + 0.001:
        raise ValueError(
            f"Generated house requires width "
            f"{house_width}, but plot only has "
            f"{available_width} usable units."
        )

    if house_height > available_height + 0.001:
        raise ValueError(
            f"Generated house requires height "
            f"{house_height}, but plot only has "
            f"{available_height} usable units."
        )

    # Center the whole house inside the plot.
    house_x = round(
        (plot_w - house_width) / 2,
        3,
    )

    house_y = round(
        (plot_l - house_height) / 2,
        3,
    )

    # =========================================================
    # ROW 1 — BATHROOMS
    #
    # This is the bottom row.
    # =========================================================

    bottom_y = house_y

    bathroom_x = house_x
    bathroom_y = bottom_y

    row_height = 0

    for bathroom in bathrooms:

        bathroom_w = float(bathroom["w"])
        bathroom_h = float(bathroom["h"])

        if bathroom_x + bathroom_w > house_x + house_width:

            bathroom_x = house_x
            bathroom_y += row_height
            row_height = 0

        add_room(
            bathroom,
            bathroom_x,
            bathroom_y,
            bathroom_w,
            bathroom_h,
        )

        bathroom_x += bathroom_w

        row_height = max(
            row_height,
            bathroom_h,
        )
    # =========================================================
    # ROW 2 — LIVING + KITCHEN
    # =========================================================

    middle_y = round(
        house_y + bathroom_max_h,
        3,
    )

    living_x = house_x

    add_room(
        living,
        living_x,
        middle_y,
        living_w,
        living_h,
    )

    if kitchen:
        kitchen_x = round(
            living_x + living_w,
            3,
        )

        add_room(
            kitchen,
            kitchen_x,
            middle_y,
            kitchen_w,
            kitchen_h,
        )

    # =========================================================
    # ROW 3 — BEDROOMS
    #
    # Exact x accumulation means neighboring bedrooms
    # share exact vertical boundaries.
    # =========================================================
    bedroom_y = round(
        middle_y + max(living_h, kitchen_h),
        3,
    )

    bedroom_x = house_x

    row_height = 0

    for bedroom in bedrooms:

        bedroom_w = float(bedroom["w"])
        bedroom_h = float(bedroom["h"])

        if bedroom_x + bedroom_w > house_x + house_width:

            bedroom_x = house_x
            bedroom_y += row_height
            row_height = 0

        add_room(
            bedroom,
            bedroom_x,
            bedroom_y,
            bedroom_w,
            bedroom_h,
        )

        bedroom_x += bedroom_w

        row_height = max(
            row_height,
            bedroom_h,
        )

    # =========================================================
    # OTHER ROOMS
    # =========================================================

    other_x = round(
        house_x + middle_width,
        3,
    )

    other_y = middle_y

    for room in others:

        room_w = float(room["w"])
        room_h = float(room["h"])

        placed = add_room(
            room,
            other_x,
            other_y,
            room_w,
            room_h,
        )

        if placed:
            other_x = round(
                other_x + room_w,
                3,
            )
    # =========================================================
    # DEBUG
    # =========================================================

    print("\n========== GENERATED LAYOUT ==========")

    for room in rooms:
        print(
            room["name"],
            "w:",
            room["w"],
            "h:",
            room["h"],
            "polygon:",
            room["polygon"],
        )

    print(
        "Generated rooms:",
        len(rooms),
        "/",
        len(requested_rooms),
    )

    print("======================================\n")

    # =========================================================
    # RETURN
    # =========================================================

    return {
        "plot": {
            "width": plot_w,
            "length": plot_l,
        },
        "rooms": rooms,
    }