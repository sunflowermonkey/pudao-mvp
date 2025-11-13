from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator


ActionType = Literal["vsl", "ramp_metering", "ramp_closure", "vms_message"]


class Scope(BaseModel):
    roadchain_id: str
    segments: List[str] = []
    ramps: List[str] = []
    vms: List[str] = []


class Action(BaseModel):
    type: ActionType
    segment_id: Optional[str] = None
    ramp_id: Optional[str] = None
    vms_id: Optional[str] = None
    value: Optional[float] = None
    veh_per_hour: Optional[float] = None
    ttl_s: Optional[float] = None
    max_duration_s: Optional[float] = None
    condition: Optional[str] = None
    text: Optional[str] = None

    @validator("segment_id", always=True)
    def vsl_needs_segment(cls, v, values):
        if values.get("type") == "vsl" and not v:
            raise ValueError("vsl action requires segment_id")
        return v

    @validator("ramp_id", always=True)
    def ramp_actions_need_ramp(cls, v, values):
        if values.get("type") in ("ramp_metering", "ramp_closure") and not v:
            raise ValueError("ramp_* action requires ramp_id")
        return v

    @validator("vms_id", always=True)
    def vms_actions_need_vms(cls, v, values):
        if values.get("type") == "vms_message" and not v:
            raise ValueError("vms_message requires vms_id")
        return v


class Guardrails(BaseModel):
    min_vsl: float
    max_vsl: float
    max_delta: float
    max_changes_per_5min: Optional[int] = 0
    max_ramp_queue: Optional[float] = None
    max_closure_s: Optional[float] = None
    always_keep_emergency_lane_free: bool = True


class Rollout(BaseModel):
    mode: Literal["immediate", "canary"]
    max_revert_time_s: Optional[float] = None


class Metadata(BaseModel):
    author: Optional[str] = None
    source: Optional[str] = None
    rationale: Optional[str] = None


class StrategyIR(BaseModel):
    strategy_id: str
    version: str
    scope: Scope
    actions: List[Action]
    guardrails: Guardrails
    rollout: Rollout
    metadata: Optional[Metadata] = Metadata()
