# Policy

## Metadata
- name: policy
- description: Menginspeksi aturan policy aktif dan menguji keputusan otorisasi command secara read-only untuk AI otonom personal assistant
- aliases: [guard, access-policy, authorize]
- category: capability
- autonomy_category: governance
- risk_level: low
- side_effects: [policy_audit]
- requires: []
- idempotency: idempotent
- schema_version: v1
- timeout_behavior: fail_fast
- retry_policy: none

## Description
Skill ini memberi surface eksplisit untuk policy diagnostics dan simulasi keputusan otorisasi.

## Purpose
- Menampilkan policy aktif yang relevan bagi operator atau agent.
- Menguji apakah prefix/args tertentu akan diizinkan atau ditolak oleh policy tanpa menjalankan aksi sebenarnya.

## Boundaries
- Gunakan untuk inspeksi dan simulasi policy.
- Jangan gunakan untuk mengubah environment policy atau mengeksekusi command target.
- Skill ini bersifat read-only terhadap runtime behavior; hasil `check` adalah simulasi keputusan.

## Primary Inputs
- `policy show`
- `policy check prefix=<name>`
- opsi tambahan untuk `check`:
  - `args=<text>`
  - `source=<cli|telegram|api|email|whatsapp>`
  - `roles=<a,b>`
  - `session_mode=<main|shared>`

## Expected Outputs
- Snapshot policy diagnostics aktif.
- Hasil keputusan `allowed/denied` untuk simulasi command.
- Penjelasan alasan policy bila keputusan ditolak.

## State Touchpoints
- Policy diagnostics.
- Event bus policy statistics.
- Simulasi TransportContext untuk authorize path.

## Failure Modes
- Prefix simulasi tidak diberikan.
- Source atau session_mode tidak valid.
- Hasil simulasi tidak representatif bila context input terlalu minim.

## Success Criteria
- User bisa melihat policy aktif secara eksplisit dari skill layer.
- Simulasi check menjelaskan `allowed`, `reason`, dan `message` tanpa mengeksekusi command target.
- Capability governance ini menjadi surface eksplisit, bukan hanya implicit di doctor/admin.

## Triggers
- policy
- guard
- access-policy
- authorize

## AI Instructions
Gunakan skill ini ketika user ingin:
- melihat rule policy aktif
- memeriksa apakah command tertentu akan lolos policy
- memahami kenapa command ditolak

Contoh:
- "lihat policy aktif" -> `policy show`
- "cek apakah executor next boleh untuk telegram approved" -> `policy check prefix=executor args=next source=telegram roles=approved`

## Execution
Handler Python terletak di `script/handler.py`
