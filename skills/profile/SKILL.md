# Profile

## Metadata
- name: profile
- description: Mengelola profil personalisasi markdown untuk private AI, termasuk purpose, preferences, constraints, dan konteks jangka panjang
- aliases: [persona, personalize]
- category: core
- autonomy_category: memory
- risk_level: high
- side_effects: [profile_write]
- requires: []
- idempotency: non_idempotent

## Description
Skill ini mengelola file markdown personalisasi agent.

## Purpose
- Mengelola identitas, preferensi, constraint, dan orientasi jangka panjang agent.
- Menjadi capability utama untuk personalisasi perilaku agent tanpa mencampur policy, secrets, atau planner state.

## Boundaries
- Gunakan untuk preference, persona, tone, style, dan identitas kerja agent.
- Jangan gunakan untuk menyimpan credential atau rahasia; gunakan `secrets`.
- Jangan gunakan untuk task operasional harian; gunakan `planner` atau `memory` sesuai kebutuhan.
- Jangan gunakan sebagai pengganti privacy/policy control.

## Primary Inputs
- `profile show`
- `profile set-purpose <text>`
- `profile add-preference <text>`
- `profile remove-preference <text>`
- `profile set-formality <value>`
- `profile set-brevity <value>`
- `profile set-proactive-mode <value>`
- `profile set-summary-style <value>`
- `profile set-channels <values>`
- `profile reset-preferences`

## Expected Outputs
- Snapshot profil personalisasi yang jelas dan dapat dibaca.
- Konfirmasi bahwa preference atau persona berhasil diperbarui.
- Penolakan yang jelas bila input tidak valid atau di luar boundary profile.

## State Touchpoints
- Structured preference profile durable state.
- Personality prompt context.
- Identity dan soul startup documents saat dipakai untuk prompt assembly.

## Failure Modes
- Nilai preference tidak valid atau tidak dikenali.
- User mencoba menyimpan data yang lebih cocok ke secrets atau policy.
- Update profile bertabrakan dengan format structured preference yang diharapkan.
- Workspace document tidak tersedia walau state durable tetap ada.

## Success Criteria
- Profile dapat dibaca dan diperbarui tanpa memengaruhi secret, planner, atau privacy state secara tidak semestinya.
- Structured preference tersusun konsisten dan dapat dipakai ulang oleh personality layer.
- Prompt personalization menjadi lebih jelas tanpa membuat policy boundary kabur.
- Error input invalid dinyatakan eksplisit dan tidak merusak profile yang sudah ada.

## Triggers
- profile
- persona
- personalize

## AI Instructions
Gunakan skill ini ketika user ingin:
- mengatur identitas atau tujuan jangka panjang agent
- menambah preferensi kerja
- menambah constraint tetap
- melihat file profil personalisasi

Contoh:
- "atur tujuan agent menjadi private ai untuk tim internal" -> `profile set-purpose private ai untuk tim internal`
- "tambahkan preferensi jawaban ringkas" -> `profile add-preference jawaban ringkas`
- "lihat profil agent" -> `profile show`

## Execution
Handler Python terletak di `script/handler.py`
