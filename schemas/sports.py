from pydantic import BaseModel

class SportCreate(BaseModel):
    name:str
    icon:str
    slug:str

class SportResponse(BaseModel):
    id:int
    name:str
    icon:str
    slug:str
