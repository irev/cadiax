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
