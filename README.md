# 地下实验室暗物质探测会议微弱信号纪要系统

地下暗物质探测实验的运行会议纪要全栈系统：前端展示探测器本底谱与拟合曲线、疑似信号事件，
后端记录物理学家与值班运行员的讨论录音，调用 Whisper 转写探测器模块与能量刻度等术语、
pyannote 区分物理学家与设备值班员、OpenAI 生成异常事件讨论与运行计划摘要，
并把纪要加密后邮件发送给地下实验室物理组。

## 项目结构

```
.
├── backend/                    # Flask 后端
│   ├── app.py                  # 应用入口（create_app 工厂 + /api/health）
│   ├── config.py               # 配置与上传文件校验
│   ├── models.py               # SQLAlchemy 数据模型
│   ├── routes/
│   │   ├── detector_routes.py  # 探测器 / 运行会话 / 本底谱 / 信号事件 API
│   │   └── audio_routes.py     # 上传 / 转写 / 摘要 / 加密 / 邮件 API
│   ├── services/
│   │   ├── speech_service.py   # Whisper + pyannote（未安装时降级为 mock）
│   │   ├── ai_service.py       # OpenAI 摘要生成（未配置 Key 时降级为 mock）
│   │   ├── crypto_service.py   # 纪要加密传输（密钥流 + HMAC 完整性标签）
│   │   └── email_service.py    # SMTP 发送
│   └── tests/                  # pytest 冒烟测试
├── frontend/                   # React + Vite + MUI + Recharts
│   └── src/pages/              # Dashboard / DetectorList / DetectorDetail / SessionDetail / TranscriptionView / SummaryView
├── requirements.txt            # 后端依赖（轻量，可离线跑测试）
├── requirements-ml.txt         # Whisper / pyannote 等重型可选依赖
└── .env.example
```

## 运行方式

后端（Python 3.11+）：

```bash
pip install -r requirements.txt
cd backend && python app.py           # http://localhost:5000
```

前端（Node 18+，可选，本次任务不涉及）：

```bash
cd frontend && npm install && npm run dev   # http://localhost:3000，/api 代理到 5000
```

测试：

```bash
cd backend && python -m pytest -q
```

`requirements.txt` 只包含轻量依赖。Whisper / pyannote（`requirements-ml.txt`）以及 OpenAI Key 都是
**可选的**：未安装模型、未配置 Key 时 `speech_service` / `ai_service` 会走确定性的 mock 分支，
因此后端与测试可在无网络、无 GPU、不调用任何外部 API 的环境下跑通。

## API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET/POST | `/api/detectors` | 探测器列表 / 新建 |
| GET | `/api/detectors/<id>` | 探测器详情（含 sessions） |
| GET/POST | `/api/detectors/<id>/sessions` | 运行会话列表 / 新建 |
| GET | `/api/detectors/sessions/<session_id>` | 运行会话详情 |
| GET/POST | `/api/detectors/sessions/<session_id>/spectra` | 本底谱 bin |
| GET/POST | `/api/detectors/sessions/<session_id>/events` | 疑似信号事件 |
| POST | `/api/audio/upload/<session_id>` | 上传会议录音 |
| POST | `/api/audio/transcribe/<recording_id>` | 转写录音 |
| GET | `/api/audio/recordings/<recording_id>` | 录音详情 |
| GET | `/api/audio/recordings/<recording_id>/transcriptions` | 转写结果 |
| POST | `/api/audio/generate-summary/<session_id>` | 生成运行纪要 |
| GET | `/api/audio/summaries/<summary_id>` | 纪要详情 |
| POST | `/api/audio/summaries/<summary_id>/encrypt` | 加密纪要报文 |
| POST | `/api/audio/summaries/<summary_id>/send-email` | 发送纪要邮件 |
| POST | `/api/audio/sessions/<session_id>/full-process` | 一键处理（转写 + 摘要 + 邮件） |

## 行为规格（验收标准）

本节是本次修复的验收依据，逐条以本节为准。

### A. 输入校验与错误响应

