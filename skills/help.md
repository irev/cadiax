# Help

## Metadata
- name: help
- description: Menampilkan daftar semua skill yang tersedia
- aliases: [?, bantuan]
- category: system

## Triggers
- "help"

## Handler
```python
def handle(args: str) -> str:
    # This is handled by the assistant's get_help method
    return "Use 'list' command to see all skills"
```
