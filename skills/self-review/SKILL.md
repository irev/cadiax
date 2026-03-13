# Self Review

## Metadata
- name: self-review
- description: Meninjau output, file, dan rencana kerja agent untuk menemukan risiko, gap, dan perbaikan berikutnya
- aliases: [review, critique, audit]
- category: governance
- autonomy_category: governance
- risk_level: high
- side_effects: [memory_write, lesson_write, planner_write]
- requires: []
- idempotency: non_idempotent

## Description
Skill ini melakukan self-review heuristik terhadap output agent.

## Purpose
- Menilai output, file, rencana kerja, atau artefak agent untuk menemukan risiko, gap, dan perbaikan.
- Menjadi capability evaluasi sebelum agent melanjutkan tindakan yang lebih jauh.

## Boundaries
- Gunakan untuk audit, kritik, dan quality review atas hasil kerja.
- Jangan gunakan untuk menjalankan perubahan langsung; gunakan `executor` atau editing flow setelah review selesai.
- Jangan gunakan untuk verifikasi fakta internet; gunakan `research`.
- Review dapat menghasilkan note atau planner follow-up, tetapi bukan pengganti policy enforcement.

## Primary Inputs
- `self-review file <path>`
- `self-review text <content>`
- `self-review plan`
- `self-review output <content>`

## Expected Outputs
- Daftar temuan utama yang jelas, terutama bug, risiko, regression, atau gap.
- Saran tindak lanjut yang operasional.
- Penjelasan bila artefak input tidak tersedia atau tidak cukup untuk direview.

## State Touchpoints
- Planner follow-up state bila review menghasilkan task.
- Memory atau lessons bila hasil review perlu disimpan.
- Audit trail untuk hasil evaluasi.

## Failure Modes
- File atau teks target tidak tersedia.
- Review terlalu dangkal karena konteks tidak cukup.
- Temuan tidak bisa diprioritaskan karena input terlalu luas.
- User mengharapkan auto-fix padahal skill ini berfokus pada evaluasi.

## Success Criteria
- Temuan disusun berdasarkan severity atau prioritas yang jelas.
- Review menyorot risiko nyata, bukan hanya ringkasan generik.
- Output dapat ditindaklanjuti oleh planner atau executor.
- Skill tidak melakukan mutasi besar tanpa jalur eksplisit terpisah.

## Triggers
- self-review
- review
- critique
- audit

## AI Instructions
Gunakan skill ini ketika user ingin:
- mengevaluasi hasil kerja agent
- mencari risiko atau gap dari file/output
- meminta audit singkat sebelum lanjut kerja

Contoh:
- "review file planner handler" -> `self-review file skills/planner/script/handler.py`
- "audit teks ini" -> `self-review text <isi>`

## Execution
Handler Python terletak di `script/handler.py`
