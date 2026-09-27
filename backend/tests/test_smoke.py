"""冒烟测试：只覆盖顺利路径。

这些用例在初始快照上全绿；它们不覆盖 README「行为规格」里的边界语义，
因此通过它们并不代表规格已被满足。
"""
import io
import importlib
import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@pytest.fixture()
def client(tmp_path):
    os.environ['DATABASE_URL'] = 'sqlite:///' + (tmp_path / 'test.db').as_posix()
    os.environ['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    os.environ['SMTP_SERVER'] = ''
    os.environ['SMTP_USERNAME'] = ''
    os.environ['PHYSICS_TEAM_EMAILS'] = ''
    os.environ['OPENAI_API_KEY'] = ''

    import config
    import app as app_module
    importlib.reload(config)
    importlib.reload(app_module)

    application = app_module.create_app()
    application.config['TESTING'] = True
    with application.test_client() as test_client:
        yield test_client


def create_detector(client, name='液氙TPC-01'):
    resp = client.post('/api/detectors', json={
        'name': name,
        'module_code': 'LXe-01',
        'target_material': '液氙',
        'location': '地下实验室B厅',
        'status': 'running',
    })
    assert resp.status_code == 201
    return resp.get_json()['id']


def create_session(client, detector_id):
    resp = client.post(f'/api/detectors/{detector_id}/sessions', json={
        'run_type': '本底测量',
        'exposure_hours': 48.5,
        'energy_threshold_kev': 1.5,
        'notes': '第一轮基线采集',
    })
    assert resp.status_code == 201
    return resp.get_json()['id']


def test_health(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'healthy'


def test_detector_and_session_flow(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)

    resp = client.get('/api/detectors')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    resp = client.get(f'/api/detectors/{detector_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == '液氙TPC-01'
    assert [s['id'] for s in data['sessions']] == [session_id]


def test_spectrum_and_event_flow(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)

    resp = client.post(f'/api/detectors/sessions/{session_id}/spectra', json={
        'energy_kev': 2.5,
        'counts': 137.0,
        'fit_value': 131.2,
    })
    assert resp.status_code == 201

    resp = client.get(f'/api/detectors/sessions/{session_id}/spectra')
    assert resp.status_code == 200
    assert resp.get_json()[0]['counts'] == 137.0

    resp = client.post(f'/api/detectors/sessions/{session_id}/events', json={
        'energy_kev': 3.2,
        's1_pe': 12.0,
        's2_pe': 480.5,
    })
    assert resp.status_code == 201

    resp = client.get(f'/api/detectors/sessions/{session_id}/events')
    assert resp.status_code == 200
    assert resp.get_json()[0]['s1_pe'] == 12.0


def test_upload_recording(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)

    resp = client.post(
        f'/api/audio/upload/{session_id}',
        data={'file': (io.BytesIO(b'RIFF....WAVEfmt '), 'run_meeting_01.wav')},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 201
    assert resp.get_json()['id']

    resp = client.get('/api/audio/recordings/1')
    assert resp.status_code == 200
    assert resp.get_json()['session_id'] == session_id


def test_generate_summary_with_mock_service(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)

    resp = client.post(f'/api/audio/generate-summary/{session_id}')
    assert resp.status_code == 201
    summary_id = resp.get_json()['id']

    resp = client.get(f'/api/audio/summaries/{summary_id}')
    assert resp.status_code == 200
    assert resp.get_json()['summary_text']


def test_get_summary_not_found(client):
    resp = client.get('/api/audio/summaries/999999')
    assert resp.status_code == 404
