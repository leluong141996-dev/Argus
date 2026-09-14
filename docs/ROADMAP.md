# ARGUS — Implementation Roadmap

> Trạng thái: **alpha**. Repo hiện có **một lát cắt dọc hoàn chỉnh** (pipeline scoring +
> plugin `agent_reasoning`), nhưng phần lớn cấu trúc mà README/blog mô tả **chưa tồn tại**.
> File này là bản kiểm kê đầy đủ những gì cần làm, chia theo milestone, dễ tick tracking.
>
> Nguồn ý tưởng: <https://engineering.grab.com/grab-bench-evaluating-ai>

## Ký hiệu

- `[ ]` chưa làm · `[~]` đang làm · `[x]` xong
- **AC** = Acceptance Criteria (điều kiện coi như "xong")
- 🔗 = phụ thuộc milestone khác

---

## 0. Ảnh chụp hiện trạng (đã có, chạy được, có test)

| Thành phần | File | Ghi chú |
|---|---|---|
| Pipeline primitives | `core/pipeline.py` | `Stage`, `StageResult`, `PipelineScore` |
| Runner (1 case) | `core/runner.py` | `run_case`, `RunConfig`, validate stage coverage |
| COST / LATENCY stage | `core/cost.py`, `core/latency.py` | runner-owned |
| Row record | `core/record_schema.py` | `to_dict()`, `legacy_score` |
| Plugin contract | `plugins/base.py` | `TaskPlugin`, `GenerationResult` |
| Plugin tham chiếu | `plugins/agent_reasoning/` | ontology + cases + plugin, 4 stage |
| Aggregate | `dashboards/aggregate.py` | theo `(task, model, stage)` |
| Demo + test | `examples/run_pipeline_demo.py`, `tests/test_pipeline_scoring.py` | pytest xanh |

**Kết luận:** lõi chấm điểm tốt. Thiếu toàn bộ lớp *chạy thật* (CLI/config/provider), *lớp tin cậy*
(baselines/gates/datasets), *dashboard web*, và *các plugin còn lại*.

---

## Milestone 0 — Repo hygiene & README trung thực (nhỏ, làm trước)

README đang mô tả nhiều thứ **chưa có** như thể đã có. Sửa để README khớp thực tế trước khi build tiếp.

- [x] **Sửa link logo hỏng**: đã move `argus-logo.png` + `argus-how-it-works.png` vào `.github/assets/`; README dòng 2 & 37 trỏ đúng.
- [x] **Sửa Roadmap README**: mục "Web dashboard" đổi `[x]` → `[ ]` (planned).
- [x] **Đánh dấu phần aspirational**: thêm note "Project status" đầu README + note "planned" ở Dashboard / Project structure / Quick start; sửa cây thư mục bỏ `argus-how-it-works.svg` không tồn tại.
- [x] **`requirements.txt`** (tối thiểu: pytest; PyYAML/httpx ghi chú cho M1).
- [x] Trỏ README/roadmap tới file `docs/ROADMAP.md` này.

**AC:** clone repo, mọi ảnh hiển thị, mọi đường dẫn/lệnh trong README hoặc chạy được hoặc ghi rõ "planned".

---

## Milestone 1 — Chạy end-to-end (Slice A) ⭐ ưu tiên

Biến repo từ "thư viện" thành "công cụ chạy được": `argus run --config … → ghi records JSON`.
Provider mục tiêu ban đầu: **mock + Groq** (OpenAI-compatible). Layout **phẳng** (giữ import `from core…`).

### 1.1 Đóng gói
- [x] `pyproject.toml`: metadata + entry point `argus = "core.cli:main"` + deps `PyYAML`, `httpx`.
- [x] Cập nhật `requirements.txt` khớp `pyproject.toml`.

### 1.2 Config layer
- [x] `core/config.py`: đọc YAML → dựng `RunConfig` + provider factory.
- [x] `configs/agent_reasoning.yaml` mẫu (task, provider, models, dataset, concurrency, seed, budgets, output).
- [x] Validate config rõ ràng (thiếu key → lỗi dễ hiểu, không traceback trần).

### 1.3 Provider layer
- [x] `core/providers/base.py`: interface `complete(prompt, **params) -> str`.
- [x] `core/providers/mock.py`: deterministic (phục vụ demo/test/gates sau).
- [x] `core/providers/groq.py`: POST `api.groq.com/openai/v1/chat/completions`, key qua `GROQ_API_KEY`.
- [x] Provider được bọc thành `model_call: str -> str` để **giữ nguyên** contract plugin + test hiện tại.

### 1.4 Dataset loader
- [x] `core/dataset.py`: nạp list case từ file JSON theo path trong config.
- [x] Seed `datasets/teaching/agent_reasoning/*.json` từ `plugins/agent_reasoning/cases.py`.

### 1.5 Plugin registry
- [x] `core/registry.py`: map tên task (`"agent_reasoning"`) → class plugin.

### 1.6 Batch runner
- [x] `run_batch` trong `core/runner.py`: lặp cases × models qua `ThreadPoolExecutor(max_workers=concurrency)`.
- [x] Case lỗi → gán `skip_reason`, không crash cả run. Thứ tự output ổn định.

### 1.7 Records writer + CLI
- [x] `core/report_io.py`: ghi `list[RowRecord] → JSON` ra `output`.
- [x] `core/cli.py`: `argus run --config PATH [--out PATH]` (argparse), in 1 dòng tóm tắt.
- [x] Cờ `--baselines-only` (README hứa) → báo "not implemented, planned M2" thay vì crash.

