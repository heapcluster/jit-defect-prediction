from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.db import get_db
from app.errors import ok
from app.services import config_store

router = APIRouter(dependencies=[Depends(require_api_key)])
DatabaseSession = Annotated[Session, Depends(get_db)]


class ConfigItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config_key: StrictStr
    value: Any


class ConfigBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ConfigItem] = Field(min_length=1, max_length=23)


class ConfigValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Any


@router.get("/api/config")
def get_config(session: DatabaseSession, keys: str | None = Query(default=None)) -> dict:
    selected = sorted(set(keys.split(","))) if keys is not None else None
    return ok({"items": config_store.read_config(session, selected),
               "schema": config_store.schema_metadata(session)})


@router.put("/api/config")
def put_config(body: ConfigBatch, session: DatabaseSession) -> dict:
    return ok({"items": config_store.write_config(session, [item.model_dump() for item in body.items])})


@router.put("/api/config/{key}")
def put_config_key(key: str, body: ConfigValue, session: DatabaseSession) -> dict:
    return ok({"items": config_store.write_config(session, [{"config_key": key, "value": body.value}])})


@router.delete("/api/config/{key}")
def delete_config_key(key: str, session: DatabaseSession) -> dict:
    return ok(config_store.delete_config(session, key))
