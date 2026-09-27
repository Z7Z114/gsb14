from .speech_service import SpeechService
from .ai_service import AIService
from .email_service import EmailService

speech_service = SpeechService()
ai_service = AIService()
email_service = EmailService()

__all__ = ['speech_service', 'ai_service', 'email_service']
