# Skill Format Specification

Dokumentasi format untuk membuat skill baru dalam bentuk file markdown.

## Struktur File

```markdown
# Nama Skill

## Metadata
- name: [nama skill]
- description: [deskripsi singkat]
- aliases: [alias1, alias2]
- category: [kategori]

## Triggers
- "trigger1 "
- "trigger2 "

## Handler
```python
def handle(args: str) -> str:
    # Kode handler
    return hasil
```
```

## Contoh Skill Lengkap

```markdown
# Reminder

## Metadata
- name: reminder
- description: Membuat pengingat tugas
- aliases: [remind, ingat]
- category: productivity

## Triggers
- "reminder "
- "remind "
- "ingat "

## Handler
```python
def handle(args: str) -> str:
    parts = args.split("|")
    if len(parts) < 2:
        return "Format: reminder <waktu> | <tugas>\nContoh: reminder 1 jam | belikan kopi"
    
    waktu = parts[0].strip()
    tugas = parts[1].strip()
    
    return f"Pengingat dibuat: '{tugas}' pada {waktu}"
```
```

## Panduan Membuat Skill

### 1. Metadata
- **name**: Nama unik skill (wajib)
- **description**: Penjelasan singkat (wajib)
- **aliases**: Nama alternatif yang bisa dipakai (opsional)
- **category**: Kategori skill (opsional, default: "general")

### 2. Triggers
- Pola yang memicu skill dijalankan
- Supports prefix matching (menggunakan spasi setelah trigger)
- Args akan diberikan ke handler function
- Jangan gunakan tanda kutip

### 3. Handler
- Kode Python yang dijalankan
- Menerima satu parameter: `args` (string)
- Wajib mengembalikan string

## Catatan Penting

1. **Trigger tanpa tanda kutip**: Gunakan `echo ` bukan `"echo "`
2. **Spasi penting**: Trigger harus memiliki spasi di akhir untuk prefix matching
3. **Nama file**: Nama file .md akan digunakan sebagai fallback jika name tidak ada

## Daftar Skill yang Tersedia

Lihat folder `skills/` untuk melihat skill yang sudah ada.
