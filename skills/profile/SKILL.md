# Profile

## Metadata
- name: profile
- description: Mengelola profil personalisasi markdown untuk private AI, termasuk purpose, preferences, constraints, dan konteks jangka panjang
- aliases: [persona, personalize, identity]
- category: core

## Description
Skill ini mengelola file markdown personalisasi agent.

## Triggers
- profile
- persona
- personalize
- identity

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
