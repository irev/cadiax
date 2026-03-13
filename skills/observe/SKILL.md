# Observe

## Metadata
- name: observe
- description: Mengamati health, status, metrics, event bus, scheduler, job queue, dan snapshot runtime lain secara read-only untuk AI otonom personal assistant
- aliases: [watch, inspect-state, runtime-status]
- category: capability
- autonomy_category: observation
- risk_level: low
- side_effects: [runtime_read]
- requires: []
- idempotency: idempotent
- schema_version: v1
- timeout_behavior: fail_fast
- retry_policy: none

## Description
Skill ini memberi surface eksplisit untuk observasi runtime dan state sistem secara read-only.

## Purpose
- Mengamati kondisi runtime, health, queue, scheduler, metrics, dan event/history tanpa melakukan mutasi.
- Menjadi capability dasar sebelum reasoning, planning, atau tindakan lanjutan dilakukan.

## Boundaries
- Gunakan untuk inspeksi state, health, metrics, dan jejak runtime.
- Jangan gunakan untuk mengubah konfigurasi, queue, memory, atau planner.
- Jangan gunakan untuk verifikasi fakta internet; gunakan `research`.
- Skill ini read-only dan harus tetap aman dipakai untuk operator visibility.

## Primary Inputs
- `observe summary`
- `observe status`
- `observe metrics`
- `observe events`
- `observe history`
- `observe jobs`
- `observe scheduler`
- opsi tambahan: `scope=<name>`, `roles=<role1,role2>`, `limit=<n>`

## Expected Outputs
- Ringkasan runtime yang jelas dan cukup untuk pengambilan keputusan berikutnya.
- Snapshot terstruktur untuk status, metrics, events, history, jobs, atau scheduler.
- Penjelasan bila subcommand tidak valid.

## State Touchpoints
- Runtime diagnostics snapshot.
- Metrics state.
- Event bus snapshot.
- Execution history.
- Job queue dan scheduler summary.

## Failure Modes
- Snapshot kosong karena belum ada aktivitas runtime.
- Scope filter terlalu sempit sehingga data tidak terlihat.
- Subcommand tidak valid atau limit tidak dapat diparse.

## Success Criteria
- Status runtime dapat diamati tanpa side effect mutatif.
- Scope/role filter tetap dihormati saat digunakan.
- Output cukup ringkas untuk summary default dan cukup kaya untuk view JSON.
- Capability ini menjadi surface observasi eksplisit, bukan hanya implicit di `doctor` atau admin API.

## Triggers
- observe
- watch
- inspect-state
- runtime-status

## AI Instructions
Gunakan skill ini ketika user ingin:
- melihat kondisi runtime saat ini
- melihat health atau status sistem
- memeriksa metrics, event bus, job queue, atau scheduler
- mengamati snapshot scoped sebelum planning atau execution

Contoh:
- "amati kondisi runtime saat ini" -> `observe summary`
- "lihat status sistem" -> `observe status`
- "cek metrics runtime" -> `observe metrics`
- "lihat event terbaru" -> `observe events limit=10`
- "amati scope finance" -> `observe status scope=finance-agent roles=finance`

## Execution
Handler Python terletak di `script/handler.py`
