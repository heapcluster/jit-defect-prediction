from __future__ import annotations

import logging

from sqlalchemy import select

from app import model_registry
from app.errors import AppError
from app.models import Model, ModelArtifact
from app.services import config_store, job_store, output_store
from app.services import file_contracts as fc

logger = logging.getLogger('backend.models')
LINE_ORDER = ('expert', 'semantic', 'fused', 'e2e')


def resolve_default(session):
    configured = config_store.get_value('default_model', session)
    if configured:
        artifact = session.scalar(select(ModelArtifact).where(ModelArtifact.model_name == configured))
        if artifact is None or artifact.status != 'available':
            return configured, '配置的默认模型不可用，需重新加载或更换默认'
        return configured, None
    entry = model_registry.default_model()
    if entry is None:
        return None, '未配置默认模型且无已加载 expert 模型'
    return entry.name, '未配置默认模型，回退已加载 expert 中 version_key 最大者'


def _artifact(session, name):
    artifact = session.scalar(select(ModelArtifact).where(ModelArtifact.model_name == name))
    if artifact is None:
        raise AppError(40400, '模型工件未登记')
    return artifact


def _read_package(artifact):
    parts = artifact.weight_path.split('/')
    job_id, name = parts[-2], parts[-1]
    path = output_store.read_output('storage', job_id, name)
    raw = path.read_bytes()
    if fc.sha256(raw) != artifact.checksum_sha256:
        raise AppError(40001, '模型工件 checksum 与登记不一致')
    return raw


def status(session, line=None, model_name=None):
    if line is not None and line not in LINE_ORDER:
        raise AppError(40001, '参数非法：line')
    default, reason = resolve_default(session)
    query = select(ModelArtifact, Model).join(Model, Model.model_name == ModelArtifact.model_name)
    if line:
        query = query.where(ModelArtifact.line == line)
    if model_name:
        query = query.where(ModelArtifact.model_name == model_name)
    items = []
    for artifact, model in session.execute(query.order_by(ModelArtifact.line, ModelArtifact.model_name)).all():
        runtime = model_registry.runtime_state(artifact.model_name)
        items.append({'model_name': artifact.model_name, 'line': artifact.line, 'algo': model.algo,
                      'artifact_status': artifact.status, 'runtime_state': runtime['state'],
                      'load_error': runtime['error'], 'version_key': artifact.version_key,
                      'feature_version': artifact.feature_version,
                      'trained_at': artifact.trained_at.isoformat() + 'Z' if artifact.trained_at else None,
                      'checksum_sha256': artifact.checksum_sha256})
    return {'default_model': default, 'fallback_reason': reason, 'items': items}


def _load(session, name):
    artifact = _artifact(session, name)
    if artifact.status == 'retired':
        raise AppError(40001, '已退役工件不可加载')
    try:
        raw = _read_package(artifact)
        model_registry.load_artifact_package(name, raw, line=artifact.line)
    except AppError as error:
        model_registry._RUNTIME[name] = {'state': 'load_failed', 'error': job_store.sanitize_text(error.message)}
        logger.warning('model load failed: %s', name)
    except Exception as error:
        model_registry._RUNTIME[name] = {'state': 'loaded' if model_registry.has(name) else 'load_failed',
                                         'error': job_store.sanitize_text(str(error))}
        logger.warning('model load failed: %s', name)
    runtime = model_registry.runtime_state(name)
    return {'model_name': name, 'runtime_state': runtime['state'], 'load_error': runtime['error']}


def load(session, name):
    return _load(session, name)


def reload(session, name):
    return _load(session, name)


def unload(session, name):
    _artifact(session, name)
    default, _ = resolve_default(session)
    if name == default:
        raise AppError(40001, '默认模型不可直接卸载，请先更换默认模型')
    model_registry.unload(name)
    runtime = model_registry.runtime_state(name)
    return {'model_name': name, 'runtime_state': runtime['state'], 'load_error': runtime['error']}


def set_default(session, name):
    artifact = _artifact(session, name)
    if artifact.status != 'available':
        raise AppError(40001, '仅可用工件可设为默认模型')
    config_store.write_config(session, [{'config_key': 'default_model', 'value': name}])
    return {'default_model': name}
