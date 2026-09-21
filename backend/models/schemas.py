from pydantic import BaseModel
from typing   import Optional, Dict, Any


class ShootingAnalysisResponse(BaseModel):
    success:          bool
    shot_type:        Optional[str]         = None
    condition:        Optional[str]         = None
    kicking_foot:     Optional[str]         = None
    contact_frame:    Optional[int]         = None
    technique_score:  Optional[float]       = None
    measured:         Optional[Dict[str, Any]] = None
    breakdown:        Optional[Dict[str, Any]] = None
    power_grade:      Optional[int]         = None
    power_speed_kmh:  Optional[float]       = None
    processing_time:  Optional[str]         = None
    error:            Optional[str]         = None
