from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request

from app.api.storage import DatabaseSession, download, query_keys
from app.auth import require_api_key
from app.errors import ok
from app.services import storage

router = APIRouter(prefix="/api/datasets", dependencies=[Depends(require_api_key)])
Page = Annotated[int, Query(ge=1)]
Size = Annotated[int, Query(ge=1, le=100)]
Binary = Annotated[int, Query(ge=0, le=1)]


@router.get("")
def datasets(request: Request, session: DatabaseSession, page: Page = 1, size: Size = 20,
             status: Literal["collecting", "ready", "failed", "archived"] | None = None,
             q: Annotated[str | None, Query(max_length=255)] = None):
    query_keys(request, {"page", "size", "status", "q"})
    return ok(storage.list_datasets(session, page, size, status, q))


@router.get("/outputs/{job_id}/{name}")
def download_dataset(job_id: str, name: str):
    return download("datasets", job_id, name)


@router.get("/{dataset_id}")
def dataset(dataset_id: str, session: DatabaseSession):
    storage.snapshot(session)
    return ok(storage.dataset_record(session, storage.require_dataset(session, dataset_id), detail=True))


@router.get("/{dataset_id}/commits")
def members(request: Request, dataset_id: str, session: DatabaseSession, page: Page = 1, size: Size = 20,
            with_features: Binary = 1, start_time: str | None = None, end_time: str | None = None):
    query_keys(request, {"page", "size", "with_features", "start_time", "end_time"})
    return ok(storage.dataset_members(session, dataset_id, page, size, with_features,
                                     start_time=start_time, end_time=end_time))


@router.get("/{dataset_id}/export")
def export_dataset(request: Request, dataset_id: str, session: DatabaseSession, format: str = "csv", artifact: str = "commits",
                   model_name: str | None = None, decision_threshold: Annotated[float | None, Query(ge=0, le=1)] = None,
                   start_time: str | None = None, end_time: str | None = None):
    query_keys(request, {"format", "artifact", "model_name", "decision_threshold", "start_time", "end_time"})
    return ok(storage.export_dataset(session, dataset_id, format, artifact, model_name, decision_threshold,
                                    start_time=start_time, end_time=end_time))
