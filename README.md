# OtonomAssist - Autonomous Assistant

Asisten otonom yang dapat melakukan tugas berdasarkan skill yang tersedia.

## 📋 Fitur Utama

- **CLI Interface**: Interaksi melalui command line
- **Skill System**: Skill didefinisikan dalam file markdown
- **AI Integration**: Mendukung OpenAI, Ollama, dan LM Studio
- **Extensible**: Tambah skill baru dengan mudah
- **Plugin Architecture**: Modular dan mudah dikembangkan

## 🚀 Cara Menggunakan

```bash
# Install dependencies
pip install -e .

# Jalankan asisten
python -m otonomassist

# Atau gunakan CLI command
otonomassist

# Single command
otonomassist "echo hello"
otonomassist "calc 10 + 5"
otonomassist "help"
```

## 🤖 AI Integration

OtonomAssist mendukung berbagai AI provider:

### Konfigurasi

Copy `.env.example` ke `.env` dan sesuaikan:

```bash
# AI Provider: openai, ollama, atau lmstudio
AI_PROVIDER=openai

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# LM Studio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model
```

### Menggunakan AI

```
> aiApa itu Python?
Python adalah bahasa pemrograman tingkat tinggi...
```

## 📁 Struktur Project

```
otonomAssist/
├── src/
│   └── otonomassist/
│       ├── __init__.py
│       ├── cli.py              # CLI interface
│       ├── ai/                  # AI providers
│       │   ├── base.py
│       │   ├── openai.py
│       │   ├── ollama.py
│       │   ├── lmstudio.py
│       │   └── factory.py
│       ├── core/
│       │   ├── assistant.py    # Core assistant logic
│       │   ├── skill_loader.py
│       │   └── skill_registry.py
│       └── models/
│           └── skill.py
├── skills/                      # Skill markdown files
│   ├── echo.md
│   ├── help.md
│   ├── calculator.md
│   └── ai-chat.md
├── tests/
├── pyproject.toml
└── README.md
```

## 💡 Contoh Penggunaan

```
> assistant: halo
Hello! Saya OtonomAssist. Ketik 'help' untuk melihat skill yang tersedia.

> assistant: help
Skill yang tersedia:
- ai: Chat dengan AI
- echo: Mengulang pesan
- help: Menampilkan daftar skill
- calculator: Kalkulator sederhana
```

## 🔧 Menambah Skill Baru

1. Buat file markdown di folder `skills/`
2. Ikuti format skill yang tersedia
3. Restart asisten - skill akan otomatis terdeteksi

Format skill:
```markdown
# Nama Skill

## Metadata
- name: nama-skill
- description: Deskripsi skill
- aliases: [alias1, alias2]
- category: utility

## Triggers
- trigger 

## Handler
```python
def handle(args: str) -> str:
    return f"Hasil: {args}"
```
```

## 📝 Lisensi

MIT
