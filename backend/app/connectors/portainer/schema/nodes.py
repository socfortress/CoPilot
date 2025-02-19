from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class Version(BaseModel):
    Index: int

class NodeSpec(BaseModel):
    Labels: dict
    Role: str
    Availability: str

class Platform(BaseModel):
    Architecture: str
    OS: str

class Resources(BaseModel):
    NanoCPUs: int
    MemoryBytes: int

class Plugin(BaseModel):
    Type: str
    Name: str

class TLSInfo(BaseModel):
    TrustRoot: Optional[str] = None
    CertIssuerSubject: Optional[str] = None
    CertIssuerPublicKey: Optional[str] = None

class Engine(BaseModel):
    EngineVersion: str
    Plugins: List[Plugin]
    TLSInfo: Optional[TLSInfo] = None

class Description(BaseModel):
    Hostname: str
    Platform: Platform
    Resources: Resources
    Engine: Engine

class ManagerStatusResults(BaseModel):
    Leader: bool
    Reachability: str
    Addr: str

class Status(BaseModel):
    State: str
    Addr: str

class Node(BaseModel):
    ID: str
    Version: Version
    CreatedAt: datetime
    UpdatedAt: datetime
    Spec: NodeSpec
    Description: Description
    Status: Status
    ManagerStatus: Optional[ManagerStatusResults] = None

class NodesResponse(BaseModel):
    nodes: List[Node]
    success: bool
    message: str

