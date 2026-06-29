from pydantic import BaseModel, Field
from typing import List

class Overview(BaseModel):
    dau: int = Field(..., description="DAU总计")
    uv: int = Field(..., description="UV总计")
    pv: int = Field(..., description="PV总计")
    avg_duration: float = Field(..., description="平均停留时长(秒)")

class PVRankItem(BaseModel):
    domain: str
    page_name: str
    uv: int
    pv: int

class UserLayerItem(BaseModel):
    domain: str
    layer: str
    user_count: int

class ReportDataContract(BaseModel):
    overview: Overview
    pv_ranks: List[PVRankItem]
    user_layers: List[UserLayerItem]