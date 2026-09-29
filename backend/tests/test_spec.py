"""行为规格测试：逐条盯住 README「行为规格」的验收点。

这些用例在未修复的实现上应当失败，修复后通过。
"""
import base64
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
    application.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    with application.test_client() as test_client:
        yield test_client


def create_detector(client, name='液氙TPC-01'):
    resp = client.post('/api/detectors', json={'name': name})
    assert resp.status_code == 201
    return resp.get_json()['id']


def create_session(client, detector_id):
    resp = client.post(f'/api/detectors/{detector_id}/sessions', json={
        'run_type': '本底测量',
        'exposure_hours': 48.5,
    })
    assert resp.status_code == 201
    return resp.get_json()['id']


def upload_recording(client, session_id, filename='run_meeting_01.wav'):
    resp = client.post(
        f'/api/audio/upload/{session_id}',
        data={'file': (io.BytesIO(b'RIFF....WAVEfmt '), filename)},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 201
    return resp.get_json()['id']


def create_summary(client, session_id):
    resp = client.post(f'/api/audio/generate-summary/{session_id}')
    assert resp.status_code == 201
    return resp.get_json()['id']


# ---------- A. 输入校验与错误响应 ----------

def test_create_detector_validation(client):
    assert client.post('/api/detectors').status_code == 400
    resp = client.post('/api/detectors', data='not-json',
                       content_type='application/json')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()
    assert client.post('/api/detectors', json={}).status_code == 400
    assert client.post('/api/detectors', json={'name': ''}).status_code == 400
    assert client.post('/api/detectors', json={'name': '  '}).status_code == 400
    assert client.post('/api/detectors', json={'name': 123}).status_code == 400


def test_create_session_validation(client):
    detector_id = create_detector(client)
    url = f'/api/detectors/{detector_id}/sessions'
    assert client.post(url).status_code == 400
    assert client.post(url, json={}).status_code == 400
    assert client.post(url, json={'run_type': ''}).status_code == 400
    assert client.post(url, json={'run_type': '本底测量',
                                  'exposure_hours': 'abc'}).status_code == 400
    assert client.post(url, json={'run_type': '本底测量',
                                  'exposure_hours': -1}).status_code == 400
    assert client.post(url, json={'run_type': '本底测量',
                                  'energy_threshold_kev': -0.5}).status_code == 400


def test_spectrum_validation(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    url = f'/api/detectors/sessions/{session_id}/spectra'
    assert client.post(url).status_code == 400
    assert client.post(url, json={'energy_kev': 2.5}).status_code == 400
    assert client.post(url, json={'counts': 10}).status_code == 400
    assert client.post(url, json={'energy_kev': 'abc',
                                  'counts': 10}).status_code == 400
    assert client.post(url, json={'energy_kev': -1,
                                  'counts': 10}).status_code == 400
    assert client.post(url, json={'energy_kev': 2.5,
                                  'counts': -3}).status_code == 400
    assert client.post(url, json={'energy_kev': 2.5, 'counts': 10,
                                  'fit_value': 'abc'}).status_code == 400
    # energy_kev 为 0 合法
    resp = client.post(url, json={'energy_kev': 0, 'counts': 5})
    assert resp.status_code == 201


def test_event_validation(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    url = f'/api/detectors/sessions/{session_id}/events'
    assert client.post(url).status_code == 400
    assert client.post(url, json={}).status_code == 400
    assert client.post(url, json={'energy_kev': -0.1}).status_code == 400
    assert client.post(url, json={'energy_kev': 3.2,
                                  's1_pe': -5}).status_code == 400
    assert client.post(url, json={'energy_kev': 3.2,
                                  's2_pe': 'abc'}).status_code == 400
    assert client.post(url, json={'energy_kev': 0}).status_code == 201


def test_not_found_returns_json_404(client):
    resp = client.get('/api/detectors/999999')
    assert resp.status_code == 404
    assert 'error' in resp.get_json()
    assert client.get('/api/detectors/sessions/999999').status_code == 404
    assert client.get('/api/audio/recordings/999999').status_code == 404


# ---------- B. 探测器与运行会话 ----------

def test_sessions_has_summary_flag(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    upload_recording(client, session_id)

    resp = client.get(f'/api/detectors/{detector_id}/sessions')
    assert resp.status_code == 200
    entry = resp.get_json()[0]
    assert entry['has_recording'] is True
    assert entry['has_summary'] is False

    create_summary(client, session_id)
    resp = client.get(f'/api/detectors/{detector_id}/sessions')
    assert resp.status_code == 200
    assert resp.get_json()[0]['has_summary'] is True


def test_session_detail_route(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    resp = client.get(f'/api/detectors/sessions/{session_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    for field in ('id', 'detector_id', 'run_type', 'exposure_hours',
                  'energy_threshold_kev', 'notes', 'session_date'):
        assert field in data
    assert data['detector_id'] == detector_id
    assert data['run_type'] == '本底测量'


def test_detectors_list_includes_sessions(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    resp = client.get('/api/detectors')
    assert resp.status_code == 200
    detector = resp.get_json()[0]
    assert [s['id'] for s in detector['sessions']] == [session_id]

    detail = client.get(f'/api/detectors/{detector_id}').get_json()
    assert detector['sessions'] == detail['sessions']


# ---------- C. 录音上传与转写 ----------

def test_upload_preserves_original_filename(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    resp = client.post(
        f'/api/audio/upload/{session_id}',
        data={'file': (io.BytesIO(b'RIFF....WAVEfmt '), '术前讨论.wav')},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 201
    recording_id = resp.get_json()['id']
    assert resp.get_json()['file_name'] == '术前讨论.wav'

    resp = client.get(f'/api/audio/recordings/{recording_id}')
    assert resp.get_json()['file_name'] == '术前讨论.wav'


def test_upload_path_traversal_contained(client, tmp_path):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    resp = client.post(
        f'/api/audio/upload/{session_id}',
        data={'file': (io.BytesIO(b'evil'), '../../etc/passwd.wav')},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 201
    upload_dir = (tmp_path / 'uploads').resolve()
    saved = list(upload_dir.iterdir())
    assert len(saved) == 1
    assert saved[0].resolve().parent == upload_dir
    assert not (tmp_path / 'etc').exists()


def test_upload_rejects_bad_extension_and_missing_file(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    resp = client.post(
        f'/api/audio/upload/{session_id}',
        data={'file': (io.BytesIO(b'x'), 'notes.txt')},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 400
    assert client.post(f'/api/audio/upload/{session_id}').status_code == 400


def test_transcribe_is_idempotent(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    recording_id = upload_recording(client, session_id)

    assert client.post(f'/api/audio/transcribe/{recording_id}').status_code == 200
    first = client.get(
        f'/api/audio/recordings/{recording_id}/transcriptions').get_json()
    assert len(first) > 0

    resp = client.post(f'/api/audio/transcribe/{recording_id}')
    assert resp.status_code in (200, 202)
    second = client.get(
        f'/api/audio/recordings/{recording_id}/transcriptions').get_json()
    assert len(second) == len(first)


# ---------- D. 外部服务失败不得伪装成功 ----------

def test_transcribe_real_failure_marked_failed(client, monkeypatch):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    recording_id = upload_recording(client, session_id)

    from services import speech_service

    class FailingModel:
        def transcribe(self, *args, **kwargs):
            raise RuntimeError('model inference exploded')

    monkeypatch.setattr(speech_service, 'whisper_model', FailingModel())
    resp = client.post(f'/api/audio/transcribe/{recording_id}')
    assert resp.status_code >= 500
    assert 'error' in resp.get_json()

    recording = client.get(f'/api/audio/recordings/{recording_id}').get_json()
    assert recording['transcription_status'] == 'failed'
    transcriptions = client.get(
        f'/api/audio/recordings/{recording_id}/transcriptions').get_json()
    assert transcriptions == []


def test_summary_real_failure_not_persisted(client, monkeypatch):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)

    from services import ai_service

    class FailingCompletions:
        def create(self, *args, **kwargs):
            raise RuntimeError('429 rate limit')

    class FailingClient:
        chat = type('Chat', (), {'completions': FailingCompletions()})()

    monkeypatch.setattr(ai_service, 'client', FailingClient())
    resp = client.post(f'/api/audio/generate-summary/{session_id}')
    assert resp.status_code >= 500
    assert 'error' in resp.get_json()

    sessions = client.get(f'/api/detectors/{detector_id}/sessions').get_json()
    assert sessions[0]['has_summary'] is False


# ---------- E. 纪要邮件与加密传输 ----------

def test_send_email_no_recipients_not_marked_sent(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    summary_id = create_summary(client, session_id)

    resp = client.post(f'/api/audio/summaries/{summary_id}/send-email')
    assert resp.status_code == 200
    assert resp.get_json()['sent_count'] == 0

    summary = client.get(f'/api/audio/summaries/{summary_id}').get_json()
    assert summary['sent_to_team'] is False
    assert summary['sent_at'] is None


def test_send_email_mock_delivery_marks_sent(client, monkeypatch):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    summary_id = create_summary(client, session_id)

    email_module = sys.modules['services.email_service']
    monkeypatch.setattr(email_module.Config, 'PHYSICS_TEAM_EMAILS',
                        ['phys1@lab.cn', 'phys2@lab.cn'])

    resp = client.post(f'/api/audio/summaries/{summary_id}/send-email')
    assert resp.status_code == 200
    assert resp.get_json()['sent_count'] == 2

    summary = client.get(f'/api/audio/summaries/{summary_id}').get_json()
    assert summary['sent_to_team'] is True
    assert summary['sent_at'] is not None


def test_encrypt_endpoint_roundtrip_and_validation(client):
    detector_id = create_detector(client)
    session_id = create_session(client, detector_id)
    summary_id = create_summary(client, session_id)

    assert client.post(
        f'/api/audio/summaries/{summary_id}/encrypt').status_code == 400
    assert client.post(
        f'/api/audio/summaries/{summary_id}/encrypt', json={}).status_code == 400

    resp = client.post(f'/api/audio/summaries/{summary_id}/encrypt',
                       json={'plaintext': '本底计数 137，疑似信号 2 例'})
    assert resp.status_code == 200
    token = resp.get_json()['ciphertext']

    from services.crypto_service import decrypt_payload
    from config import Config
    assert decrypt_payload(token, Config.TRANSMISSION_KEY) == '本底计数 137，疑似信号 2 例'


def test_crypto_tamper_and_wrong_key_detected():
    from services.crypto_service import (
        encrypt_payload, decrypt_payload, CryptoError,
    )

    key = 'dark-matter-minutes-key'
    token = encrypt_payload('机密纪要', key)
    assert decrypt_payload(token, key) == '机密纪要'

    with pytest.raises(CryptoError):
        decrypt_payload(token, 'wrong-key')

    blob = bytearray(base64.b64decode(token))
    # 篡改完整性标签
    bad_tag = bytearray(blob)
    bad_tag[-1] ^= 0x01
    with pytest.raises(CryptoError):
        decrypt_payload(base64.b64encode(bytes(bad_tag)).decode(), key)
    # 篡改密文正文
    bad_body = bytearray(blob)
    bad_body[20] ^= 0x01
    with pytest.raises(CryptoError):
        decrypt_payload(base64.b64encode(bytes(bad_body)).decode(), key)
