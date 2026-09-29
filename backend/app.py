import os
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from models import db
from routes import detector_bp, audio_bp
from validation import ValidationError


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    db.init_app(app)

    app.register_blueprint(detector_bp)
    app.register_blueprint(audio_bp)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()

    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return jsonify({'error': str(err)}), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({'error': 'resource not found'}), 404

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return {
            'status': 'healthy',
            'message': 'Dark Matter Detection Minutes API is running'
        }

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
