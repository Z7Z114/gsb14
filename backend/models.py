from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class DetectorModule(db.Model):
    """地下实验室的探测器模块（如液氙时间投影室、锗探测器阵列）。"""

    __tablename__ = 'detector_modules'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    module_code = db.Column(db.String(50))
    target_material = db.Column(db.String(50))
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='commissioning')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sessions = db.relationship('RunSession', backref='detector', lazy=True)


class RunSession(db.Model):
    """一次数据采集 / 分析运行（校准、本底测量或暗物质搜索）。"""

    __tablename__ = 'run_sessions'
    id = db.Column(db.Integer, primary_key=True)
    detector_id = db.Column(db.Integer, db.ForeignKey('detector_modules.id'), nullable=False)
    session_date = db.Column(db.DateTime, default=datetime.utcnow)
    run_type = db.Column(db.String(50))
    exposure_hours = db.Column(db.Float)
    energy_threshold_kev = db.Column(db.Float, default=1.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    spectra = db.relationship('BackgroundSpectrum', backref='session', lazy=True)
    events = db.relationship('SignalEvent', backref='session', lazy=True)
    recordings = db.relationship('AudioRecording', backref='session', lazy=True)


class BackgroundSpectrum(db.Model):
    """本底谱的一个能量 bin 及拟合曲线取值。"""

    __tablename__ = 'background_spectra'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('run_sessions.id'), nullable=False)
    energy_kev = db.Column(db.Float, nullable=False)
    counts = db.Column(db.Float, nullable=False)
    fit_value = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SignalEvent(db.Model):
    """疑似暗物质散射事件（含 S1/S2 光电信号）。"""

    __tablename__ = 'signal_events'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('run_sessions.id'), nullable=False)
    event_time = db.Column(db.DateTime, default=datetime.utcnow)
    energy_kev = db.Column(db.Float, nullable=False)
    s1_pe = db.Column(db.Float)
    s2_pe = db.Column(db.Float)
    classification = db.Column(db.String(50), default='unclassified')
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AudioRecording(db.Model):
    __tablename__ = 'audio_recordings'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('run_sessions.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    duration_seconds = db.Column(db.Float)
    transcription_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transcriptions = db.relationship('Transcription', backref='recording', lazy=True)


class Transcription(db.Model):
    __tablename__ = 'transcriptions'
    id = db.Column(db.Integer, primary_key=True)
    recording_id = db.Column(db.Integer, db.ForeignKey('audio_recordings.id'), nullable=False)
    speaker = db.Column(db.String(50))
    speaker_role = db.Column(db.String(50))
    start_time = db.Column(db.Float)
    end_time = db.Column(db.Float)
    text = db.Column(db.Text, nullable=False)
    physics_terms = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RunSummary(db.Model):
    __tablename__ = 'run_summaries'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('run_sessions.id'), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    anomaly_analysis = db.Column(db.Text)
    run_plan = db.Column(db.Text)
    calibration_notes = db.Column(db.Text)
    key_terms = db.Column(db.Text)
    sent_to_team = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    id = db.Column(db.Integer, primary_key=True)
    summary_id = db.Column(db.Integer, db.ForeignKey('run_summaries.id'), nullable=False)
    recipient = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='sent')
    error_message = db.Column(db.Text)
