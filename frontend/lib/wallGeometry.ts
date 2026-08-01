export type Door = {
  wall: number;
  position: number;
  width: number;
  connects_to: string;
};

export type Room = {
  name: string;
  height: number;
  polygon: [number, number][];
  doors?: Door[];
};

export type DoorOpening = {
  start: number;
  end: number;
  connectsTo: string;
};

export type CanonicalWall = {
  start: [number, number];
  end: [number, number];
  height: number;
  rooms: string[];
  openings: DoorOpening[];
};

type RawWall = {
  room: Room;
  wallIndex: number;
  start: [number, number];
  end: [number, number];
  length: number;
  doors: Door[];
};

const EPS = 0.001;

/* =========================================================
   BASIC GEOMETRY
   ========================================================= */

function samePoint(
  a: [number, number],
  b: [number, number]
): boolean {
  return (
    Math.abs(a[0] - b[0]) < EPS &&
    Math.abs(a[1] - b[1]) < EPS
  );
}

function distance(
  a: [number, number],
  b: [number, number]
): number {
  return Math.hypot(
    b[0] - a[0],
    b[1] - a[1]
  );
}

function isHorizontal(wall: RawWall): boolean {
  return (
    Math.abs(
      wall.start[1] - wall.end[1]
    ) < EPS
  );
}

function isVertical(wall: RawWall): boolean {
  return (
    Math.abs(
      wall.start[0] - wall.end[0]
    ) < EPS
  );
}

function uniqueSorted(
  values: number[]
): number[] {
  const sorted = [...values].sort(
    (a, b) => a - b
  );

  return sorted.filter(
    (value, index) =>
      index === 0 ||
      Math.abs(
        value - sorted[index - 1]
      ) > EPS
  );
}

/* =========================================================
   RAW ROOM WALLS
   ========================================================= */

function collectRawWalls(
  rooms: Room[]
): RawWall[] {
  const result: RawWall[] = [];

  rooms.forEach((room) => {
    const points = room.polygon;

    if (
      !points ||
      points.length < 3
    ) {
      return;
    }

    const closed =
      points.length > 1 &&
      samePoint(
        points[0],
        points[points.length - 1]
      );

    const count = closed
      ? points.length - 1
      : points.length;

    for (
      let wallIndex = 0;
      wallIndex < count;
      wallIndex++
    ) {
      const start =
        points[wallIndex];

      const end =
        points[
          (wallIndex + 1) % count
        ];

      const length =
        distance(start, end);

      if (length <= EPS) {
        continue;
      }

      /*
       * Current backend generates
       * axis-aligned rooms.
       *
       * Ignore unsupported diagonal
       * edges rather than corrupting
       * canonical wall geometry.
       */
      const horizontal =
        Math.abs(
          start[1] - end[1]
        ) < EPS;

      const vertical =
        Math.abs(
          start[0] - end[0]
        ) < EPS;

      if (!horizontal && !vertical) {
        console.warn(
          "Ignoring non-axis-aligned wall",
          {
            room: room.name,
            wallIndex,
            start,
            end,
          }
        );

        continue;
      }

      const doors =
        (room.doors ?? []).filter(
          (door) =>
            door.wall === wallIndex
        );

      result.push({
        room,
        wallIndex,
        start,
        end,
        length,
        doors,
      });
    }
  });

  return result;
}

/* =========================================================
   CONVERT LOCAL WALL DISTANCE TO WORLD COORDINATE
   ========================================================= */

function pointAtDistance(
  wall: RawWall,
  distanceFromStart: number
): [number, number] {
  const clamped = Math.max(
    0,
    Math.min(
      distanceFromStart,
      wall.length
    )
  );

  const t =
    clamped / wall.length;

  return [
    wall.start[0] +
      (wall.end[0] -
        wall.start[0]) *
        t,

    wall.start[1] +
      (wall.end[1] -
        wall.start[1]) *
        t,
  ];
}

/* =========================================================
   OPENING MERGE
   ========================================================= */

