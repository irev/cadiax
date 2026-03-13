# Install

Cadiax menyediakan installer awal untuk Windows dan Linux agar user tidak perlu menebak dependency dasar saat first install.

## Jalur Resmi

### Windows

```powershell
./install.ps1
```

Atau dari `cmd` / double-click:

```bat
install.bat
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
./install.sh
```

Dengan dashboard dependency opsional:

```bash
chmod +x ./install.sh
./install.sh --install-node
```

Secara default installer akan merecreate virtual environment target jika foldernya sudah ada. Jika Anda memang ingin memakai virtual environment yang sama tanpa dihapus, gunakan:

```powershell
./install.ps1 -ReuseVenv
```

atau:

```bash
./install.sh --reuse-venv
```

Secara default installer juga akan mendaftarkan command user-level:

- Windows: `%USERPROFILE%\.cadiax\bin\cadiax.cmd`
- Linux: `~/.local/bin/cadiax`

Jika Anda tidak menginginkan itu:

```powershell
./install.ps1 -SkipUserShim
```

atau:

```bash
./install.sh --skip-user-shim
```

## Yang Dilakukan Installer

- memastikan `Python` tersedia
- memastikan `Git` tersedia
- opsional memastikan `Node.js` dan `npm` tersedia untuk dashboard
- membuat virtual environment `.venv`
- menjalankan `pip install .`
- men-seed dokumen workspace aktif ke workspace root:
  - `AGENTS.md`
  - `SOUL.md`
  - `USER.md`
  - `IDENTITY.md`
  - `TOOLS.md`
  - `HEARTBEAT.md`
- opsional menjalankan `cadiax dashboard install`
- menjalankan `cadiax setup` kecuali diminta skip

Dokumen bootstrap aktif selalu disalin ke `workspace root`, bukan ke `.cadiax/`.
Setelah setup selesai, dokumen inilah yang benar-benar dibaca Cadiax untuk startup context, identity, soul, scope, dan heartbeat behavior.

## Setelah Install

Pada install berbasis virtual environment, command `cadiax` global di shell Anda bisa saja masih menunjuk ke executable lama atau shim Python global.

Jalur yang benar setelah install:

### Windows

```powershell
.venv\Scripts\cadiax.exe
```

Atau aktifkan dulu:

```powershell
.\.venv\Scripts\Activate.ps1
cadiax
```

### Linux

```bash
.venv/bin/cadiax
```

Atau aktifkan dulu:

```bash
source .venv/bin/activate
cadiax
```

Cadiax installer sekarang juga membuat shim user-level agar command `cadiax` lebih mudah dipakai tanpa harus selalu mengetik path `.venv`.

Jika shell yang sedang terbuka masih memakai instalasi global lama, tutup lalu buka shell baru setelah install selesai.

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
