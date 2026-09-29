import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import (
    db, AudioRecording, Transcription, RunSession, DetectorModule, RunSummary
)
from services import speech_service, ai_service, email_service
from services.crypto_service import encrypt_payload, CryptoError
from config import Config
from validation import get_json_body, require_non_empty_string

audio_bp = Blueprint('audio', __name__, url_prefix='/api/audio')


def _existing_transcription_segments(recording):
    return [{
        'start': t.start_time,
        'end': t.end_time,
        'speaker': t.speaker,
        'speaker_role': t.speaker_role,
        'text': t.text,
        'physics_terms': t.physics_terms.split(',') if t.physics_terms else []
    } for t in recording.transcriptions]


@audio_bp.route('/upload/<int:session_id>', methods=['POST'])
def upload_audio(session_id):
    RunSession.query.get_or_404(session_id)

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    original_filename = file.filename
    if file and Config.allowed_file(original_filename):
        safe_name = secure_filename(original_filename)
        if not safe_name:
            extension = original_filename.rsplit('.', 1)[1].lower()
            safe_name = f'audio.{extension}'
        unique_filename = f"{uuid.uuid4().hex}_{safe_name}"
        upload_dir = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.abspath(os.path.join(upload_dir, unique_filename))
        if os.path.dirname(file_path) != upload_dir:
            return jsonify({'error': 'Invalid file name'}), 400
        file.save(file_path)

        recording = AudioRecording(
            session_id=session_id,
            file_path=file_path,
            file_name=original_filename,
            transcription_status='pending'
        )
        db.session.add(recording)
        db.session.commit()

        return jsonify({
            'id': recording.id,
            'message': 'Audio uploaded successfully',
            'file_name': original_filename
        }), 201

    return jsonify({'error': 'Invalid file type'}), 400


@audio_bp.route('/transcribe/<int:recording_id>', methods=['POST'])
def transcribe_audio(recording_id):
    recording = AudioRecording.query.get_or_404(recording_id)

    if recording.transcription_status == 'processing':
        return jsonify({'message': 'Transcription already in progress'}), 202

    if recording.transcription_status == 'completed' and recording.transcriptions:
        return jsonify({
            'message': 'Transcription already completed',
            'transcriptions': _existing_transcription_segments(recording)
        }), 200

    recording.transcription_status = 'processing'
    db.session.commit()

    try:
        transcription = speech_service.transcribe_audio(recording.file_path)
        diarization = speech_service.diarize_speakers(recording.file_path)
        combined = speech_service.combine_transcription_with_speakers(
            transcription, diarization
        )

        for seg in combined:
            trans = Transcription(
                recording_id=recording_id,
                speaker=seg['speaker'],
                speaker_role=seg['speaker_role'],
                start_time=seg['start'],
                end_time=seg['end'],
                text=seg['text'],
                physics_terms=','.join(seg['physics_terms']) if seg['physics_terms'] else None
            )
            db.session.add(trans)

        recording.transcription_status = 'completed'
        db.session.commit()

        return jsonify({
            'message': 'Transcription completed',
            'transcriptions': combined
        })
    except Exception as e:
        recording.transcription_status = 'failed'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@audio_bp.route('/recordings/<int:recording_id>/transcriptions', methods=['GET'])
def get_transcriptions(recording_id):
    recording = AudioRecording.query.get_or_404(recording_id)
    return jsonify([{
        'id': t.id,
        'speaker': t.speaker,
        'speaker_role': t.speaker_role,
        'start_time': t.start_time,
        'end_time': t.end_time,
        'text': t.text,
        'physics_terms': t.physics_terms.split(',') if t.physics_terms else [],
        'created_at': t.created_at.isoformat()
    } for t in recording.transcriptions])


@audio_bp.route('/recordings/<int:recording_id>', methods=['GET'])
def get_recording(recording_id):
    recording = AudioRecording.query.get_or_404(recording_id)
    return jsonify({
        'id': recording.id,
        'session_id': recording.session_id,
        'file_name': recording.file_name,
        'duration_seconds': recording.duration_seconds,
        'transcription_status': recording.transcription_status,
        'created_at': recording.created_at.isoformat()
    })


@audio_bp.route('/generate-summary/<int:session_id>', methods=['POST'])
def generate_summary(session_id):
    session = RunSession.query.get_or_404(session_id)
    detector = DetectorModule.query.get(session.detector_id)

    all_transcriptions = []
    for recording in session.recordings:
        for t in recording.transcriptions:
            all_transcriptions.append({
                'speaker': t.speaker,
                'speaker_role': t.speaker_role,
                'text': t.text,
                'physics_terms': t.physics_terms.split(',') if t.physics_terms else []
            })

    spectra = [{
        'energy_kev': b.energy_kev,
        'counts': b.counts,
        'fit_value': b.fit_value
    } for b in session.spectra]

    events = [{
        'energy_kev': e.energy_kev,
        's1_pe': e.s1_pe,
        's2_pe': e.s2_pe,
        'classification': e.classification
    } for e in session.events]

    detector_info = {
        'name': detector.name,
        'module_code': detector.module_code,
        'target_material': detector.target_material,
        'location': detector.location
    }

    try:
        summary_data = ai_service.generate_run_summary(
            all_transcriptions, spectra, events, detector_info
        )
    except Exception as e:
        return jsonify({'error': f'Summary generation failed: {e}'}), 502

    summary = RunSummary(
        session_id=session_id,
        summary_text=summary_data['summary_text'],
        anomaly_analysis=summary_data['anomaly_analysis'],
        run_plan=summary_data['run_plan'],
        calibration_notes=summary_data['calibration_notes'],
        key_terms=','.join(summary_data['key_terms']) if summary_data['key_terms'] else None
    )
    db.session.add(summary)
    db.session.commit()

    return jsonify({
        'id': summary.id,
        'message': 'Run summary generated successfully',
        'summary': summary_data
    }), 201


