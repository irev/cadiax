# Monitor

## Metadata
- name: monitor
- description: Memantau sinyal operasional penting seperti error, timeout, leased jobs, queue depth, policy denial, dan quiet hours untuk AI otonom personal assistant
- aliases: [watch-health, alert-state, monitor-runtime]
- category: capability
- autonomy_category: monitoring
- risk_level: low
- side_effects: [runtime_read]
- requires: []
- idempotency: idempotent
- schema_version: v1
- timeout_behavior: fail_fast
- retry_policy: none

## Description
Skill ini memberi surface eksplisit untuk monitoring operasional dan deteksi sinyal waspada.

## Purpose
- Menyorot sinyal penting yang perlu perhatian operator atau agent.
- Membedakan mode monitoring dari sekadar snapshot observasi umum.

## Boundaries
- Gunakan untuk health watch, warning detection, dan ringkasan sinyal runtime.
- Jangan gunakan untuk eksekusi mitigasi langsung; gunakan skill lain bila tindakan diperlukan.
- Skill ini read-only dan fokus pada signal extraction, bukan full analytics engine.

## Primary Inputs
- `monitor summary`
- `monitor alerts`
- `monitor health`
- opsi tambahan:
  - `scope=<name>`
  - `roles=<a,b>`

## Expected Outputs
- Ringkasan health monitoring dengan daftar alert atau warning aktif.
- Penjelasan bila saat ini tidak ada sinyal kritis yang menonjol.

## State Touchpoints
- Config/status snapshot.
- Metrics snapshot.
- Event bus snapshot.
- Job queue and scheduler summary.

## Failure Modes
- Data monitoring masih terlalu sedikit karena runtime baru mulai.
- Scope filter terlalu sempit sehingga sinyal tidak terlihat.
- Hasil monitoring terlalu umum bila belum ada activity sample.

## Success Criteria
- Skill menyorot warning yang relevan tanpa perlu operator membaca semua snapshot mentah.
- Output memisahkan kondisi sehat dari kondisi yang butuh perhatian.
- Scope/role filter tetap dihormati.

## Triggers
- monitor
- watch-health
- alert-state
- monitor-runtime

## AI Instructions
Gunakan skill ini ketika user ingin:
- memantau health runtime
- mencari sinyal warning yang aktif
- mengetahui apakah ada leased job, failed job, timeout, atau policy denial

Contoh:
- "monitor kondisi sistem" -> `monitor summary`
- "lihat alert aktif" -> `monitor alerts`
- "cek health finance scope" -> `monitor health scope=finance-agent roles=finance`

## Execution
Handler Python terletak di `script/handler.py`