function mergeOpenings(
  openings: DoorOpening[]
): DoorOpening[] {
  if (openings.length === 0) {
    return [];
  }

  const sorted = [...openings].sort(
    (a, b) => a.start - b.start
  );

  const merged: DoorOpening[] = [];

  for (const opening of sorted) {
    const previous =
      merged[merged.length - 1];

    if (!previous) {
      merged.push({
        ...opening,
      });

      continue;
    }

    /*
     * Same physical doorway may be
     * supplied by both adjacent rooms.
     *
     * Merge overlapping/touching ranges.
     */
    if (
      opening.start <=
      previous.end + EPS
    ) {
      previous.end = Math.max(
        previous.end,
        opening.end
      );

      /*
       * Keep connection information useful
       * for debugging.
       */
      if (
        !previous.connectsTo
          .split("|")
          .includes(
            opening.connectsTo
          )
      ) {
        previous.connectsTo +=
          `|${opening.connectsTo}`;
      }
    } else {
      merged.push({
        ...opening,
      });
    }
  }

  return merged;
}

/* =========================================================
   BUILD CANONICAL WALLS
   ========================================================= */

export function buildCanonicalWalls(
  rooms: Room[],
  debug = false
): CanonicalWall[] {
  const rawWalls =
    collectRawWalls(rooms);

  /*
   * Group walls by infinite
   * horizontal/vertical line.
   */

  const horizontalLines =
    new Map<string, RawWall[]>();

  const verticalLines =
    new Map<string, RawWall[]>();

  rawWalls.forEach((wall) => {
    if (isHorizontal(wall)) {
      const key =
        wall.start[1].toFixed(3);

      const current =
        horizontalLines.get(key) ??
        [];

      current.push(wall);

      horizontalLines.set(
        key,
        current
      );

      return;
    }

    if (isVertical(wall)) {
      const key =
        wall.start[0].toFixed(3);

      const current =
        verticalLines.get(key) ??
        [];

      current.push(wall);

      verticalLines.set(
        key,
        current
      );
    }
  });

  const result: CanonicalWall[] =
    [];

  /* =======================================================
     PROCESS ONE HORIZONTAL/VERTICAL LINE
     ======================================================= */

  function processLine(
    walls: RawWall[],
    orientation:
      | "horizontal"
      | "vertical"
  ) {
    const breakpoints: number[] =
      [];

    /*
     * Every room-wall endpoint becomes
     * a breakpoint.
     *
     * This handles:
     *
     * long wall:
     * 0 ---------------- 10
     *
     * adjacent wall:
     * 0 ------ 4
     *
     * producing:
     *
     * 0 ------ 4 -------- 10
     */

    walls.forEach((wall) => {
      if (
        orientation ===
        "horizontal"
      ) {
        breakpoints.push(
          wall.start[0],
          wall.end[0]
        );
      } else {
        breakpoints.push(
          wall.start[1],
          wall.end[1]
        );
      }
    });

    const points =
      uniqueSorted(breakpoints);

    for (
      let i = 0;
      i < points.length - 1;
      i++
    ) {
      const segmentStart =
        points[i];

      const segmentEnd =
        points[i + 1];

      const segmentLength =
        segmentEnd -
        segmentStart;

      if (
        segmentLength <= EPS
      ) {
        continue;
      }

      const midpoint =
        (segmentStart +
          segmentEnd) /
        2;

      /*
       * Find room walls that physically
       * contain this canonical segment.
       */

      const coveringWalls =
        walls.filter((wall) => {
          const a =
            orientation ===
            "horizontal"
              ? wall.start[0]
              : wall.start[1];

          const b =
            orientation ===
            "horizontal"
              ? wall.end[0]
              : wall.end[1];

          const min = Math.min(
            a,
            b
          );

          const max = Math.max(
            a,
            b
          );

          return (
            midpoint >
              min - EPS &&
            midpoint <
              max + EPS
          );
        });

      if (
        coveringWalls.length === 0
      ) {
        continue;
      }

      const reference =
        coveringWalls[0];

      const fixedCoordinate =
        orientation ===
        "horizontal"
          ? reference.start[1]
          : reference.start[0];

      const canonicalStart:
        [number, number] =
          orientation ===
          "horizontal"
            ? [
                segmentStart,
                fixedCoordinate,
              ]
            : [
                fixedCoordinate,
                segmentStart,
              ];

      const canonicalEnd:
        [number, number] =
          orientation ===
          "horizontal"
            ? [
                segmentEnd,
                fixedCoordinate,
              ]
            : [
                fixedCoordinate,
                segmentEnd,
              ];

      /*
       * Which rooms actually own this
       * physical wall section?
       */

      const roomNames = [
        ...new Set(
          coveringWalls.map(
            (wall) =>
              wall.room.name
          )
        ),
      ];

      const height = Math.max(
        ...coveringWalls.map(
          (wall) =>
            wall.room.height
        )
      );

      const candidateOpenings:
        DoorOpening[] = [];

      /*
       * IMPORTANT FIX:
       *
       * A door may cut this canonical
       * segment ONLY when:
       *
       * 1. The room owning the door
       *    covers this segment.
       *
       * 2. door.connects_to also owns
       *    this SAME segment.
       *
       * Therefore a living->kitchen
       * door cannot accidentally cut
       * some unrelated living-room
       * exterior wall.
       */

      coveringWalls.forEach(
        (wall) => {
          wall.doors.forEach(
            (door) => {
              const targetExists =
                roomNames.includes(
                  door.connects_to
                );

              if (!targetExists) {
                if (debug) {
                  console.warn(
                    "DOOR REJECTED: target room does not share canonical segment",
                    {
                      room:
                        wall.room
                          .name,

                      target:
                        door.connects_to,

                      wallIndex:
                        wall.wallIndex,

                      canonicalStart,

                      canonicalEnd,

                      rooms:
                        roomNames,
                    }
                  );
                }

                return;
              }

              /*
               * Backend convention:
               *
               * position = distance
               * from room-wall START
               * to doorway START.
               */

              const localStart =
                door.position;

              const localEnd =
                door.position +
                door.width;

              if (
                localStart <
                  -EPS ||
                localEnd >
                  wall.length +
                    EPS ||
                localEnd <=
                  localStart +
                    EPS
              ) {
                if (debug) {
                  console.warn(
                    "INVALID DOOR RANGE",
                    {
                      room:
                        wall.room
                          .name,

                      wallIndex:
                        wall.wallIndex,

                      wallLength:
                        wall.length,

                      door,
                    }
                  );
                }

                return;
              }

              /*
               * Convert local wall
               * distance to world
               * coordinates.
               *
               * This automatically
               * handles reversed edges.
               */

              const pointA =
                pointAtDistance(
                  wall,
                  localStart
                );

              const pointB =
                pointAtDistance(
                  wall,
                  localEnd
                );

              const globalStart =
                orientation ===
                "horizontal"
                  ? Math.min(
                      pointA[0],
                      pointB[0]
                    )
                  : Math.min(
                      pointA[1],
                      pointB[1]
                    );

              const globalEnd =
                orientation ===
                "horizontal"
                  ? Math.max(
                      pointA[0],
                      pointB[0]
                    )
                  : Math.max(
                      pointA[1],
                      pointB[1]
                    );

              /*
               * Intersect doorway with
               * this canonical segment.
               */

              const overlapStart =
                Math.max(
                  segmentStart,
                  globalStart
                );

              const overlapEnd =
                Math.min(
                  segmentEnd,
                  globalEnd
                );

              if (
                overlapEnd <=
                overlapStart +
                  EPS
              ) {
                return;
              }

              const openingStart =
                overlapStart -
                segmentStart;

              const openingEnd =
                overlapEnd -
                segmentStart;

              candidateOpenings.push(
                {
                  start:
                    Math.max(
                      0,
                      Math.min(
                        segmentLength,
                        openingStart
                      )
                    ),

                  end:
                    Math.max(
                      0,
                      Math.min(
                        segmentLength,
                        openingEnd
                      )
                    ),

                  connectsTo:
                    door.connects_to,
                }
              );
            }
          );
        }
      );

      const openings =
        mergeOpenings(
          candidateOpenings
        );

      result.push({
        start:
          canonicalStart,

        end:
          canonicalEnd,

        height,

        rooms:
          roomNames,

        openings,
      });

      if (debug) {
        console.log(
          "CANONICAL SEGMENT",
          {
            start:
              canonicalStart,

            end:
              canonicalEnd,

            rooms:
              roomNames,

            openings,
          }
        );
      }
    }
  }

  /* =======================================================
     PROCESS ALL LINES
     ======================================================= */

  horizontalLines.forEach(
    (walls) => {
      processLine(
        walls,
        "horizontal"
      );
    }
  );

  verticalLines.forEach(
    (walls) => {
      processLine(
        walls,
        "vertical"
      );
    }
  );

  if (debug) {
    console.table(
      result.map(
        (wall, index) => ({
          index,

          start:
            `${wall.start[0]},${wall.start[1]}`,

          end:
            `${wall.end[0]},${wall.end[1]}`,

          rooms:
            wall.rooms.join(
              " + "
            ),

          openings:
            wall.openings
              .map(
                (opening) =>
                  `${opening.start}-${opening.end} -> ${opening.connectsTo}`
              )
              .join(" | "),
        })
      )
    );
  }

  return result;
}