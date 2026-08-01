from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional

class Plot(BaseModel):
    width: float = Field(..., gt=0)
    length: float = Field(..., gt=0)

class Room(BaseModel):
    name: str
    w: float = Field(..., gt=0)
    h: float = Field(..., gt=0)

class Adjacency(BaseModel):
    a: str
    b: str

class Requirements(BaseModel):
    style: str = "modern"
    plot: Plot
    rooms: List[Room]
    entrance_side: Optional[Literal["north", "south", "east", "west"]] = "north"
    adjacency: List[Adjacency] = []

    @field_validator("rooms")
    @classmethod
    def unique_room_names(cls, v):
        names = [r.name for r in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate room names")
        return v

    @field_validator("adjacency")
    @classmethod
    def adjacency_refs_exist(cls, v, info):
        data = info.data
        if "rooms" not in data:
            return v
        room_names = {r.name for r in data["rooms"]}
        for adj in v:
            if adj.a not in room_names or adj.b not in room_names:
                raise ValueError(f"Invalid adjacency: {adj.a} or {adj.b} not in rooms")
        return v
    