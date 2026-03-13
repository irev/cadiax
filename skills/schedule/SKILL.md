# Schedule

## Metadata
- name: schedule
- description: Menjalankan dan menginspeksi scheduler cycle untuk AI otonom personal assistant, termasuk state quiet hours dan hasil loop terjadwal
- aliases: [scheduler, defer, timed-run]
- category: capability
- autonomy_category: scheduling
- risk_level: medium
- side_effects: [scheduler_run, job_queue_write, planner_write]
- requires: []
- idempotency: mixed
- schema_version: v1
- timeout_behavior: fail_fast
- retry_policy: none

## Description
Skill ini memberi surface eksplisit untuk scheduling runtime yang sudah ada.

## Purpose
- Menginspeksi state scheduler dan memicu scheduler cycle secara terkontrol.
- Menjadi capability dasar untuk time-based execution yang saat ini tersedia di runtime.

## Boundaries
- Gunakan untuk scheduler runtime, bukan untuk percakapan kalender umum atau itinerary.
- Jangan gunakan untuk planning umum; gunakan `planner` atau `ai`.
- Skill ini menghormati quiet hours dan privacy governance yang sudah ada.
- Surface ini belum dimaksudkan sebagai full reminder/calendar system.

## Primary Inputs
- `schedule show`
- `schedule run`
- opsi tambahan untuk `run`:
  - `cycles=<n>`
  - `steps=<n>`
  - `interval=<seconds>`
  - `enqueue_first=true|false`
  - `until_idle=true|false`

## Expected Outputs
- Snapshot state scheduler terkini.
- Ringkasan hasil run scheduler termasuk cycle, processed count, dan final status.
- Status `quiet_hours` bila scheduler ditahan governance layer.

## State Touchpoints
- Scheduler runtime state.
- Job queue and planner follow-through through scheduler cycles.
- Execution history dan metrics scheduler.

## Failure Modes
- Input numerik tidak valid.
- Scheduler tidak memproses apa pun karena queue kosong.
- Scheduler langsung berhenti karena quiet hours aktif.

## Success Criteria
- User bisa melihat state scheduler tanpa side effect mutatif.
- User bisa memicu run scheduler dengan parameter eksplisit dan hasil yang tertrace.
- Quiet hours tetap dihormati.
- Capability schedule menjadi eksplisit tanpa mengaburkan batas dengan planner atau runner.

## Triggers
- schedule
- scheduler
- defer
- timed-run

## AI Instructions
Gunakan skill ini ketika user ingin:
- melihat state scheduler
- menjalankan cycle scheduler
- memeriksa apakah quiet hours menunda automation

Contoh:
- "lihat scheduler" -> `schedule show`
- "jalankan scheduler sekali" -> `schedule run`
- "jalankan scheduler 2 cycle" -> `schedule run cycles=2`
- "cek apakah scheduler tertahan quiet hours" -> `schedule show`

## Execution
Handler Python terletak di `script/handler.py`
