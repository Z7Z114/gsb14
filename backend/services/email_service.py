import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import Config
from services.crypto_service import encrypt_payload


class EmailService:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.username = Config.SMTP_USERNAME
        self.password = Config.SMTP_PASSWORD
        self.use_tls = Config.SMTP_USE_TLS

    def send_run_summary(
        self,
        recipient: str,
        detector_name: str,
        summary_data: dict,
        session_date: datetime
    ) -> bool:
        if not self.smtp_server or not self.username:
            print(f'Mock email sent to {recipient} (SMTP not configured)')
            return True

        try:
            subject = f'【暗物质探测纪要】{detector_name} - {session_date.strftime("%Y-%m-%d")}'
            body = self._build_email_body(detector_name, summary_data, session_date)

            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = recipient
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            print(f'Email sent successfully to {recipient}')
            return True
        except Exception as e:
            print(f'Failed to send email to {recipient}: {e}')
            return False

    def _build_email_body(
        self,
        detector_name: str,
        summary_data: dict,
        session_date: datetime
    ) -> str:
        encrypted = encrypt_payload(
            summary_data.get('summary_text', ''), Config.TRANSMISSION_KEY
        )
        body = f"""
{'=' * 60}
              地下暗物质探测会议纪要
{'=' * 60}

探测器: {detector_name}
运行日期: {session_date.strftime('%Y年%m月%d日 %H:%M')}
生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

{'=' * 60}
【运行摘要】
{'=' * 60}
{summary_data.get('summary_text', '无')}

{'=' * 60}
【异常事件分析】
{'=' * 60}
{summary_data.get('anomaly_analysis', '无')}

{'=' * 60}
【后续运行计划】
{'=' * 60}
{summary_data.get('run_plan', '无')}

{'=' * 60}
【校准注意事项】
{'=' * 60}
{summary_data.get('calibration_notes', '无')}

{'=' * 60}
【关键物理术语】
{'=' * 60}
{', '.join(summary_data.get('key_terms', []))}

{'=' * 60}
【加密传输报文 (AES-ready base64)】
{'=' * 60}
{encrypted}

{'=' * 60}
本邮件由系统自动生成，如有疑问请联系地下实验室物理组。
{'=' * 60}
"""
        return body

    def send_to_physics_team(
        self,
        detector_name: str,
        summary_data: dict,
        session_date: datetime
    ) -> list:
        results = []
        for email in Config.PHYSICS_TEAM_EMAILS:
            email = email.strip()
            if email:
                success = self.send_run_summary(
                    email, detector_name, summary_data, session_date
                )
                results.append({
                    'email': email,
                    'success': success
                })
        return results
