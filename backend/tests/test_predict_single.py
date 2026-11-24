"""AI-generated W6 single-predict enhancement tests; not human-reviewed."""
from app.services.predict import predict_single

from tests.conftest import C1, HEADERS


def test_single_adds_contract_fields_and_keeps_explanation(client):
    data = client.post('/api/predict', json={'commit_hash': C1, 'model_name': 'fixture_v2'}, headers=HEADERS).json()['data']
    for field in ('predicted_label', 'decision_threshold', 'risk_level', 'model_version', 'feature_version', 'result_source', 'stale'):
        assert field in data
    assert data['predicted_label'] == int(data['risk_score'] >= data['decision_threshold'])
    assert data['risk_level'] in ('high', 'mid', 'low')
    assert 'explanation' not in data and 'features' in data and 'summary' in data
    assert data['result_source'] in ('stored', 'computed')


def test_single_stored_then_force_recompute(client):
    first = predict_single(C1, 'fixture_v2')
    assert first['result_source'] == 'stored'
    forced = predict_single(C1, 'fixture_v2', force_recompute=True)
    assert forced['result_source'] == 'computed'
    again = predict_single(C1, 'fixture_v2')
    assert again['result_source'] == 'stored'
    assert again['risk_score'] == forced['risk_score']
    assert again['predicted_at'] == forced['predicted_at']


def test_single_threshold_changes_label_not_score(client):
    low = predict_single(C1, 'fixture_v2', decision_threshold=0.01, force_recompute=True)
    high = predict_single(C1, 'fixture_v2', decision_threshold=0.99, force_recompute=True)
    assert low['risk_score'] == high['risk_score']
    assert low['predicted_label'] == int(low['risk_score'] >= 0.01)
    assert high['predicted_label'] == int(high['risk_score'] >= 0.99)


def test_single_rejects_extra_field_and_bad_threshold(client):
    assert client.post('/api/predict', json={'commit_hash': C1, 'wat': 1}, headers=HEADERS).status_code == 400
    assert client.post('/api/predict', json={'commit_hash': C1, 'decision_threshold': 1.5}, headers=HEADERS).status_code == 400
