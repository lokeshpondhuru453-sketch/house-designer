"use client";

import { Canvas } from "@react-three/fiber";
import { Grid, OrbitControls, Text } from "@react-three/drei";
import type { ReactNode } from "react";

import {
  buildCanonicalWalls,
  type CanonicalWall,
  type DoorOpening,
  type Room,
} from "../lib/wallGeometry";

type MeshData = {
  wall_height: number;
  wall_thickness: number;
  rooms: Room[];
};

const EPS = 0.001;
const DEFAULT_DOOR_HEIGHT = 2.1;

/* =========================================================
   ROOM LABEL
   ========================================================= */

function RoomLabel({ room }: { room: Room }) {
  const points = room.polygon;

  if (!points || points.length < 3) {
    return null;
  }

  const closed =
    points.length > 1 &&
    Math.abs(
      points[0][0] - points[points.length - 1][0]
    ) < EPS &&
    Math.abs(
      points[0][1] - points[points.length - 1][1]
    ) < EPS;

  const count = closed
    ? points.length - 1
    : points.length;

  if (count <= 0) {
    return null;
  }

  let x = 0;
  let z = 0;

  for (let i = 0; i < count; i++) {
    x += points[i][0];
    z += points[i][1];
  }

  x /= count;
  z /= count;

  const label = room.name
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );

  return (
    <Text
      position={[x, 0.05, z]}
      rotation={[-Math.PI / 2, 0, 0]}
      fontSize={0.45}
      anchorX="center"
      anchorY="middle"
      color="white"
      outlineWidth={0.02}
      outlineColor="black"
    >
      {label}
    </Text>
  );
}

/* =========================================================
   WALL MESH PIECE

   Creates one rectangular section of a wall.

   startDistance/endDistance = position along wall
   bottom/top = vertical position
   ========================================================= */

function WallPiece({
  wall,
  thickness,
  startDistance,
  endDistance,
  bottom,
  top,
}: {
  wall: CanonicalWall;
  thickness: number;
  startDistance: number;
  endDistance: number;
  bottom: number;
  top: number;
}) {
  const [x1, z1] = wall.start;
  const [x2, z2] = wall.end;

  const dx = x2 - x1;
  const dz = z2 - z1;

  const wallLength = Math.hypot(dx, dz);

  if (wallLength <= EPS) {
    return null;
  }

  const safeStart = Math.max(
    0,
    Math.min(wallLength, startDistance)
  );

  const safeEnd = Math.max(
    0,
    Math.min(wallLength, endDistance)
  );

  const pieceLength =
    safeEnd - safeStart;

  const pieceHeight =
    top - bottom;

  if (
    pieceLength <= EPS ||
    pieceHeight <= EPS
  ) {
    return null;
  }

  const centerDistance =
    (safeStart + safeEnd) / 2;

  const centerX =
    x1 +
    (dx / wallLength) *
      centerDistance;

  const centerZ =
    z1 +
    (dz / wallLength) *
      centerDistance;

  const centerY =
    bottom + pieceHeight / 2;

  const angle =
    Math.atan2(dz, dx);

  return (
    <mesh
  position={[centerX, centerY, centerZ]}
  rotation={[0, -angle, 0]}
>
      <boxGeometry
        args={[
          pieceLength,
          pieceHeight,
          thickness,
        ]}
      />

      <meshStandardMaterial color="white" />
    </mesh>
  );
}

/* =========================================================
   MERGE DOOR OPENINGS

   Prevent duplicated doors from producing overlapping
   or strange wall pieces.
   ========================================================= */

function mergeOpenings(
  openings: DoorOpening[],
  wallLength: number
): DoorOpening[] {
  const valid = openings
    .map((opening) => {
      const start = Math.max(
        0,
        Math.min(
          wallLength,
          opening.start
        )
      );

      const end = Math.max(
        0,
        Math.min(
          wallLength,
          opening.end
        )
      );

      return {
        start,
        end,
        connectsTo:
          opening.connectsTo,
      };
    })
    .filter(
      (opening) =>
        opening.end >
        opening.start + EPS
    )
    .sort(
      (a, b) =>
        a.start - b.start
    );

  const merged: DoorOpening[] = [];

  for (const opening of valid) {
    const previous =
      merged[merged.length - 1];

    if (
      previous &&
      opening.start <=
        previous.end + EPS
    ) {
      previous.end =
        Math.max(
          previous.end,
          opening.end
        );

      continue;
    }

    merged.push({
      ...opening,
    });
  }

  return merged;
}

/* =========================================================
   CANONICAL WALL

   Normal wall:

       █████████████████

   Door wall:

       █████████████████
       █████ HEADER ████
       ███          ████
       ███   DOOR   ████
       ███          ████
   ========================================================= */

