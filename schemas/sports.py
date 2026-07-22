from pydantic import BaseModel


class SportCreate(BaseModel):
    name: str
    icon: str
    slug: str


class SportResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    icon: str
    slug: str