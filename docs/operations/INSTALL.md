# Install

Cadiax menyediakan lifecycle installer yang tegas untuk Windows dan Linux agar user tidak perlu menebak dependency dasar maupun konsekuensi install ulang.

## Mode Installer

- `install`
  - untuk first install
  - jika runtime sudah ada, installer akan meminta konfirmasi untuk lanjut sebagai `reinstall`
- `reinstall`
  - untuk memperbarui atau membangun ulang runtime aplikasi
  - default tetap mempertahankan config, state, dan workspace user
- `uninstall`
  - menghapus runtime aplikasi dan command shim
  - default tetap mempertahankan config, state, dan workspace user
  - gunakan purge jika ingin menghapus semuanya

## Jalur Resmi

Installer Cadiax sekarang melakukan **user install**. Artinya runtime aplikasi tidak hidup di folder git/source yang didownload user.
Source checkout hanya dipakai sebagai bahan install, lalu executable Cadiax berjalan dari direktori aplikasi native OS.

### Windows

```powershell
./install.ps1 -Mode install
```

Atau dari `cmd` / double-click:

```bat
install.bat -Mode install
```

Dengan dashboard dependency opsional:

```powershell
./install.ps1 -InstallNode
```

Atau:

```bat
install.bat -InstallNode
```

### Linux

```bash
chmod +x ./install.sh
./install.sh --mode install
```

Dengan dashboard dependency opsional:

```bash
chmod +x ./install.sh
./install.sh --install-node
```

Untuk install ulang:

```powershell
./install.ps1 -Mode reinstall
```

atau:

```bash
./install.sh --mode reinstall
```

Jika Anda memang ingin memakai virtual environment yang sama tanpa dihapus saat reinstall, gunakan:

```powershell
./install.ps1 -ReuseVenv
```

atau:

```bash
./install.sh --reuse-venv
```

Untuk uninstall runtime aplikasi:

```powershell
./install.ps1 -Mode uninstall
```

atau:

```bash
./install.sh --mode uninstall
```

Jika ingin sekaligus menghapus config, state, dan workspace:

```powershell
./install.ps1 -Mode uninstall -PurgeData
```

atau:

```bash
./install.sh --mode uninstall --purge-data
```

Secara default installer juga akan mendaftarkan command user-level:

- Windows: `%USERPROFILE%\.cadiax\bin\cadiax.cmd`
- Linux: `~/.local/bin/cadiax`

Di Windows installer juga akan menulis shim PowerShell ke profile user agar command `cadiax` di PowerShell tidak kalah oleh command global lama seperti `pyenv`.

Jika Anda tidak menginginkan itu:

```powershell
./install.ps1 -SkipUserShim
```

atau:

```bash
./install.sh --skip-user-shim
```

Untuk Windows PowerShell, Anda juga bisa menonaktifkan profile shim:

```powershell
./install.ps1 -SkipPowerShellProfileShim
```

## Yang Dilakukan Installer

