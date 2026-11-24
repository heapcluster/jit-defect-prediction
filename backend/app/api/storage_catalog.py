from fastapi import APIRouter, Depends

from app.auth import require_api_key
from app.errors import ok
from app.models import Base

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/api/storage/tables")
def table_catalog() -> dict:
    items = []
    for name, table in sorted(Base.metadata.tables.items()):
        filters = ["limit"]
        if name in ("commit", "commit_feature", "prediction", "dataset", "dataset_commit"):
            filters.append("dataset_id")
        if "model_name" in table.columns:
            filters.append("model_name")
        if name in ("commit", "commit_feature", "prediction", "dataset_commit") or any(
            column in table.columns for column in ("trained_at", "generated_at", "created_at", "updated_at")
        ):
            filters.extend(("start_time", "end_time"))
        items.append({"name": name, "columns": list(table.columns.keys()), "filters": filters})
    return ok({"items": items})