### 1.8 Tests
- [x] Test: load config, mock provider, batch ≥2 case, file records ghi đúng, registry resolve đúng.

**AC:** `argus run --config configs/agent_reasoning.yaml` với `GROQ_API_KEY` chạy Groq thật, ghi ra
`report.json` gồm nhiều `RowRecord` hợp lệ; chạy với provider `mock` không cần mạng.

> **Follow-up (ghi nợ có chủ đích):** token thật từ Groq **chưa** được nối vào `GenerationResult`
> (plugin vẫn tự ước lượng token). "Plumb real token usage" → xem Backlog.

---

## Milestone 2 — Trust machinery (Slice D) — điểm khác biệt cốt lõi của blog

"Bắt shortcut" và "gate trước khi tin kết quả" là lý do GrabBench tồn tại. 🔗 M1.

### 2.1 Baselines first-class
- [ ] `baselines/base.py`: interface baseline (một `model_call` giả cho một chiến lược shortcut).
- [ ] Baselines dùng chung: `empty_output`, `schema_only`, `cite_all`, `unsafe_sensitive`, `no_op`, `reference/oracle`.
- [ ] Cho phép plugin khai báo baselines nào áp dụng cho nó.
- [ ] `argus run --baselines-only`: chạy baselines, khẳng định cái nào *phải fail*.

### 2.2 Gates
- [ ] `gates/`: oracle/reference behaves-as-expected; weak baselines fail; redaction pass (nếu áp dụng); score-spread không degenerate; canary bắt regression harness.
- [ ] Gate chạy **trước** khi một comparison run được coi là đáng tin (exit code khác 0 nếu gate fail).

### 2.3 Datasets teaching/certification
- [ ] Chuẩn hoá `datasets/teaching/` (public) vs `datasets/certification/` (hidden, access-controlled).
- [ ] Loader tôn trọng ranh giới; certification không lẫn vào teaching.
- [ ] Canary suite tối thiểu (case cố tình đơn giản/malformed, kết quả kỳ vọng biết trước).

**AC:** `argus run --baselines-only` báo rõ baseline nào fail đúng như thiết kế; gate fail → run bị chặn với lý do cụ thể.

---

## Milestone 3 — Dashboard web (Slice B)

Cả mục "Dashboard" trong README hiện chưa build. Client-side, không server, không build step. 🔗 M1.

- [ ] `dashboards/export.py`: `list[RowRecord] → report.json` cho web.
- [ ] `dashboards/web/template.html`: nguồn dashboard (stage matrix + row table + expand chi tiết + "Load report.json").
- [ ] `dashboards/build_dashboard.py`: nhúng report vào template → `index.html`.
- [ ] `examples/generate_sample_report.py`: sinh demo report bundled.
- [ ] `dashboards/web/index.html`: bản build sẵn kèm demo data.

**AC:** mở `dashboards/web/index.html` trực tiếp trong trình duyệt thấy demo; "Load report.json" nạp được output từ M1.

---

## Milestone 4 — Thêm task plugins (Slice C)

Mở rộng bề mặt benchmark. Mỗi plugin: case format + ontology/contract + scorer + baselines. 🔗 M1, M2.

- [ ] `plugins/tool_use/` — deterministic: canonical tool selection (ACTION_SELECTION) + parameter correctness (tag).
- [ ] `plugins/query_generation/` — **LLM judge** (business intent mở) → cần hạ tầng judge (`core/judge.py`?).
- [ ] `plugins/multimodal_matching/` — deterministic, exact label match; xử lý input đa phương thức.
- [ ] `plugins/agentic_coding/` — visible + hidden tests, hard-failure gates, anti-gaming; stage set giàu hơn.

**AC:** mỗi plugin mới có ≥1 case teaching, scorer, bộ baselines shortcut, và test bắt được shortcut ở đúng stage.

---

## Backlog / follow-ups (chưa gắn milestone)

- [ ] **Plumb real token usage** từ provider vào `GenerationResult` (thay ước lượng của plugin) → COST stage chính xác.
- [ ] `configs/pricing.yaml` + loader cho `core/cost.py` (bỏ phụ thuộc `DEFAULT_PRICING` ngoài demo).
- [ ] Per-stage weight overrides trong `RunConfig` (đổi ưu tiên stage khi report mà không sửa plugin).
- [ ] `argus report --run-id` (đọc records → in summary console) — mục CLI thứ 2 README hứa.
- [ ] Migrate `tool_use`/`agentic_coding` sang stage set như mô tả cuối `docs/pipeline-scoring.md`.
- [ ] Plugin authoring guide + cookiecutter template (roadmap README).
- [ ] Standardized canary suite chia sẻ giữa mọi plugin (roadmap README).

---

## Thứ tự đề xuất & phụ thuộc

```
M0 (hygiene)
      │
      ▼
M1 (end-to-end run)  ⭐  ── nền tảng cho tất cả
      ├──────────────┬──────────────┐
      ▼              ▼              ▼
M2 (trust)       M3 (dashboard)   M4 (plugins)
```

- **M0** làm ngay, rất nhỏ.
- **M1** là nền — không có nó thì M2/M3/M4 không có dữ liệu thật để chạy.
- **M2 / M3 / M4** sau M1 là **độc lập**, có thể làm song song hoặc theo nhu cầu.
- Mỗi milestone nên có spec riêng (brainstorm → `docs/superpowers/specs/…` → writing-plans) trước khi code.
