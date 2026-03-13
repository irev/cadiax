# AI Chat

## Metadata
- name: ai
- description: Chat umum dan reasoning fallback ketika tidak ada skill inti private AI yang lebih spesifik
- aliases: [chat, ask, gpt]
- category: capability
- autonomy_category: knowledge
- risk_level: low
- side_effects: []
- requires: [ai_provider]
- idempotency: best_effort

## Description
Skill ini adalah fallback untuk percakapan umum, reasoning terbuka, dan pertanyaan yang tidak cocok ke skill `memory`, `planner`, `workspace`, atau `self-review`.

## Purpose
- Menangani percakapan umum, brainstorming, klarifikasi, dan reasoning fallback saat tidak ada capability yang lebih spesifik.
- Menjadi entry point aman untuk interaksi yang belum perlu diubah menjadi aksi, memory, atau planning.

## Boundaries
- Gunakan untuk chat umum dan reasoning non-spesifik.
- Jangan gunakan bila intent user jelas mengarah ke `memory`, `planner`, `workspace`, `research`, `review`, atau capability lain yang lebih spesifik.
- Jangan mengklaim verifikasi fakta terbaru tanpa jalur `research`.
- Jangan menyimpan secret atau memori baru kecuali user memang mengalihkan ke capability yang tepat.

## Primary Inputs
- `ai <message>`
- `chat <message>`
- `ask <question>`

## Expected Outputs
- Jawaban percakapan yang relevan, jelas, dan sesuai context.
- Klarifikasi intent bila permintaan user ambigu.
- Pengalihan implisit atau rekomendasi ke capability lain bila dibutuhkan.

## State Touchpoints
- AI provider response.
- Personality and runtime context budget.
- Tidak seharusnya menulis state durable secara langsung kecuali jalur orchestration memutuskan sebaliknya.

## Failure Modes
- AI provider tidak tersedia.
- Prompt terlalu ambigu sehingga intent tidak jelas.
- User sebenarnya memerlukan verifikasi faktual atau tool capability lain.
- Context terlalu tipis atau budget terpotong sehingga jawaban kurang memadai.

## Success Criteria
- Percakapan umum terjawab tanpa salah memakai capability yang lebih tepat.
- Jawaban tetap jujur terhadap batas verifikasi dan tool availability.
- Skill dapat berfungsi sebagai fallback tanpa menutupi intent spesifik yang seharusnya dirutekan.
- Tidak ada side effect state yang tidak disengaja.

## Triggers
- ai 
- chat 
- ask 
- gpt 

## AI Instructions
Ketika user ingin chatting umum, brainstorming, atau bertanya sesuatu yang tidak butuh skill spesifik, gunakan skill ini.

Contoh:
- "halo" → `ai halo`
- "apa itu python" → `ai apa itu python?`
- "chat dengan saya" → `ai Hi, siap membantu Anda`

## Execution
Handler Python terletak di `script/handler.py`
