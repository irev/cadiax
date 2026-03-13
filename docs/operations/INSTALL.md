# Install

Cadiax menyediakan installer awal untuk Windows dan Linux agar user tidak perlu menebak dependency dasar saat first install.

## Jalur Resmi

### Windows

```powershell
./install.ps1
```

Dengan dashboard dependency opsional:

```powershell
./install.ps1 -InstallNode
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

## Yang Dilakukan Installer

- memastikan `Python` tersedia
- memastikan `Git` tersedia
- opsional memastikan `Node.js` dan `npm` tersedia untuk dashboard
- membuat virtual environment `.venv`
- menjalankan `pip install .`
- opsional menjalankan `cadiax dashboard install`
- menjalankan `cadiax setup` kecuali diminta skip

## Catatan Tentang Output `pip`

`pip` memang selalu menampilkan format seperti:

```text
Successfully installed cadiax-1.1.1
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
.venv/bin/cadiax setup
```

Di Windows:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\cadiax.exe setup
```
