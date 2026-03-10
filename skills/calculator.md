# Calculator

## Metadata
- name: calc
- description: Kalkulator sederhana untuk operasi matematika dasar
- aliases: [calculator, hitung]
- category: utility

## Triggers
- calc 
- calculator 
- hitung 

## Handler
```python
def handle(args: str) -> str:
    import operator
    
    ops = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        'x': operator.mul,
    }
    
    args = args.strip()
    if not args:
        return "Usage: calc <angka1> <operator> <angka2>\nContoh: calc 10 + 5"
    
    parts = args.split()
    if len(parts) != 3:
        return "Format salah. Contoh: calc 10 + 5"
    
    try:
        a = float(parts[0])
        op = parts[1]
        b = float(parts[2])
        
        if op not in ops:
            return f"Operator tidak valid: {op}. Gunakan: + - * /"
        
        if op == '/' and b == 0:
            return "Error: Pembagian dengan nol"
        
        result = ops[op](a, b)
        return f"{a} {op} {b} = {result}"
        
    except ValueError:
        return "Error: Input harus angka"
    except Exception as e:
        return f"Error: {str(e)}"
```