@audio_bp.route('/summaries/<int:summary_id>', methods=['GET'])
def get_summary(summary_id):
    summary = RunSummary.query.get_or_404(summary_id)
    return jsonify({
        'id': summary.id,
        'session_id': summary.session_id,
        'summary_text': summary.summary_text,
        'anomaly_analysis': summary.anomaly_analysis,
        'run_plan': summary.run_plan,
        'calibration_notes': summary.calibration_notes,
        'key_terms': summary.key_terms.split(',') if summary.key_terms else [],
        'sent_to_team': summary.sent_to_team,
        'sent_at': summary.sent_at.isoformat() if summary.sent_at else None,
        'created_at': summary.created_at.isoformat()
    })


@audio_bp.route('/summaries/<int:summary_id>/send-email', methods=['POST'])
def send_summary_email(summary_id):
    summary = RunSummary.query.get_or_404(summary_id)
    session = RunSession.query.get(summary.session_id)
    detector = DetectorModule.query.get(session.detector_id)

    summary_data = {
        'summary_text': summary.summary_text,
        'anomaly_analysis': summary.anomaly_analysis,
        'run_plan': summary.run_plan,
        'calibration_notes': summary.calibration_notes,
        'key_terms': summary.key_terms.split(',') if summary.key_terms else []
    }

    results = email_service.send_to_physics_team(
        detector.name, summary_data, session.session_date
    )

    sent_count = sum(1 for r in results if r.get('success'))
    if sent_count > 0:
        summary.sent_to_team = True
        summary.sent_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': 'Emails sent' if sent_count > 0 else 'No emails delivered',
        'sent_count': sent_count,
        'results': results
    })


@audio_bp.route('/summaries/<int:summary_id>/encrypt', methods=['POST'])
def encrypt_summary(summary_id):
    summary = RunSummary.query.get_or_404(summary_id)
    payload = get_json_body()
    plaintext = require_non_empty_string(payload, 'plaintext')
    token = encrypt_payload(plaintext, Config.TRANSMISSION_KEY)
    return jsonify({
        'summary_id': summary.id,
        'ciphertext': token
    })


@audio_bp.route('/sessions/<int:session_id>/full-process', methods=['POST'])
def full_process(session_id):
    session = RunSession.query.get_or_404(session_id)
    detector = DetectorModule.query.get(session.detector_id)

    all_transcriptions = []
    for recording in session.recordings:
        if recording.transcription_status != 'completed':
            recording.transcription_status = 'processing'
            db.session.commit()

            try:
                transcription = speech_service.transcribe_audio(recording.file_path)
                diarization = speech_service.diarize_speakers(recording.file_path)
                combined = speech_service.combine_transcription_with_speakers(
                    transcription, diarization
                )
            except Exception as e:
                recording.transcription_status = 'failed'
                db.session.commit()
                return jsonify({'error': f'Transcription failed: {e}'}), 500

            for seg in combined:
                trans = Transcription(
                    recording_id=recording.id,
                    speaker=seg['speaker'],
                    speaker_role=seg['speaker_role'],
                    start_time=seg['start'],
                    end_time=seg['end'],
                    text=seg['text'],
                    physics_terms=','.join(seg['physics_terms']) if seg['physics_terms'] else None
                )
                db.session.add(trans)
                all_transcriptions.append({
                    'speaker': seg['speaker'],
                    'speaker_role': seg['speaker_role'],
                    'text': seg['text'],
                    'physics_terms': seg['physics_terms']
                })

            recording.transcription_status = 'completed'
            db.session.commit()
        else:
            for t in recording.transcriptions:
                all_transcriptions.append({
                    'speaker': t.speaker,
                    'speaker_role': t.speaker_role,
                    'text': t.text,
                    'physics_terms': t.physics_terms.split(',') if t.physics_terms else []
                })

    spectra = [{
        'energy_kev': b.energy_kev,
        'counts': b.counts,
        'fit_value': b.fit_value
    } for b in session.spectra]

    events = [{
        'energy_kev': e.energy_kev,
        's1_pe': e.s1_pe,
        's2_pe': e.s2_pe,
        'classification': e.classification
    } for e in session.events]

    detector_info = {
        'name': detector.name,
        'module_code': detector.module_code,
        'target_material': detector.target_material,
        'location': detector.location
    }

    try:
        summary_data = ai_service.generate_run_summary(
            all_transcriptions, spectra, events, detector_info
        )
    except Exception as e:
        return jsonify({'error': f'Summary generation failed: {e}'}), 502

    summary = RunSummary(
        session_id=session_id,
        summary_text=summary_data['summary_text'],
        anomaly_analysis=summary_data['anomaly_analysis'],
        run_plan=summary_data['run_plan'],
        calibration_notes=summary_data['calibration_notes'],
        key_terms=','.join(summary_data['key_terms']) if summary_data['key_terms'] else None
    )
    db.session.add(summary)
    db.session.commit()

    email_results = email_service.send_to_physics_team(
        detector.name, summary_data, session.session_date
    )

    sent_count = sum(1 for r in email_results if r.get('success'))
    if sent_count > 0:
        summary.sent_to_team = True
        summary.sent_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'summary_id': summary.id,
        'summary': summary_data,
        'transcriptions': all_transcriptions,
        'sent_count': sent_count,
        'email_results': email_results,
        'message': 'Full processing completed'
    })
