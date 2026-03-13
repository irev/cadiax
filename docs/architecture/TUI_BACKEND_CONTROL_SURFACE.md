# Cadiax TUI Backend Control Surface

## Tujuan

Cadiax membutuhkan `operator surface` lokal yang lebih kaya dari CLI biasa, tetapi tetap lebih aman dan lebih langsung daripada dashboard web. Dokumen ini mendefinisikan `TUI backend/configuration surface` sebagai antarmuka utama untuk:

- first-run setup
- reconfigure
- service control
- provider and secret diagnostics
- workspace and path inspection
- privacy-safe operational audit

Web dashboard tetap dipertahankan sebagai `frontend observability` opsional, bukan pusat konfigurasi utama.

## Posisi TUI dalam Arsitektur

TUI berada di antara CLI dan service/config layer yang sudah ada.

```text
CLI / installer / service wrapper
        |
        v
TUI control surface
        |
        v
setup_wizard / config_doctor / path_layout / dashboard_runtime / service_runtime
        |
        v
durable config + state + workspace docs
```

Prinsipnya:

- TUI tidak menulis file konfigurasi mentah secara ad hoc
- TUI memanggil service/helper yang sama dengan `setup`, `doctor`, `dashboard`, dan `service`
- TUI harus menghormati `project mode` dan `user install mode`
- TUI harus aman dijalankan lokal di Windows dan Linux

## Pembagian Tanggung Jawab

### TUI

Menangani:

- wizard interaktif
- menu konfigurasi
- status service
- ringkasan provider dan secret
- path/runtime mode
- dashboard settings
- Telegram enable/disable
- health and doctor views

### Web Dashboard

Tetap fokus pada:

- monitoring
- metrics
- routing telemetry
- jobs/events/history
- runtime snapshot
- channel and notification observability

Dashboard tidak menjadi tempat utama untuk:

- setup credential
- perubahan path install
- perubahan workspace root
- keputusan install/reinstall/uninstall

## Layar Minimum

### 1. Home

Menampilkan:

- runtime mode: `project` atau `user`
- status health: `healthy / warning / critical`
- path ringkas:
  - config
  - state
  - workspace
  - dashboard
- provider aktif
- Telegram status
- dashboard status

### 2. First-Run Wizard

Menggantikan pengalaman `setup` berbasis pertanyaan linear menjadi wizard bertahap:

- provider
- model/base URL
- secret status
- workspace root
- dashboard enable/access/port/admin API URL
- Telegram enable/disable
- summary + confirm write

### 3. Paths and Runtime

Menampilkan layout aktif:

- `path_mode`
- app root
- config file
- state dir
- workspace root
- dashboard root
- command resolution

Harus bisa membedakan:

- shell command aktif benar
- shim lama/global conflict
- current shell perlu restart atau tidak

### 4. Providers and Secrets

Menampilkan:

- provider aktif
- daftar provider tersedia
- status secret:
  - available
  - missing
  - invalid/corrupt
- masked value preview
- issue list dari doctor

TUI tidak menampilkan plaintext secret.

### 5. Services

Mengelola:

- `cadiax` main service
- admin API
- conversation API
- dashboard

Catatan:

- Telegram bukan service utama terpisah
- Telegram ikut runtime `cadiax` utama dan hanya on/off via setting user

### 6. Dashboard Settings

Menampilkan dan mengubah:

- enabled
- access mode
- port
- admin API URL
- dependency/build status

### 7. Doctor and Audit

Menyajikan hasil `doctor` dalam bentuk:

- summary cards
- issue list
- sections:
  - storage
  - AI
  - Telegram
  - dashboard
  - privacy
  - routing
  - runtime

### 8. Install Lifecycle

Membantu operator menjalankan:

- install
- reinstall
- uninstall
- purge data

TUI tidak menggantikan script installer, tetapi menjadi control surface yang menjelaskan status runtime install dan langkah aman berikutnya.

## Entry Point yang Diinginkan

Target command publik:

```text
cadiax tui
```

Subcommand yang mungkin diperlukan:

- `cadiax tui`
- `cadiax tui doctor`
- `cadiax tui setup`

Tetapi fase awal cukup satu entrypoint `cadiax tui`.

## Teknologi yang Direkomendasikan

Pilihan terbaik untuk TUI Python modern adalah:

- `textual`
- `rich`

Alasan:

- layout modern
- widgets dan keyboard navigation matang
- cocok untuk forms, tables, panels, logs
- lintas Windows dan Linux

`uv` tidak dibutuhkan untuk kualitas TUI. `uv` hanya memengaruhi workflow dependency, bukan UI/UX.

## Batas Implementasi

TUI fase awal tidak perlu:

- terminal multiplexer complex views
- live chart berat
- edit markdown workspace secara penuh dari TUI
- menggantikan dashboard web
- menggantikan admin API

TUI harus fokus pada `control`, bukan `full document editor`.

## Dependency ke Sistem Saat Ini

TUI harus reuse komponen yang sudah ada:

- `src/cadiax/core/setup_wizard.py`
- `src/cadiax/core/config_doctor.py`
- `src/cadiax/core/path_layout.py`
- `src/cadiax/platform/dashboard_runtime.py`
- `src/cadiax/platform/service_runtime.py`
- `src/cadiax/core/secure_storage.py`

Jika helper yang ada terlalu CLI-oriented, refactor sebaiknya memindahkan logika ke service/helper netral, bukan menduplikasi logika di layer TUI.

## Fase Implementasi

### Phase T1: Foundation

- tambah dependency TUI
- tambah command `cadiax tui`
- buat app shell dengan sidebar dan routing layar
- tampilkan `Home`, `Paths`, `Doctor`

### Phase T2: Configuration

- pindahkan flow setup ke wizard layar bertahap
- provider and secret status
- dashboard settings
- Telegram settings

### Phase T3: Service Control

- tampilkan status service target
- jalankan action aman:
  - show
  - write wrapper
  - run foreground

### Phase T4: Hardening

- keyboard shortcuts
- empty/error state
- doctor issue drill-down
- regression test untuk TUI state model

## Acceptance Criteria

TUI dianggap siap baseline jika:

- `cadiax tui` berjalan di Windows dan Linux
- dapat membaca `project mode` dan `user install mode`
- dapat menampilkan `doctor` tanpa membocorkan secret
- dapat melakukan first-run setup tanpa edit file manual
- dapat mengonfigurasi dashboard dan Telegram settings
- tidak tergantung pada source checkout saat user install mode

## Risiko

- menggandakan logika setup jika helper tidak cukup reusable
- terlalu banyak aksi mutatif di TUI bisa memperbesar risiko konfigurasi rusak
- TUI yang mencoba merangkum terlalu banyak observability bisa tumpang tindih dengan dashboard

## Rekomendasi

Urutan paling tepat:

1. bangun shell TUI + screen model
2. reuse `paths` dan `doctor` lebih dulu
3. baru masukkan `setup` dan `dashboard settings`
4. terakhir tambahkan service control

Ini menjaga TUI tetap berguna sejak awal tanpa langsung menanggung seluruh kompleksitas runtime.
