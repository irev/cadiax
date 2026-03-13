# Skill Format Specification

Dokumentasi ini menjelaskan format skill yang digunakan oleh Cadiax saat ini.

Format utama bukan lagi satu file markdown yang berisi kode handler. Format aktual adalah direktori skill yang berisi metadata markdown dan file Python handler terpisah.

## Struktur Skill

Setiap skill disimpan dalam folder sendiri:

```text
skills/
  <skill_name>/
    SKILL.md
    script/
      handler.py
```

Contoh:

```text
skills/echo/
├── SKILL.md
└── script/
    └── handler.py
```

## Struktur `SKILL.md`

`SKILL.md` berisi metadata, trigger, dan instruksi untuk AI routing.

Contoh minimal:

```markdown
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

## AI Instructions
Gunakan skill ini ketika user ingin pesannya diulang.
```

## Struktur `script/handler.py`

Handler harus menyediakan fungsi `handle(args: str)`.

Contoh:

```python
def handle(args: str) -> str:
    if not args:
        return "Usage: echo <text>"
    return args
```

Async handler juga didukung:

```python
async def handle(args: str) -> str:
    return f"Hasil async: {args}"
```

Handler juga boleh mengembalikan structured result envelope (`dict`) bila skill ingin mendukung formatter universal.

Saat ini runtime `Assistant` akan lebih stabil jika skill baru memisahkan:

- produksi data hasil
- presentasi hasil ke user

Artinya, untuk skill baru yang bukan sekadar echo/string sederhana, envelope result sebaiknya dianggap default, bukan tambahan opsional belaka.

## Structured Result Envelope

Untuk skill yang ingin mendukung tampilan universal seperti `table`, `summary`, `short`, `markdown`, atau `json`, handler sebaiknya mengembalikan envelope berikut:

```python
{
    "type": "my_skill_result",
    "status": "ok",
    "data": {...},
    "meta": {
        "source_skill": "my-skill",
        "default_view": "summary",
    },
}
```

Cara yang direkomendasikan adalah memakai helper core:

```python
from otonomassist.core.result_builder import build_result


def handle(args: str):
    return build_result(
        "my_skill_result",
        {
            "summary": "Ringkasan hasil",
            "items": [{"name": "contoh"}],
        },
        source_skill="my-skill",
        default_view="summary",
    )
```

Prinsip desain:

- `type` menjelaskan jenis hasil domain
- `status` biasanya `ok` atau `degraded`
- `data` berisi payload utama
- `meta.source_skill` wajib diisi
- `meta.default_view` menentukan tampilan bawaan jika user tidak meminta format tertentu

Jika skill hanya butuh output sederhana, return string tetap valid. Envelope direkomendasikan khususnya untuk skill yang:

- mengembalikan list
- mengembalikan hasil pencarian
- mengembalikan summary data
- berpotensi ditampilkan dalam beberapa view

Selain itu, skill yang dipakai dalam loop otonom atau transport eksternal sebaiknya memakai envelope karena:

- lebih mudah diuji
- lebih stabil untuk automation chaining
- lebih mudah dirender ulang di CLI/Telegram
- lebih mudah diberi metadata status/verifikasi

## Praktik yang Disarankan untuk Skill Baru

Gunakan `build_result(...)` untuk response terstruktur.

Pisahkan:

- parsing args
- eksekusi domain logic
- penyusunan payload data
- pemilihan `default_view`

Hindari menanam renderer tabel/markdown manual di dalam skill jika formatter universal sudah cukup.

Jika skill tetap menulis side effect seperti memory/planner/lessons:

- laporkan side effect itu di `data`
- jangan campur side effect dengan string presentasi acak
- pertimbangkan field seperti `persistence`, `follow_up`, atau `verification_status`

## Section yang Diparse Loader

Loader saat ini membaca section berikut dari `SKILL.md`:

### 1. `## Metadata`

Field yang didukung:

- `name`: nama skill runtime
- `description`: deskripsi singkat skill
- `aliases`: daftar alias dalam format `[a, b, c]`
- `category`: kategori skill
- `autonomy_category`: kategori skill-layer otonom
- `risk_level`: level risiko `low|medium|high|critical`
- `side_effects`: daftar efek samping seperti `memory_write`, `planner_write`, `network_access`
- `requires`: dependency logis seperti `ai_provider`, `workspace_access`, `secure_storage`
- `idempotency`: `idempotent|best_effort|mixed|non_idempotent`

Contoh:

```markdown
## Metadata
- name: calc
- description: Kalkulator sederhana
- aliases: [calculator, hitung]
- category: utility
- autonomy_category: knowledge
- risk_level: low
- side_effects: []
- requires: []
- idempotency: idempotent
```

Taxonomy `autonomy_category` yang direkomendasikan:

