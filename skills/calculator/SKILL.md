# Calculator

## Metadata
- name: calc
- description: Kalkulator sederhana untuk operasi matematika dasar
- aliases: [calculator, hitung]
- category: utility

## Description
Skill ini melakukan operasi matematika dasar:
- Penjumlahan (+)
- Pengurangan (-)
- Perkalian (* atau x)
- Pembagian (/)

## Triggers
- calc 
- calculator 
- hitung 

## AI Instructions
Ketika user ingin menghitung, gunakan skill ini dengan format: `calc <angka1> <operator> <angka2>`

Contoh:
- "10 + 5" → `calc 10 + 5`
- "100 - 30" → `calc 100 - 30`
- "5 x 5" → `calc 5 * 5`
- "20 / 4" → `calc 20 / 4`

## Execution
Handler Python terletak di `script/handler.py`