1. 接收 JSON body 的接口（`POST /api/detectors`、`POST /api/detectors/<id>/sessions`、
   `POST .../spectra`、`POST .../events`、`POST /api/audio/summaries/<id>/encrypt`）
   在 body 缺失、不是合法 JSON、缺少必填字段，或字段类型 / 取值非法时，必须返回 `400`
   并带 JSON 错误信息；不得抛出 `KeyError` / `TypeError` 变成 `500`。
2. 必填字段：探测器 `name`、运行会话 `run_type`（均为非空字符串）；
   本底谱 `energy_kev`、`counts`（数值）；信号事件 `energy_kev`（数值）。可选的数值字段（`exposure_hours`、`energy_threshold_kev`、
   `s1_pe`、`s2_pe`、`fit_value`）若给出，必须是合法数值且不得为负数；
   类型不对（如 `"abc"`）同样按 `400` 处理。`energy_kev` 为 0 合法，负数非法。
3. 资源不存在时返回 `404`（JSON 错误体），不能是 `500`。

### B. 探测器与运行会话

4. `GET /api/detectors/<id>/sessions` 的每个会话必须返回 `has_recording`（是否存在录音）
   与 `has_summary`（该会话是否已有运行纪要）。**有录音但尚未生成纪要时为 `false`，
   生成纪要后为 `true`；该接口在任意数据组合下都不得因内部错误返回 `500`。**
5. `GET /api/detectors/sessions/<session_id>` 必须存在，返回该会话详情，字段包含
   `id`、`detector_id`、`run_type`、`exposure_hours`、`energy_threshold_kev`、`notes`、
   `session_date`；会话不存在时 `404`。前端的运行详情页（SessionDetail）正是通过该接口加载数据。
6. `GET /api/detectors` 返回的每个探测器对象必须带 `sessions` 数组（该探测器的运行会话），
   使前端仪表盘能统计「运行次数」；列表元素之间不得共享同一可变对象。

### C. 录音上传与转写

7. 上传按扩展名白名单校验（`wav` / `mp3` / `m4a` / `flac` / `aac`），非白名单返回 `400`；
   未选择文件返回 `400`。落盘文件名必须去除路径成分，不允许写出上传目录之外
   （例如 `../../etc/passwd.wav` 不得逃逸）。
8. 上传成功后返回的 `file_name` 必须与前端传入的原始文件名一致，包括中文等非 ASCII 字符；
   落盘文件名需去重且安全，但不得因为名称清洗把 `file_name` 变成扩展名残段
   （例如把 `术前讨论.wav` 变成 `wav`）。该字段在 `GET /api/audio/recordings/<id>` 中同样保持一致。
9. 转写接口必须幂等：对同一条 `recording` 重复调用，不得重复插入转写记录。
   已有转写结果时应直接复用既有结果（可返回 `200` 或 `202`），不产生重复数据。

### D. 外部服务失败不得伪装成功

10. Whisper / pyannote 真的安装且被调用、但推理失败（模型报错、音频损坏等）时，
    不得把 mock 示例文本当作真实转写结果写入数据库并标成 `completed`；
    该次调用必须记为失败（`transcription_status = 'failed'`），并向调用方返回错误响应。
    （注意：模型未安装属于「服务不可用」，仍走 mock 分支，不属于本条。）
11. 同理，已配置 Key 且真实调用 OpenAI 失败（网络错误、`429`、鉴权失败等）时，
    不得把 mock 摘要持久化为正式运行纪要并返回 `201`；必须返回错误响应，
    且数据库中不留下该会话的纪要记录。未配置 Key 的 mock 降级不属于本条。

### E. 纪要邮件与加密传输

12. 纪要邮件：`POST /api/audio/summaries/<id>/send-email` 只有在至少一封邮件真正投递成功时
    才把 `sent_to_team` 置为 `true` 并写入 `sent_at`；没有可投递收件人、或全部投递失败时，
    `sent_to_team` 必须保持 `false`，响应如实给出成功投递数 `sent_count`（未配置 SMTP 时按
    mock 投递成功处理）。