function CanonicalWall3D({
  wall,
  thickness,
}: {
  wall: CanonicalWall;
  thickness: number;
}) {
  const [x1, z1] = wall.start;
  const [x2, z2] = wall.end;

  const wallLength =
    Math.hypot(
      x2 - x1,
      z2 - z1
    );

  if (wallLength <= EPS) {
    return null;
  }

  const openings =
    mergeOpenings(
      wall.openings ?? [],
      wallLength
    );

  /* -----------------------------------------
     NO DOORS
     ----------------------------------------- */

  if (openings.length === 0) {
    return (
      <WallPiece
        wall={wall}
        thickness={thickness}
        startDistance={0}
        endDistance={wallLength}
        bottom={0}
        top={wall.height}
      />
    );
  }

  const pieces: ReactNode[] = [];

  let cursor = 0;

  const doorHeight =
    Math.min(
      DEFAULT_DOOR_HEIGHT,
      wall.height
    );

  openings.forEach(
    (opening, index) => {

      /* =====================================
         WALL BEFORE DOOR
         ===================================== */

      if (
        opening.start >
        cursor + EPS
      ) {
        pieces.push(
          <WallPiece
            key={`left-${index}`}
            wall={wall}
            thickness={thickness}
            startDistance={cursor}
            endDistance={
              opening.start
            }
            bottom={0}
            top={wall.height}
          />
        );
      }

      /* =====================================
         HEADER ABOVE DOOR

         This is the critical fix.

         Instead of deleting the whole wall
         height, only remove 0 -> 2.1m.
         ===================================== */

      if (
        wall.height >
        doorHeight + EPS
      ) {
        pieces.push(
          <WallPiece
            key={`header-${index}`}
            wall={wall}
            thickness={thickness}
            startDistance={
              opening.start
            }
            endDistance={
              opening.end
            }
            bottom={doorHeight}
            top={wall.height}
          />
        );
      }

      cursor =
        Math.max(
          cursor,
          opening.end
        );
    }
  );

  /* -----------------------------------------
     WALL AFTER LAST DOOR
     ----------------------------------------- */

  if (
    cursor <
    wallLength - EPS
  ) {
    pieces.push(
      <WallPiece
        key="right-last"
        wall={wall}
        thickness={thickness}
        startDistance={cursor}
        endDistance={wallLength}
        bottom={0}
        top={wall.height}
      />
    );
  }

  return <>{pieces}</>;
}

/* =========================================================
   HOUSE
   ========================================================= */

function Floor() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[60, 60]} />
      <meshStandardMaterial color="#f5f5f5" />
    </mesh>
  );
}
function getHouseCenter(rooms: Room[]) {
  let minX = Infinity;
  let minZ = Infinity;
  let maxX = -Infinity;
  let maxZ = -Infinity;

  rooms.forEach((room) => {
    room.polygon.forEach(([x, z]) => {
      minX = Math.min(minX, x);
      minZ = Math.min(minZ, z);

      maxX = Math.max(maxX, x);
      maxZ = Math.max(maxZ, z);
    });
  });

  return {
    centerX: (minX + maxX) / 2,
    centerZ: (minZ + maxZ) / 2,
  };
}
function House3D({
  rooms,
  thickness,
}: {
  rooms: Room[];
  thickness: number;
}) {
  const canonicalWalls = buildCanonicalWalls(
    rooms,
    false
  );
  const { centerX, centerZ } = getHouseCenter(rooms);

  return (
    <group position={[-centerX, 0, -centerZ]}>
      {canonicalWalls.map((wall, index) => (
        <CanonicalWall3D
          key={`wall-${index}`}
          wall={wall}
          thickness={thickness}
        />
      ))}

      {rooms.map((room, index) => (
        <RoomLabel
          key={`label-${room.name}-${index}`}
          room={room}
        />
      ))}
    </group>
  );
}

/* =========================================================
   VIEWER
   ========================================================= */

export default function HouseViewer({
  mesh,
}: {
  mesh: MeshData;
}) {
  return (
  <Canvas
  camera={{
    position: [0,20,20],
    fov: 45,
  }}
>
      {/* LIGHTING */}

<ambientLight intensity={0.9} />

<directionalLight
  position={[10, 20, 10]}
  intensity={0.8}
/>

      {/* GRID */}

      {/* FLOOR */}

<Floor />

{/* GRID */}

<Grid
    args={[50,50]}
    cellSize={1}
    sectionSize={5}
    fadeDistance={100}
/>

{/* HOUSE */}

<House3D
  rooms={mesh.rooms}
  thickness={mesh.wall_thickness || 0.15}
/>

      {/* CAMERA */}

      <OrbitControls
  makeDefault
  target={[0, 0, 0]}
  enableDamping
/>
    </Canvas>
  );
}