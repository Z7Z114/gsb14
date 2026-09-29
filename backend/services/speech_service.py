import os
import re
from typing import List, Dict
from config import Config

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False


PHYSICS_TERMS = [
    '暗物质', '弱相互作用大质量粒子', 'WIMP', '液氙', '时间投影室', 'TPC',
    '锗探测器', '高纯锗', '本底谱', '本底计数', '能量刻度', '能量阈值',
    '光电倍增管', '闪烁光', '电离信号', 'S1', 'S2', '光电子', 'keV',
    '反冲核', '核反冲', '电子反冲', '信号效率', '曝光量', '探测效率',
    '屏蔽体', '中子本底', '伽马本底', '氡污染', '宇生放射性', '宇生中子',
    '事例率', '散射截面', '自旋无关', '自旋相关', '质量区间', '排除曲线',
    '中微子本底', '中微子雾', '年度调制', '暗物质晕', '银河系晕',
    '蒙特卡洛', '模拟样本', '似然分析', '置信区间', '盲分析',
    '探测器响应', '淬灭因子', '光电产额', '漂移电场', '提取电场',
    '液氙纯度', '氪污染', '氩污染', '制冷系统', '低温恒温器',
    '低本底铅', '聚乙烯屏蔽', '符合计数', '单光子计数', '噪声阈值'
]


class SpeechServiceError(Exception):
    """Whisper / pyannote 已安装且被真实调用，但推理失败。"""


class SpeechService:
    def __init__(self):
        self.whisper_model = None
        self.pyannote_pipeline = None
        self._init_models()

    def _init_models(self):
        if WHISPER_AVAILABLE:
            try:
                self.whisper_model = whisper.load_model('base')
            except Exception as e:
                print(f'Failed to load Whisper model: {e}')
                self.whisper_model = None

        if PYANNOTE_AVAILABLE and Config.HUGGINGFACE_AUTH_TOKEN:
            try:
                self.pyannote_pipeline = Pipeline.from_pretrained(
                    'pyannote/speaker-diarization-3.1',
                    use_auth_token=Config.HUGGINGFACE_AUTH_TOKEN
                )
            except Exception as e:
                print(f'Failed to load pyannote pipeline: {e}')
                self.pyannote_pipeline = None

    def transcribe_audio(self, audio_path: str) -> Dict:
        if not self.whisper_model:
            return self._mock_transcription(audio_path)

        try:
            result = self.whisper_model.transcribe(
                audio_path,
                language='zh',
                word_timestamps=True
            )
            return {
                'text': result['text'],
                'segments': [
                    {
                        'start': seg['start'],
                        'end': seg['end'],
                        'text': seg['text']
                    }
                    for seg in result['segments']
                ]
            }
        except Exception as e:
            raise SpeechServiceError(f'Whisper transcription failed: {e}') from e

    def diarize_speakers(self, audio_path: str) -> List[Dict]:
        if not self.pyannote_pipeline:
            return self._mock_diarization(audio_path)

        try:
            diarization = self.pyannote_pipeline(audio_path)
            speakers = []
            for segment, _, speaker in diarization.itertracks(yield_label=True):
                speakers.append({
                    'start': segment.start,
                    'end': segment.end,
                    'speaker': speaker
                })
            return speakers
        except Exception as e:
            raise SpeechServiceError(f'pyannote diarization failed: {e}') from e

    def combine_transcription_with_speakers(
        self,
        transcription: Dict,
        diarization: List[Dict]
    ) -> List[Dict]:
        segments = transcription.get('segments', [])
        combined = []

        for seg in segments:
            speaker = self._match_speaker(seg['start'], seg['end'], diarization)
            physics_terms = self._extract_physics_terms(seg['text'])
            combined.append({
                'start': seg['start'],
                'end': seg['end'],
                'speaker': speaker,
                'speaker_role': self._guess_speaker_role(speaker, seg['text']),
                'text': seg['text'],
                'physics_terms': physics_terms
            })

        return combined

    def _match_speaker(self, start: float, end: float, diarization: List[Dict]) -> str:
        mid_point = (start + end) / 2
        for seg in diarization:
            if seg['start'] <= mid_point <= seg['end']:
                return seg['speaker']
        return 'UNKNOWN'

    def _guess_speaker_role(self, speaker: str, text: str) -> str:
        physicist_keywords = ['本底', '截面', '排除', '似然', '置信', '本底谱', '刻度', '模拟', '分析']
        operator_keywords = ['制冷', '液位', '纯度', '漂移', '提取', '屏蔽', '维护', '巡检', '值班']

        physicist_count = sum(1 for kw in physicist_keywords if kw in text)
        operator_count = sum(1 for kw in operator_keywords if kw in text)

        if physicist_count > operator_count:
            return 'physicist'
        elif operator_count > physicist_count:
            return 'operator'
        return 'unknown'

    def _extract_physics_terms(self, text: str) -> List[str]:
        found_terms = []
        for term in PHYSICS_TERMS:
            if term in text:
                found_terms.append(term)
        return found_terms

    def _mock_transcription(self, audio_path: str) -> Dict:
        return {
            'text': '本次运行曝光量偏低，本底谱在低能区计数偏高，疑似氡污染引起的电子反冲本底。建议重新做能量刻度并延长屏蔽体吹扫时间。',
            'segments': [
                {
                    'start': 0.0,
                    'end': 4.5,
                    'text': '本次运行的曝光量偏低，本底谱在低能区的计数明显偏高'
                },
                {
                    'start': 4.5,
                    'end': 9.0,
                    'text': '初步判断是氡污染带来的电子反冲本底，需要排查探测器纯度'
                },
                {
                    'start': 9.0,
                    'end': 13.5,
                    'text': '建议重新做一次能量刻度，并把低能阈值上调到探测效率稳定区间'
                },
                {
                    'start': 13.5,
                    'end': 18.0,
                    'text': '同时延长屏蔽体的吹扫时间，下一轮再评估WIMP质量区间的排除曲线'
                }
            ]
        }

    def _mock_diarization(self, audio_path: str) -> List[Dict]:
        return [
            {'start': 0.0, 'end': 4.5, 'speaker': 'SPEAKER_00'},
            {'start': 4.5, 'end': 9.0, 'speaker': 'SPEAKER_01'},
            {'start': 9.0, 'end': 13.5, 'speaker': 'SPEAKER_00'},
            {'start': 13.5, 'end': 18.0, 'speaker': 'SPEAKER_01'}
        ]
