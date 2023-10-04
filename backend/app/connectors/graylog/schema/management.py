from typing import List, Optional, Dict, Union
from pydantic import BaseModel

class DeletedIndexBody(BaseModel):
    index_name: str

class DeletedIndexResponse(BaseModel):
    success: bool
    message: str

class StopInputBody(BaseModel):
    input_id: str

class StopInputResponse(BaseModel):
    success: bool
    message: str

class StartInputBody(BaseModel):
    input_id: str

class StartInputResponse(BaseModel):
    success: bool
    message: str

class StopStreamBody(BaseModel):
    stream_id: str

class StopStreamResponse(BaseModel):
    success: bool
    message: str

class StartStreamBody(BaseModel):
    stream_id: str

class StartStreamResponse(BaseModel):
    success: bool
    message: str