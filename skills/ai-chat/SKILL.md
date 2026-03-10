# AI Chat

## Metadata
- name: ai
- description: Chat dengan AI (mendukung OpenAI, Anthropic, Ollama, LM Studio)
- aliases: [chat, ask, gpt]
- category: ai

## Description
Skill ini memungkinkan asisten untuk berkomunikasi dengan berbagai AI providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Ollama (local models)
- LM Studio (local models)

## Triggers
- ai 
- chat 
- ask 
- gpt 

## AI Instructions
Ketika user ingin chatting dengan AI atau bertanya sesuatu, gunakan skill ini.

Contoh:
- "halo" → `ai halo`
- "apa itu python" → `ai apa itu python?`
- "chat dengan saya" → `ai Hi, siap membantu Anda`

## Execution
Handler Python terletak di `script/handler.py`
