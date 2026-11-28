"""请求 / 响应 Pydantic 模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class SourceRef(BaseModel):
    kind: str
    id: str


class CollectRunRequest(BaseModel):
    repo_url: str
    branch: str
    mode: str = "expert"


class CollectPrecheckRequest(BaseModel):
    repo_url: str
    branch: str
    mode: str = "expert"


class CleanRunRequest(BaseModel):
    source: SourceRef
    operations: list[dict[str, Any]] = Field(default_factory=list)


class TrainRunRequest(BaseModel):
    source: SourceRef
    algorithms: list[dict[str, Any]] = Field(default_factory=list)
    split: dict[str, Any] = Field(default_factory=lambda: {"mode": "time", "ratios": {"train": 70, "valid": 15, "test": 15}})


class TrainPrecheckRequest(BaseModel):
    dataset_id: str


class TrainSaveRequest(BaseModel):
    job_id: str
    model_names: list[str] = Field(default_factory=list)
    save_test: bool = False
    test_name: str | None = None


class PredictRunRequest(BaseModel):
    source: SourceRef
    model: dict[str, Any]
    threshold: float = 0.5


class PredictPrecheckRequest(BaseModel):
    dataset_id: str


class PredictSaveRequest(BaseModel):
    job_id: str
    name: str


class PredictSaveModelRequest(BaseModel):
    model_ref: str
    name: str | None = None


class PredictExplainRequest(BaseModel):
    job_id: str
    commit_hash: str
    technique: str = "shap"


class PredictLocalizeRequest(BaseModel):
    job_id: str
    commit_hash: str


class EvaluatePrecheckRequest(BaseModel):
    dataset_id: str


class EvaluateRunRequest(BaseModel):
    source: SourceRef
    metrics: list[str] = Field(default_factory=list)
    threshold: float = 0.5


class EvaluateSaveRequest(BaseModel):
    job_id: str
    name: str


class DatasetSaveRequest(BaseModel):
    job_id: str
    name: str


class ConfigSaveRequest(BaseModel):
    items: dict[str, Any] = Field(default_factory=dict)


class PageStateRequest(BaseModel):
    model_config = {"extra": "allow"}
