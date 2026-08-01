from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_parser import parse_text_to_json
from layout_generator import generate_layout
from mesh_builder import blueprint_to_mesh
from validator import validate_requirements
from schemas import Requirements
import os
from google.genai.errors import ClientError

@app.post("/generate")
def generate(payload: PromptIn):
    try:
        req_dict = parse_text_to_json(payload.prompt)
        ...
    except ClientError as e:
        return {
            "error": "Gemini API quota exceeded",
            "details": str(e)
        }

app = FastAPI(
    title="AI House Designer API",
    version="1.0.0"
)

API_KEY = None

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://house-designer-7ug3.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(x_api_key: str | None = Header(None)):
    if not API_KEY:
        return

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

class PromptIn(BaseModel):
    prompt: str

@app.post("/generate")
def generate(payload: PromptIn):

    req_dict = parse_text_to_json(payload.prompt)

    if "adjacency" in req_dict:
        req_dict["adjacency"] = [
            {"a": pair[0], "b": pair[1]}
            for pair in req_dict["adjacency"]
        ]

    req = Requirements(**req_dict)

    val = validate_requirements(req)

    if not val["valid"]:
        return {
            "error": "Invalid requirements",
            "details": val["errors"]
        }

    layout = generate_layout(req_dict)
    mesh = blueprint_to_mesh(layout)

    return mesh