- menjalankan preflight dependency check di awal sebelum runtime install dimulai
- memastikan `Python` tersedia
- memastikan versi `Python >= 3.10`
- memastikan `venv/ensurepip` benar-benar tersedia, bukan hanya command `python` yang ada
- memastikan `Git` tersedia
- opsional memastikan `Node.js` dan `npm` tersedia untuk dashboard
- membuat runtime aplikasi di direktori install native OS:
  - Windows: `%LOCALAPPDATA%\Cadiax\app\`
  - Linux: `~/.local/share/cadiax/app/`
- menempatkan monitoring dashboard opsional di dalam runtime aplikasi native OS:
  - Windows: `%LOCALAPPDATA%\Cadiax\app\monitoring-dashboard\`
  - Linux: `~/.local/share/cadiax/app/monitoring-dashboard/`
- membuat virtual environment di dalam direktori aplikasi itu:
  - Windows: `%LOCALAPPDATA%\Cadiax\app\venv\`
  - Linux: `~/.local/share/cadiax/app/venv/`
- menjalankan install package Cadiax ke virtual environment aplikasi
- menyalin asset dashboard opsional ke direktori aplikasi bila tersedia
- menyiapkan layout native per-OS untuk user install:
  - Windows:
    - config: `%APPDATA%\Cadiax\config.env`
    - state: `%LOCALAPPDATA%\Cadiax\state\`
    - workspace: `%USERPROFILE%\Cadiax\workspace\`
    - dashboard: `%LOCALAPPDATA%\Cadiax\app\monitoring-dashboard\`
  - Linux:
    - config: `~/.config/cadiax/config.env`
    - state: `~/.local/state/cadiax/`
    - workspace: `~/cadiax/workspace/`
    - dashboard: `~/.local/share/cadiax/app/monitoring-dashboard/`
- men-seed dokumen workspace aktif ke workspace root:
  - `AGENTS.md`
  - `SOUL.md`
  - `USER.md`
  - `IDENTITY.md`
  - `TOOLS.md`
  - `HEARTBEAT.md`
- opsional menjalankan `cadiax dashboard install`
- menjalankan `cadiax setup` (TUI setup) kecuali diminta skip

Saat `cadiax setup` dijalankan dari installer, TUI setup awal juga akan menawarkan konfigurasi monitoring dashboard:
- aktif atau tidak
- access mode `local` atau `public`
- port dashboard
- `admin API URL` yang dipakai dashboard

Jika Anda membutuhkan wizard prompt lama untuk reconfigure non-TUI, gunakan:

```bash
cadiax setup --classic
```

Dokumen bootstrap aktif selalu disalin ke `workspace root`, bukan ke `.cadiax/`.
Setelah setup selesai, dokumen inilah yang benar-benar dibaca Cadiax untuk startup context, identity, soul, scope, dan heartbeat behavior.

Sesudah install selesai, folder source/git yang dipakai untuk install tidak lagi menjadi dependency runtime utama Cadiax.

Di Linux, jika installer dijalankan dari shell non-interaktif dan butuh `sudo` untuk memasang dependency seperti `python3-venv`, installer sekarang akan berhenti dengan pesan yang jelas, bukan hang di tengah proses.

Pada `project mode` untuk contributor, default path tetap repo-relative:

- config: `.env`
- state: `.cadiax/`
- workspace: `workspace/`

## Service Runtime

Untuk deployment Windows/Linux, target service yang direkomendasikan sekarang adalah:

```bash
cadiax service run cadiax
```

Target ini menjalankan runtime utama Cadiax dan akan mengaktifkan Telegram polling dalam service yang sama bila `TELEGRAM_ENABLED=true`.
Jika `TELEGRAM_ENABLED=false`, service tetap berjalan tanpa Telegram.

## Setelah Install

Pada install berbasis virtual environment, command `cadiax` global di shell Anda bisa saja masih menunjuk ke executable lama atau shim Python global.

Gunakan command berikut untuk memeriksa layout runtime aktif:

```bash
cadiax paths
```

Interpretasinya:
- `project mode`: Anda sedang menjalankan Cadiax dari checkout repo/source
- `user install mode`: Anda sedang menjalankan Cadiax dari layout native OS hasil installer

Jalur yang benar setelah install:

### Windows

```powershell
$env:LOCALAPPDATA\Cadiax\app\venv\Scripts\cadiax.exe
```

Atau aktifkan dulu:

```powershell
& "$env:LOCALAPPDATA\Cadiax\app\venv\Scripts\Activate.ps1"
cadiax
```

### Linux

```bash
~/.local/share/cadiax/app/venv/bin/cadiax
```

Atau aktifkan dulu:

```bash
source ~/.local/share/cadiax/app/venv/bin/activate
cadiax
```

Cadiax installer sekarang juga membuat shim user-level agar command `cadiax` lebih mudah dipakai tanpa harus selalu mengetik path `.venv`.

Jika shell yang sedang terbuka masih memakai instalasi global lama, tutup lalu buka shell baru setelah install selesai.

Di Windows, jika konflik berasal dari `pyenv` atau Python global lama, remedi terbaik adalah:

```powershell
pyenv which python
<python> -m pip uninstall -y cadiax autonomiq otonomassist
pyenv rehash
```

## Catatan Tentang Output `pip`

`pip` memang selalu menampilkan format seperti:

```text
Successfully installed cadiax-<version>
```

Itu perilaku standar `pip`, bukan nama aplikasi yang salah.
Untuk itu installer Cadiax selalu menutup proses dengan pesan yang lebih bersih:

```text
Cadiax installed
```

## Mode Manual

Kalau user tidak ingin memakai installer:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
.venv/bin/cadiax bootstrap foundation
.venv/bin/cadiax setup
```

Di Windows:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\cadiax.exe bootstrap foundation
.venv\Scripts\cadiax.exe setup
```

## Tentang Workspace Docs

Cadiax membedakan dua area:

- `.cadiax/` untuk internal state mesin
- `workspace root` untuk dokumen kerja yang bisa diedit user

Dokumen berikut adalah dokumen runtime aktif:

- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `IDENTITY.md`
- `TOOLS.md`
- `HEARTBEAT.md`

User boleh mengedit dokumen ini secara manual setelah install atau setup.
Cadiax memang dirancang untuk membaca hasil edit tersebut pada runtime berikutnya.

Jika ingin men-seed template tambahan seperti `BOOTSTRAP.md` atau file `*.dev.md`, gunakan:

```bash
cadiax bootstrap foundation --include-optional
```
