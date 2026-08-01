"use client";

import { useState } from "react";
import HouseViewer from "@/components/HouseViewer";

type Door = {
  wall: number;
  position: number;
  width: number;
  connects_to: string;
};

type MeshData = {
  wall_height: number;
  wall_thickness: number;
  rooms: {
    name: string;
    height: number;
    polygon: [number, number][];
    doors: Door[];
  }[];
};

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [mesh, setMesh] = useState<MeshData | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
  setLoading(true);
  setError(null);
  setMesh(null);

  try {
    const API_URL =
      process.env.NEXT_PUBLIC_API_URL ||
      "https://house-designer-hroi.onrender.com";
      console.log("API_URL =", API_URL);

    const res = await fetch(`${API_URL}/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Remove this line if you disabled API key verification
        // "x-api-key": "house-designer-secret",
      },
      body: JSON.stringify({ prompt }),
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      setError(data.details?.join(" ") || data.error || "Failed to generate layout");
    } else {
      setMesh(data);
    }
  } catch (e) {
    console.error(e);
    setError("Network error");
  } finally {
    setLoading(false);
  }
}

  return (
    <div className="container">
      <h1>Text-to-Blueprint-to-3D House Designer</h1>
      <p style={{ marginBottom: 16, color: "#94a3b8" }}>
        Enter a description like: “3-bedroom modern house, open kitchen, 2 bathrooms, living room, large windows.”
      </p>

      <div className="formRow">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your house..."
        />
        <button onClick={handleGenerate} disabled={loading || !prompt.trim()}>
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>

      {error && (
        <div style={{ color: "#f87171", marginBottom: 12 }}>
          {error}
        </div>
      )}

      {mesh && (
        <div className="viewer">
          <HouseViewer mesh={mesh} />
        </div>
      )}
    </div>
  );
}