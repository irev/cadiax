# Memory

## Metadata
- name: memory
- description: Menyimpan, mencari, merangkum, dan mengambil memori kerja lokal untuk agent private AI
- aliases: [remember, mem, ingat]
- category: core
- autonomy_category: memory
- risk_level: medium
- side_effects: [memory_write, lessons_write]
- requires: []
- idempotency: mixed

## Description
Skill ini mengelola memori kerja lokal agent.

## Triggers
- memory
- remember
- mem
- ingat

## AI Instructions
Gunakan skill ini ketika user ingin:
- menyimpan fakta, keputusan, atau konteks penting
- mencari memori yang pernah disimpan
- melihat ringkasan memori kerja
- mengkonsolidasikan pelajaran ke knowledge markdown

Contoh:
- "ingat bahwa proyek ini fokus ke private ai" -> `memory add proyek ini fokus ke private ai`
- "cari memori tentang planner" -> `memory search planner`
- "ringkas memori aktif" -> `memory summarize`
- "konsolidasikan pelajaran terbaru" -> `memory consolidate`

## Execution
Handler Python terletak di `script/handler.py`
