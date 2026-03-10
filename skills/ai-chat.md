# AI Chat

## Metadata
- name: ai
- description: Chat dengan AI (mendukung OpenAI, Ollama, LM Studio)
- aliases: [chat, ask, gpt]
- category: ai

## Triggers
- ai 
- chat 
- ask 
- gpt 

## Handler
```python
async def handle(args: str) -> str:
    from otonomassist.ai.factory import AIProviderFactory
    
    if not args:
        return "Usage: ai <pertanyaan>\nContoh: ai Apa itu Python?"
    
    try:
        provider = AIProviderFactory.auto_detect()
        if not provider:
            return "Error: Tidak ada AI provider yang tersedia. Pastikan .env dikonfigurasi dengan benar."
        
        response = await provider.chat_completion(
            prompt=args,
            system_prompt="Anda adalah asisten yang membantu. Jawab dalam bahasa Indonesia kecuali diminta sebaliknya."
        )
        return response
    except Exception as e:
        return f"Error: {str(e)}"
```
