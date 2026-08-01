from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")
import os
import json
from google import genai

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

client = genai.Client(api_key=api_key)

PROMPT = """
You are an AI architect.

Convert the user's house description into JSON.

Return ONLY valid JSON.

Format:
{
  "style": "modern",
  "plot": {
    "width": 20,
    "length": 30
  },
  "rooms": [
    {"name":"living_room","w":6,"h":5},
    {"name":"kitchen","w":4,"h":4},
    {"name":"bedroom_1","w":4,"h":4},
    {"name":"bathroom_1","w":3,"h":3}
  ],
  "entrance_side":"north",
  "adjacency":[]
}
"""

def parse_text_to_json(text: str) -> dict:
    response = client.models.generate_content(
      model="gemini-2.5-flash-pro",
        contents=f"{PROMPT}\n\nUser request:\n{text}"
    )

    content = response.text.strip()

    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    return json.loads(content)