13. `POST /api/audio/summaries/<id>/encrypt` 用 `TRANSMISSION_KEY` 加密 `plaintext`，
    返回 `ciphertext`；同一明文与密钥可被 `decrypt_payload` 还原，不同密钥必须无法还原。
14. 密文必须防篡改：任何对密文正文或完整性标签的改动，在解密时都必须被检出并抛出
    `CryptoError`，绝不能把被篡改的内容当作合法明文返回。

### F. 不得回归

15. 现有 `backend/tests/test_smoke.py` 必须继续全绿。
## 变更说明

本次修复以「行为规格」为验收标准，各问题的根因与修法如下：

- 输入校验缺失（A）：各 POST 接口直接 `data['field']` 取值，body 缺失 / 非法 JSON /
  缺字段时抛 `KeyError` / `TypeError` 变成 500，负数也未拦截。修法：新增
  `backend/validation.py`（`get_json_body` / `require_non_empty_string` /
  `require_number` / `optional_number`，拒绝 bool 与负数，`energy_kev` 允许 0），
  非法输入抛 `ValidationError`，由 `app.py` 注册的错误处理器统一转为 400 JSON；
  同时为 404 注册 JSON 错误体。
- 会话列表 500（B4）：`has_summary` 误写成 `any(r.summary_text for r in s.recordings)`，
  `AudioRecording` 没有 `summary_text` 属性，会话一旦有录音就 `AttributeError`。
  修法：改为按 `RunSummary.session_id` 集合查询判断是否已有纪要。
- 会话详情 404（B5）：`GET /api/detectors/sessions/<session_id>` 路由缺失。
  修法：在 `detector_routes.py` 补上该路由，返回规格要求的全部字段。
- 仪表盘运行次数恒为 0（B6）：`GET /api/detectors` 未返回 `sessions`。
  修法：列表元素带上与详情接口一致的 `sessions` 数组（每元素独立构造）。
- 中文文件名丢失（C8）：`secure_filename` 把 `术前讨论.wav` 清洗成 `wav` 后直接存库。
  修法：展示用 `file_name` 保留原始文件名；落盘文件名单独做安全化
  （`secure_filename` 为空时回退为 `audio.<ext>`，加 uuid 前缀防重名，
  并校验最终路径不逃逸出上传目录）。
- 转写重复插入（C9）：重复调用转写接口每次都重新插入。修法：状态为
  `completed` 且已有转写记录时直接返回既有结果，不再重复写库。
- 失败伪装成功（D10/D11）：`speech_service` / `ai_service` 把真实调用异常吞掉后
  降级为 mock 模板并标成功。修法：模型 / Key 未配置时仍走 mock；一旦真实调用
  失败则抛 `SpeechServiceError` / `AIServiceError`，转写接口记
  `transcription_status = 'failed'` 并返回错误，摘要接口返回 502 且不落库；
  `full-process` 做同样处理。
- 邮件状态虚报（E12）：无论是否投递都置 `sent_to_team = True`。修法：按
  `send_to_physics_team` 的逐收件人结果统计 `sent_count`，只有至少一封投递
  成功才置 `true` 并写 `sent_at`，响应如实返回 `sent_count`
  （SMTP 未配置时按 mock 投递成功计）。
- 加密不校验完整性（E14）：`decrypt_payload` 解密前未验证 HMAC 标签。
  修法：解密前用 `hmac.compare_digest` 校验标签，篡改密文 / 标签或密钥错误
  一律抛 `CryptoError`。

回归保障：新增 `backend/tests/test_spec.py`（18 条规格用例，在未修复实现上失败），
原有 `backend/tests/test_smoke.py` 未改动且继续全绿。

## 技术栈

- 后端：Flask 3、Flask-SQLAlchemy 3、SQLite；Whisper / pyannote / OpenAI 为可选
- 前端：React 18、Vite 5、Material-UI 5、Recharts、React Router 6
- 测试：pytest（`backend/tests`）

## 许可证

MIT License
