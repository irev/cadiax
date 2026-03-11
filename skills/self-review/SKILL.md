# Self Review

## Metadata
- name: self-review
- description: Meninjau output, file, dan rencana kerja agent untuk menemukan risiko, gap, dan perbaikan berikutnya
- aliases: [review, critique, audit]
- category: governance

## Description
Skill ini melakukan self-review heuristik terhadap output agent.

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
