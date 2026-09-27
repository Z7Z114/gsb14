import json
from typing import Dict, List
from config import Config

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AIService:
    def __init__(self):
        self.client = None
        if OPENAI_AVAILABLE and Config.OPENAI_API_KEY:
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_run_summary(
        self,
        transcriptions: List[Dict],
        spectra: List[Dict],
        events: List[Dict],
        detector_info: Dict
    ) -> Dict:
        if not self.client:
            return self._mock_summary(transcriptions, spectra, events, detector_info)

        try:
            prompt = self._build_summary_prompt(
                transcriptions, spectra, events, detector_info
            )

            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        'role': 'system',
                        'content': '你是一名地下暗物质探测实验的物理学家，负责整理探测器运行会议的讨论，生成专业的运行纪要与异常事件分析。'
                    },
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            content = response.choices[0].message.content
            return self._parse_ai_response(content)
        except Exception as e:
            print(f'OpenAI API error: {e}')
            return self._mock_summary(transcriptions, spectra, events, detector_info)

    def _build_summary_prompt(
        self,
        transcriptions: List[Dict],
        spectra: List[Dict],
        events: List[Dict],
        detector_info: Dict
    ) -> str:
        transcription_text = '\n'.join([
            f"[{t.get('speaker_role', 'unknown')}] {t.get('text', '')}"
            for t in transcriptions
        ])

        spectrum_summary = self._summarize_spectra(spectra)
        event_summary = self._summarize_events(events)

        prompt = f"""
请基于以下信息生成地下暗物质探测实验的运行纪要：

【探测器信息】
名称: {detector_info.get('name', '未知')}
模块编号: {detector_info.get('module_code', '未知')}
靶物质: {detector_info.get('target_material', '未知')}
位置: {detector_info.get('location', '未知')}

【物理学家与值班员讨论记录】
{transcription_text}

【本底谱摘要】
{spectrum_summary}

【疑似信号事件摘要】
{event_summary}

请以JSON格式输出，包含以下字段：
1. summary_text: 运行讨论的专业摘要（300-500字）
2. anomaly_analysis: 异常事件分析，识别本底异常与可能的探测器效应
3. run_plan: 后续运行计划，包含曝光量、能量阈值与校准安排
4. calibration_notes: 能量刻度与探测器响应校准注意事项
5. key_terms: 提取的关键物理术语列表

请严格按照JSON格式输出，不要有其他文字。
"""
        return prompt

    def _summarize_spectra(self, spectra: List[Dict]) -> str:
        if not spectra:
            return '无本底谱数据'

        total_counts = sum(d.get('counts', 0) for d in spectra)
        energies = [d.get('energy_kev', 0) for d in spectra]
        summary = [
            f'能量范围: {min(energies):.2f} - {max(energies):.2f} keV',
            f'总本底计数: {total_counts:.0f}',
        ]
        return '\n'.join(summary)

    def _summarize_events(self, events: List[Dict]) -> str:
        if not events:
            return '无疑似信号事件'

        energies = [d.get('energy_kev', 0) for d in events]
        return f'事件数: {len(events)}，能量范围: {min(energies):.2f} - {max(energies):.2f} keV'

    def _parse_ai_response(self, content: str) -> Dict:
        try:
            json_str = content.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            return json.loads(json_str.strip())
        except Exception as e:
            print(f'Failed to parse AI response: {e}')
            return {
                'summary_text': content,
                'anomaly_analysis': '',
                'run_plan': '',
                'calibration_notes': '',
                'key_terms': []
            }

    def _mock_summary(
        self,
        transcriptions: List[Dict],
        spectra: List[Dict],
        events: List[Dict],
        detector_info: Dict
    ) -> Dict:
        return {
            'summary_text': f"""本次{detector_info.get('name', '探测器')}运行会议围绕低能区本底偏高的问题展开。
本底谱显示 2-6 keV 区间的计数率高于上一轮基线约 18%，物理学家判断主要来自氡子体衰变
产生的电子反冲与部分宇生放射性。值班员报告液氙纯度巡检正常，制冷系统与漂移电场稳定。
会议决定下一轮提高屏蔽体吹扫流量、重新做能量刻度，并在盲分析前完成模拟样本的更新。""",
            'anomaly_analysis': """【异常事件分析】
1. 低能区本底抬升: 2-6 keV 计数率较基线偏高约 18%
   - 主要来源判断为氡污染导致的电子反冲本底
   - 排除探测器噪声与漂移电场异常
2. 宇生中子贡献: 结合符合计数判断占比有限
   - 建议延长宇生本底扣除样本
3. 单光子计数: 光电倍增管噪声处于正常范围""",
            'run_plan': """【后续运行计划】
1. 曝光量: 下一轮计划累计曝光 60 天·公斤
2. 能量阈值: 低能阈值上调至探测效率平台区
3. 校准安排: 每周一次钾-40 与铯-137 刻度
4. 屏蔽维护: 提高吹扫流量并更换部分低本底铅""",
            'calibration_notes': """【校准注意事项】
1. 能量刻度前确认漂移电场稳定
2. 记录淬灭因子与光电产额变化
3. 盲分析前冻结校准参数
4. 保存原始波形用于复核""",
            'key_terms': [
                '暗物质', '本底谱', '电子反冲', '氡污染', '能量刻度',
                '液氙', '时间投影室', '屏蔽体', '曝光量', '能量阈值',
                '信号效率', '排除曲线'
            ]
        }