- `planning`
- `memory`
- `knowledge`
- `environment`
- `execution`
- `governance`

Tujuannya adalah memberi sinyal ke orchestrator tentang peran skill dalam loop agent, bukan hanya kategori umum UI/dokumentasi.

### 2. `## Triggers`

Setiap baris trigger diawali `- `.

Contoh:

```markdown
## Triggers
- calc
- calculator
- hitung
```

Trigger dipakai untuk prefix matching. Args akan diambil dari sisa input setelah trigger yang cocok.

Contoh:

- Trigger: `calc`
- Input: `calc 10 + 5`
- Args yang dikirim ke handler: `10 + 5`

### 3. `## AI Instructions`

Section ini dipakai sebagai konteks tambahan untuk AI orchestration.

Contoh:

```markdown
## AI Instructions
Gunakan skill ini ketika user meminta perhitungan matematika sederhana.

Contoh:
- "10 + 5" -> `calc 10 + 5`
- "berapa 20 dibagi 4" -> `calc 20 / 4`
```

## Contoh Skill Lengkap

### `SKILL.md`

```markdown
# Reminder

## Metadata
- name: reminder
- description: Membuat pengingat tugas
- aliases: [remind, ingat]
- category: productivity

## Description
Skill ini membuat pengingat berbasis input teks.

## Triggers
- reminder
- remind
- ingat

## AI Instructions
Gunakan skill ini ketika user ingin membuat pengingat.

Contoh:
- "ingatkan saya meeting jam 3" -> `reminder meeting jam 3`
```

### `script/handler.py`

```python
def handle(args: str) -> str:
    if not args:
        return "Usage: reminder <pesan>"

    return f"Pengingat dibuat: {args}"
```

## Aturan Penting

1. Nama folder skill tidak harus sama dengan `name`, tetapi sebaiknya tetap konsisten agar mudah dipelihara.
2. Loader mencari file `SKILL.md` di dalam folder skill.
3. Loader mencari handler di `script/handler.py`.
4. Fungsi `handle` wajib ada dan callable.
5. Return value handler boleh string atau structured result envelope.
6. Trigger tidak wajib memakai tanda kutip.
7. Trigger biasanya ditulis tanpa placeholder seperti `<text>` karena loader hanya melakukan prefix matching sederhana.
8. Untuk skill baru yang bersifat read-heavy atau data-heavy, lebih baik gunakan `build_result(...)` daripada string mentah.

## Catatan Tentang Parsing

Implementasi loader saat ini:

- mem-parse markdown dengan pendekatan sederhana berbasis baris
- tidak memakai parser markdown penuh
- mendukung fallback untuk format legacy `.md` flat

Artinya:

- heading harus ditulis persis seperti `## Metadata`, `## Triggers`, dan `## AI Instructions`
- field metadata harus diawali `- `
- format alias terbaik adalah `[alias1, alias2]`

## Legacy Format

Project masih memiliki fallback untuk format lama berupa satu file markdown yang mengandung code block Python. Namun format ini hanya dipertahankan untuk kompatibilitas dan tidak direkomendasikan untuk skill baru.

Gunakan format direktori:

```text
skills/<skill_name>/SKILL.md
skills/<skill_name>/script/handler.py
```

## Checklist Skill Baru

Sebelum menambahkan skill baru, pastikan:

- folder skill dibuat di dalam `skills/`
- `SKILL.md` ada
- `script/handler.py` ada
- metadata `name` dan `description` terisi
- trigger sudah didefinisikan
- fungsi `handle(args: str)` tersedia
- contoh penggunaan di `AI Instructions` cukup jelas untuk AI router
- jika skill menghasilkan data/list/search result, pertimbangkan memakai structured result envelope
- set `default_view` yang masuk akal, misalnya `summary` atau `table`
- jika skill punya side effect, buat payload yang menjelaskan side effect itu secara eksplisit
- jika skill akan dipakai di loop otonom, pikirkan stabilitas output lebih dulu daripada gaya string bebas
- hindari mengasumsikan credential ada di `.env`; gunakan runtime helper env-or-secret bila perlu
- isi metadata `autonomy_category`, `risk_level`, `side_effects`, `requires`, dan `idempotency` bila skill akan ikut dipakai oleh planner/orchestrator

## Referensi

- Contoh implementasi: `skills/echo/`, `skills/calculator/`, `skills/ai-chat/`
- Contoh structured result: `skills/research/`, `skills/workspace/`, `skills/planner/`, `skills/memory/`, `skills/self-review/`
- Helper result: `src/cadiax/core/result_builder.py`
- Formatter universal: `src/cadiax/core/result_formatter.py`
- Arsitektur runtime: `docs/architecture/ARCHITECTURE.md`
