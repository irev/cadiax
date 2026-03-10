# Echo

## Metadata
- name: echo
- description: Mengulang pesan yang diberikan pengguna
- aliases: [repeat, ulang]
- category: utility

## Triggers
- echo 
- repeat 
- ulang 

## Handler
```python
def handle(args: str) -> str:
    if not args:
        return "Usage: echo <text>"
    return args
```
