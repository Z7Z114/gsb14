from flask import Blueprint, request, jsonify
from models import (
    db, DetectorModule, RunSession, BackgroundSpectrum, SignalEvent, RunSummary
)
from validation import (
    get_json_body, require_non_empty_string, require_number, optional_number
)

detector_bp = Blueprint('detectors', __name__, url_prefix='/api/detectors')


def _session_brief(session):
    return {
        'id': session.id,
        'session_date': session.session_date.isoformat(),
        'run_type': session.run_type,
        'exposure_hours': session.exposure_hours,
        'energy_threshold_kev': session.energy_threshold_kev
    }


@detector_bp.route('', methods=['GET'])
def get_detectors():
    detectors = DetectorModule.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'module_code': d.module_code,
        'target_material': d.target_material,
        'location': d.location,
        'status': d.status,
        'created_at': d.created_at.isoformat(),
        'sessions': [_session_brief(s) for s in d.sessions]
    } for d in detectors])


@detector_bp.route('', methods=['POST'])
def create_detector():
    data = get_json_body()
    detector = DetectorModule(
        name=require_non_empty_string(data, 'name'),
        module_code=data.get('module_code'),
        target_material=data.get('target_material'),
        location=data.get('location'),
        status=data.get('status')
    )
    db.session.add(detector)
    db.session.commit()
    return jsonify({'id': detector.id, 'message': 'Detector registered successfully'}), 201


@detector_bp.route('/<int:detector_id>', methods=['GET'])
def get_detector(detector_id):
    detector = DetectorModule.query.get_or_404(detector_id)
    return jsonify({
        'id': detector.id,
        'name': detector.name,
        'module_code': detector.module_code,
        'target_material': detector.target_material,
        'location': detector.location,
        'status': detector.status,
        'created_at': detector.created_at.isoformat(),
        'sessions': [_session_brief(s) for s in detector.sessions]
    })


@detector_bp.route('/<int:detector_id>/sessions', methods=['GET'])
def get_detector_sessions(detector_id):
    detector = DetectorModule.query.get_or_404(detector_id)
    session_ids = [s.id for s in detector.sessions]
    if session_ids:
        summarized_ids = {
            row.session_id for row in RunSummary.query.filter(
                RunSummary.session_id.in_(session_ids)
            ).all()
        }
    else:
        summarized_ids = set()
    return jsonify([{
        'id': s.id,
        'session_date': s.session_date.isoformat(),
        'run_type': s.run_type,
        'exposure_hours': s.exposure_hours,
        'energy_threshold_kev': s.energy_threshold_kev,
        'notes': s.notes,
        'has_recording': len(s.recordings) > 0,
        'has_summary': s.id in summarized_ids
    } for s in detector.sessions])


@detector_bp.route('/<int:detector_id>/sessions', methods=['POST'])
def create_session(detector_id):
    detector = DetectorModule.query.get_or_404(detector_id)
    data = get_json_body()
    session = RunSession(
        detector_id=detector_id,
        run_type=require_non_empty_string(data, 'run_type'),
        exposure_hours=optional_number(data, 'exposure_hours'),
        energy_threshold_kev=optional_number(data, 'energy_threshold_kev', 1.0),
        notes=data.get('notes')
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({'id': session.id, 'message': 'Run session created successfully'}), 201


@detector_bp.route('/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    session = RunSession.query.get_or_404(session_id)
    return jsonify({
        'id': session.id,
        'detector_id': session.detector_id,
        'run_type': session.run_type,
        'exposure_hours': session.exposure_hours,
        'energy_threshold_kev': session.energy_threshold_kev,
        'notes': session.notes,
        'session_date': session.session_date.isoformat()
    })


@detector_bp.route('/sessions/<int:session_id>/spectra', methods=['GET'])
def get_session_spectra(session_id):
    session = RunSession.query.get_or_404(session_id)
    return jsonify([{
        'id': b.id,
        'energy_kev': b.energy_kev,
        'counts': b.counts,
        'fit_value': b.fit_value
    } for b in session.spectra])


@detector_bp.route('/sessions/<int:session_id>/spectra', methods=['POST'])
def add_spectrum_bin(session_id):
    RunSession.query.get_or_404(session_id)
    data = get_json_body()
    bin_row = BackgroundSpectrum(
        session_id=session_id,
        energy_kev=require_number(data, 'energy_kev'),
        counts=require_number(data, 'counts'),
        fit_value=optional_number(data, 'fit_value')
    )
    db.session.add(bin_row)
    db.session.commit()
    return jsonify({'id': bin_row.id, 'message': 'Spectrum bin added successfully'}), 201


@detector_bp.route('/sessions/<int:session_id>/events', methods=['GET'])
def get_session_events(session_id):
    session = RunSession.query.get_or_404(session_id)
    return jsonify([{
        'id': e.id,
        'event_time': e.event_time.isoformat(),
        'energy_kev': e.energy_kev,
        's1_pe': e.s1_pe,
        's2_pe': e.s2_pe,
        'classification': e.classification,
        'note': e.note
    } for e in session.events])


@detector_bp.route('/sessions/<int:session_id>/events', methods=['POST'])
def add_signal_event(session_id):
    RunSession.query.get_or_404(session_id)
    data = get_json_body()
    event = SignalEvent(
        session_id=session_id,
        energy_kev=require_number(data, 'energy_kev'),
        s1_pe=optional_number(data, 's1_pe'),
        s2_pe=optional_number(data, 's2_pe'),
        classification=data.get('classification', 'unclassified'),
        note=data.get('note')
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'id': event.id, 'message': 'Signal event recorded successfully'}), 201
