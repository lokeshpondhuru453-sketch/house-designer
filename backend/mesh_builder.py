def blueprint_to_mesh(
    layout: dict,
    wall_height: float = 3.0,
    wall_thickness: float = 0.15,
) -> dict:
    """
    Convert room polygons into mesh data with controlled
    doorway connectivity.

    Strategy:
    1. Find every pair of rooms that genuinely shares a wall.
    2. Store the best shared boundary for each adjacent pair.
    3. Build a connectivity graph.
    4. Start from the living room when available.
    5. Select only the edges needed to connect every reachable room.
    6. Generate one physical doorway for each selected connection.
    """

    EPS = 0.001
    MIN_DOOR_WIDTH = 0.8
    MAX_DOOR_WIDTH = 1.0

    rooms = []

    for room in layout.get("rooms", []):
        rooms.append(
            {
                "name": room["name"],
                "height": wall_height,
                "polygon": room["polygon"],
                "doors": [],
            }
        )

    # =========================================================
    # HELPERS
    # =========================================================

    def wall_length(p1, p2):
        return (
            (p2[0] - p1[0]) ** 2
            + (p2[1] - p1[1]) ** 2
        ) ** 0.5

    def shared_segment(a1, a2, b1, b2):
        """
        Find an overlapping section between two
        axis-aligned wall segments.

        Returns:
            (
                shared_start,
                shared_end,
                orientation
            )

        or None.
        """

        # -----------------------------------------------------
        # Vertical
        # -----------------------------------------------------

        a_vertical = (
            abs(a1[0] - a2[0]) < EPS
        )

        b_vertical = (
            abs(b1[0] - b2[0]) < EPS
        )

        if (
            a_vertical
            and b_vertical
            and abs(a1[0] - b1[0]) < EPS
        ):
            a_min = min(
                a1[1],
                a2[1],
            )

            a_max = max(
                a1[1],
                a2[1],
            )

            b_min = min(
                b1[1],
                b2[1],
            )

            b_max = max(
                b1[1],
                b2[1],
            )

            shared_start = max(
                a_min,
                b_min,
            )

            shared_end = min(
                a_max,
                b_max,
            )

            if (
                shared_end
                - shared_start
                > EPS
            ):
                return (
                    shared_start,
                    shared_end,
                    "vertical",
                )

        # -----------------------------------------------------
        # Horizontal
        # -----------------------------------------------------

        a_horizontal = (
            abs(a1[1] - a2[1]) < EPS
        )

        b_horizontal = (
            abs(b1[1] - b2[1]) < EPS
        )

        if (
            a_horizontal
            and b_horizontal
            and abs(a1[1] - b1[1]) < EPS
        ):
            a_min = min(
                a1[0],
                a2[0],
            )

            a_max = max(
                a1[0],
                a2[0],
            )

            b_min = min(
                b1[0],
                b2[0],
            )

            b_max = max(
                b1[0],
                b2[0],
            )

            shared_start = max(
                a_min,
                b_min,
            )

            shared_end = min(
                a_max,
                b_max,
            )

            if (
                shared_end
                - shared_start
                > EPS
            ):
                return (
                    shared_start,
                    shared_end,
                    "horizontal",
                )

        return None

    def local_position(
        wall_start,
        wall_end,
        global_start,
        global_end,
        orientation,
    ):
        """
        Convert world-space doorway coordinates into a
        distance measured from wall_start.

        Handles walls stored in either direction.
        """

        if orientation == "horizontal":

            # Left -> right
            if (
                wall_end[0]
                >= wall_start[0]
            ):
                return (
                    global_start
                    - wall_start[0]
                )

            # Right -> left
            return (
                wall_start[0]
                - global_end
            )

        # Bottom -> top
        if (
            wall_end[1]
            >= wall_start[1]
        ):
            return (
                global_start
                - wall_start[1]
            )

        # Top -> bottom
        return (
            wall_start[1]
            - global_end
        )

    # =========================================================
    # STEP 1
    #
    # Find all valid physical room adjacencies.
    # =========================================================

    adjacency_edges = []

    for i in range(len(rooms)):
        for j in range(
            i + 1,
            len(rooms),
        ):
            room_a = rooms[i]
            room_b = rooms[j]

            polygon_a = room_a["polygon"]
            polygon_b = room_b["polygon"]

            best_match = None

            for wall_a in range(
                len(polygon_a) - 1
            ):
                a1 = polygon_a[wall_a]
                a2 = polygon_a[wall_a + 1]

                if (
                    wall_length(a1, a2)
                    <= EPS
                ):
                    continue

                for wall_b in range(
                    len(polygon_b) - 1
                ):
                    b1 = polygon_b[wall_b]
                    b2 = polygon_b[
                        wall_b + 1
                    ]

                    if (
                        wall_length(b1, b2)
                        <= EPS
                    ):
                        continue

                    shared = shared_segment(
                        a1,
                        a2,
                        b1,
                        b2,
                    )

                    if shared is None:
                        continue

                    (
                        shared_start,
                        shared_end,
                        orientation,
                    ) = shared

                    shared_length = (
                        shared_end
                        - shared_start
                    )

                    if (
                        shared_length
                        < MIN_DOOR_WIDTH
                    ):
                        continue

                    if (
                        best_match is None
                        or shared_length
                        > best_match[
                            "shared_length"
                        ]
                    ):
                        best_match = {
                            "room_a_index": i,
                            "room_b_index": j,

                            "wall_a": wall_a,
                            "wall_b": wall_b,

                            "a1": a1,
                            "a2": a2,

                            "b1": b1,
                            "b2": b2,

                            "shared_start":
                                shared_start,

                            "shared_end":
                                shared_end,

                            "shared_length":
                                shared_length,

                            "orientation":
                                orientation,
                        }

            if best_match is not None:
                adjacency_edges.append(
                    best_match
                )

    # =========================================================
    # STEP 2
    #
    # Build graph from the physical adjacencies.
    # =========================================================

    graph = {
        index: []
        for index in range(len(rooms))
    }

    for edge_index, edge in enumerate(
        adjacency_edges
    ):
        a = edge["room_a_index"]
        b = edge["room_b_index"]

        graph[a].append(
            (b, edge_index)
        )

        graph[b].append(
            (a, edge_index)
        )

    # =========================================================
    # STEP 3
    #
    # Find living room.
    # =========================================================

    living_index = None

    for index, room in enumerate(rooms):
        if "living" in room[
            "name"
        ].lower():
            living_index = index
            break

    if (
        living_index is None
        and rooms
    ):
        living_index = 0

    # =========================================================
    # STEP 4
    #
    # Select a spanning tree.
    #
    # This means:
    #
    # 7 connected rooms -> normally 6 doorways.
    #
    # We start from the living room.
    # =========================================================

    selected_edge_indexes = []

    if living_index is not None:

        visited = {
            living_index
        }

        queue = [
            living_index
        ]

        while queue:
            current = queue.pop(0)

            candidates = []

            for (
                neighbor,
                edge_index,
            ) in graph[current]:

                if neighbor in visited:
                    continue

                edge = adjacency_edges[
                    edge_index
                ]

                # Larger shared boundaries
                # are preferred.
                candidates.append(
                    (
                        -edge[
                            "shared_length"
                        ],
                        neighbor,
                        edge_index,
                    )
                )

            candidates.sort()

            for (
                _,
                neighbor,
                edge_index,
            ) in candidates:

                if neighbor in visited:
                    continue

                visited.add(
                    neighbor
                )

                queue.append(
                    neighbor
                )

                selected_edge_indexes.append(
                    edge_index
                )

        # -----------------------------------------------------
        # Report rooms that cannot physically reach living.
        # -----------------------------------------------------

        if len(visited) != len(rooms):

            missing = [
                rooms[index]["name"]
                for index in range(
                    len(rooms)
                )
                if index not in visited
            ]

            print(
                "WARNING: These rooms cannot "
                "be connected through shared walls:",
                missing,
            )

    # =========================================================
    # STEP 5
    #
    # Generate doors ONLY for selected graph edges.
    # =========================================================

    for edge_index in selected_edge_indexes:

        edge = adjacency_edges[
            edge_index
        ]

        room_a = rooms[
            edge["room_a_index"]
        ]

        room_b = rooms[
            edge["room_b_index"]
        ]

        wall_a = edge["wall_a"]
        wall_b = edge["wall_b"]

        a1 = edge["a1"]
        a2 = edge["a2"]

        b1 = edge["b1"]
        b2 = edge["b2"]

        shared_start = edge[
            "shared_start"
        ]

        shared_end = edge[
            "shared_end"
        ]

        shared_length = edge[
            "shared_length"
        ]

        orientation = edge[
            "orientation"
        ]

        # -----------------------------------------------------
        # Door width
        # -----------------------------------------------------

        door_width = min(
            MAX_DOOR_WIDTH,
            shared_length * 0.6,
        )

        if (
            door_width
            < MIN_DOOR_WIDTH
        ):
            continue

        # -----------------------------------------------------
        # Center door inside the actual shared boundary.
        # -----------------------------------------------------

        shared_center = (
            shared_start
            + shared_end
        ) / 2

        door_global_start = (
            shared_center
            - door_width / 2
        )

        door_global_end = (
            shared_center
            + door_width / 2
        )

        # -----------------------------------------------------
        # Convert to each polygon wall's local coordinates.
        # -----------------------------------------------------

        position_a = local_position(
            a1,
            a2,
            door_global_start,
            door_global_end,
            orientation,
        )

        position_b = local_position(
            b1,
            b2,
            door_global_start,
            door_global_end,
            orientation,
        )

        length_a = wall_length(
            a1,
            a2,
        )

        length_b = wall_length(
            b1,
            b2,
        )

        position_a = max(
            0.0,
            min(
                position_a,
                length_a
                - door_width,
            ),
        )

        position_b = max(
            0.0,
            min(
                position_b,
                length_b
                - door_width,
            ),
        )

        # -----------------------------------------------------
        # Store the same physical doorway on both rooms.
        # -----------------------------------------------------

        room_a["doors"].append(
            {
                "wall": wall_a,

                "position": round(
                    position_a,
                    6,
                ),

                "width": round(
                    door_width,
                    6,
                ),

                "connects_to":
                    room_b["name"],
            }
        )

        room_b["doors"].append(
            {
                "wall": wall_b,

                "position": round(
                    position_b,
                    6,
                ),

                "width": round(
                    door_width,
                    6,
                ),

                "connects_to":
                    room_a["name"],
            }
        )

        print(
            "SELECTED DOOR:",
            room_a["name"],
            "<->",
            room_b["name"],
            "| walls:",
            wall_a,
            wall_b,
            "| position:",
            round(
                position_a,
                3,
            ),
            round(
                position_b,
                3,
            ),
            "| width:",
            round(
                door_width,
                3,
            ),
        )

    # =========================================================
    # DEBUG
    # =========================================================

    print(
        "\n========== ADJACENCY =========="
    )

    for edge in adjacency_edges:
        print(
            rooms[
                edge[
                    "room_a_index"
                ]
            ]["name"],
            "<->",
            rooms[
                edge[
                    "room_b_index"
                ]
            ]["name"],
            "| shared:",
            round(
                edge[
                    "shared_length"
                ],
                3,
            ),
        )

    print(
        "================================\n"
    )

    print(
        "========== GENERATED DOORS =========="
    )

    total_connections = 0

    for room in rooms:
        print(
            room["name"],
            "doors:",
            room["doors"],
        )

        total_connections += len(
            room["doors"]
        )

    # Every physical doorway exists in
    # both rooms, so divide by two.
    print(
        "Physical doorways:",
        total_connections // 2,
    )

    print(
        "=====================================\n"
    )

    # =========================================================
    # RETURN
    # =========================================================

    return {
        "wall_height":
            wall_height,

        "wall_thickness":
            wall_thickness,

        "rooms":
            rooms,
    }