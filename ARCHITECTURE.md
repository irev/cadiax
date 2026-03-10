# Arsitektur OtonomAssist

## Gambaran Umum

OtonomAssist adalah asisten otonom modular yang mengeksekusi tugas berdasarkan skill yang didefinisikan dalam file markdown.

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Interface                          │
│                   (Command Line Input)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Core Assistant                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Skill Registry  │  │ Skill Loader    │  │ Executor    │  │
│  │                 │  │                 │  │             │  │
│  │ - List skills   │  │ - Parse .md     │  │ - Route cmd │  │
│  │ - Get skill     │  │ - Validate      │  │ - Execute   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Skills Directory                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ echo.md  │ │ help.md  │ │ calc.md  │ │ [skill_name].md│  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Komponen Utama

### 1. CLI Interface (`cli.py`)
- Menangani input dari pengguna
- Parsing perintah dan argument
- Menampilkan output ke pengguna

### 2. Core Assistant (`core/assistant.py`)
- Orchestrator utama
- Mengelola lifecycle asisten
- Menangani error dan recovery

### 3. Skill Registry (`core/skill_registry.py`)
- Database skill yang tersedia
- Mapping command ke skill handler
- Register/unregister skill dinamis

### 4. Skill Loader (`core/skill_loader.py`)
- Load skill dari file markdown
- Parse metadata skill
- Validasi format skill
- Hot-reload capability

### 5. Skill Definition (Markdown Format)
```markdown
# Skill Name

## Metadata
- name: echo
- description: Mengulang pesan yang diberikan
- aliases: [repeat, ulang]
- category: utility

## Triggers
- "echo <text>"
- "ulang <text>"

## Handler
```python
async def handle(args: str) -> str:
    return args
```

## Response Template
- Default: "{result}"
```

## Alur Eksekusi Command

```
User Input: "echo hello world"
        │
        ▼
┌───────────────────┐
│  CLI Parser       │
│  cmd="echo"       │
│  args="hello world│
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Skill Registry   │
│  Find handler for │
│  "echo"           │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Skill Loader     │
│  Load & validate  │
│  skill definition │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Execute Handler  │
│  Pass args to      │
│  handler function │
└────────┬──────────┘
         │
         ▼
    Output Response
```

## Teknologi yang Digunakan

- **Python 3.10+**: Bahasa pemrograman utama
- **Click**: CLI framework
- **PyYAML**: Parse skill metadata
- **Markdown**: Format dokumentasi skill

## Desain Pola

1. **Registry Pattern**: Untuk skill management
2. **Plugin Architecture**: Skill sebagai plugin independen
3. **Strategy Pattern**: Setiap skill adalah strategy berbeda
4. **Dependency Injection**: Untuk testability

## Keamanan

- Input sanitization sebelum eksekusi
- Timeout untuk setiap skill execution
- Error handling yang aman
- Logging untuk audit trail

## Extensibility

Untuk menambah skill baru:
1. Buat file `.md` di folder `skills/`
2. Definisikan metadata dan handler
3. Skill otomatis ter-register saat restart

## Pengembangan Future

- [ ] Telegram Bot Integration
- [ ] WhatsApp Integration  
- [ ] Web UI
- [ ] AI-powered natural language understanding
- [ ] Skill marketplace
