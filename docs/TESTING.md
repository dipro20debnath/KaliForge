# KaliForge — Real Kali Integration Testing (step by step)

This guide walks you through running KaliForge on an **actual Kali Linux**
machine and exercising every major feature end-to-end with real tools, in a
safe, isolated lab.

> ⚠️ **Authorised use only.** Do every test against **your own lab VMs** (an
> isolated host-only network) or targets you are explicitly authorised to test.
> Never point the lab-only tools at systems you don't own.

---

## 0. What you need

- Kali Linux (bare metal, VM, WSL2, or a Kali Docker image) — 64-bit.
- Python 3.9+ (Kali ships it) and `pip`.
- For the lab targets: **VirtualBox** or **Docker**.
- ~4 GB free disk for the vulnerable lab images.

---

## 1. Get the code onto Kali

```bash
# in a terminal on Kali
cd ~
git clone https://github.com/dipro20debnath/KaliForge.git
cd KaliForge
git checkout ccr-fbbcc15d-trtys4     # the branch with all the work
```

## 2. Install dependencies

```bash
sudo apt update
# Qt runtime libs (usually already on Kali desktop):
sudo apt install -y python3-pip libegl1 libxkbcommon0 libfontconfig1

# Python packages (use a venv to avoid PEP-668 "externally managed" errors):
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt     # PySide6, psutil, pyte, reportlab, cryptography, keyring
```

> If you prefer system-wide: `pip install --break-system-packages -r requirements.txt`.

## 3. First launch (sanity check)

```bash
python3 main.py
```

You should see the dark **Dashboard**. Check:
- **Tools Available** shows ~106, **Installed** reflects what's really on your
  Kali (nmap, dirb, etc.). On Kali this number will be much higher than in the
  cloud build.
- Open **Tool Arsenal** → tools you have installed show **● Installed** with a
  real path; click **Details → Probe installed version** to confirm versions.

If the window doesn't appear: see **Troubleshooting** at the bottom.

## 4. Build a safe lab

Pick **one** (Docker is fastest):

### Option A — Docker vulnerable targets (built in)
KaliForge has a **Lab Environments** page that does this for you:
```bash
sudo apt install -y docker.io
sudo systemctl start docker
sudo usermod -aG docker $USER      # then log out / back in
```
In KaliForge → **Lab Environments** → click **Start** on *OWASP Juice Shop*
(or DVWA). Wait, then click **Open** → it loads `http://127.0.0.1:3000`.
Click **→ Scope** to authorise it.

### Option B — VirtualBox target VM
Import a deliberately-vulnerable VM (e.g. **Metasploitable 2/3**, **DVWA VM**)
on a **Host-Only** adapter (e.g. `192.168.56.0/24`). Note its IP
(`ip a` inside the VM). Add it under **Scope Manager** and **Evidence & Labs**.

## 5. Define your scope first (important)

KaliForge blocks lab-only tools against anything not in scope.
- Go to **Scope Manager** → add your lab target(s):
  - `192.168.56.0/24` (your host-only network), or
  - `127.0.0.1:3000` / `http://127.0.0.1:3000` for the Docker lab.
- Use the **Check** box to confirm a target is in scope.

## 6. End-to-end feature tests

Run these in order; each should now use **real** tools.

### 6.1 Terminal (Command Center)
- Open **Command Center**, type `whoami`, `ip a`, `nmap --version` → real output.
- Try **＋ Tab**, **⬌ Split**, **⏺ Record**, **💾 Save** / **↺ Restore**.

### 6.2 Tool launch with guard-rails
- **Tool Arsenal → Nmap → Details → Build & Run** → template
  `nmap -sV -sC {target}` → fill `target` = your lab IP → **Run**.
- Because the target is in scope it runs; the command appears in the terminal
  and in the **audit log**. Try an **out-of-scope** IP to see it **blocked**.

### 6.3 Workflows
- **Workflows → Reconnaissance** (or *Network Audit*) → set inputs to your lab →
  **Run workflow**. Watch each step (whois/dig/nmap) complete; output is written
  to `~/KaliForge/workspaces/<name>/output/`.

### 6.4 Scan Import → Findings / Hosts / Attack Surface
```bash
# in the Command Center or a shell:
nmap -sV -oX scan.xml 192.168.56.101
```
- **Scan Import** → **Load file… → scan.xml** → **Parse** → **Import to workspace**.
- Check **Vulnerability → Findings**, **Hosts**, and **Attack Surface** — all
  populated from the real scan.

### 6.5 Vulnerability + CVE intel
- **Vulnerability → CVE Intelligence** → look up `CVE-2021-44228` (needs
  internet) → NVD + EPSS + CISA KEV results; it's saved as a finding.

### 6.6 Crypto Toolkit / Payloads (offline)
- **Crypto Toolkit** → Base64/Hex encode-decode; paste a hash to identify it.
- **Payloads** → set LHOST/LPORT, pick *Bash /dev/tcp*; start the **Netcat
  listener** in the terminal, fire the shell from your lab VM, confirm callback.

### 6.7 Password / Wireless / Forensics (real tools)
- **Password**: on an authorised target, run the *Password Audit* workflow
  (hydra) against your lab SSH.
- **Wireless**: only on **your own** adapter/network — *Wireless Survey* workflow
  (airmon-ng/airodump-ng); needs a monitor-mode-capable card and `sudo`.
- **Forensics**: run *Forensics Triage* on a sample file (exiftool/binwalk/strings).

### 6.8 Evidence, Credentials, Reports
- **Evidence & Labs** → add a screenshot/pcap → it's hashed (SHA-256); click
  **Verify integrity**.
- **Credentials** → add any creds you find (stored encrypted).
- **Reports** → fill title/summary → **Export… → PDF/HTML** (tick *Embed
  evidence*) → open the file.

### 6.9 Workspaces backup
- **Workspaces → Export** → saves a `.kfw`; **Import** it back → a new workspace
  with the same findings/scope/evidence.

## 7. Package & install (optional)

```bash
bash packaging/deb/build_deb.sh 1.4.2
sudo dpkg -i kaliforge_1.4.2_all.deb
# then launch from the menu, or:
kaliforge
```

## 8. Run the test suite on Kali

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest
# expect: 77 passed
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install` → "externally-managed-environment" | use a `venv` (step 2) or `--break-system-packages` |
| Window doesn't open / Qt plugin error | `sudo apt install -y libegl1 libxkbcommon0 libfontconfig1 libdbus-1-3`; for headless use `QT_QPA_PLATFORM=offscreen` |
| A tool shows **Missing** that you have | its binary name differs — check **Install Manager**, or add it via **Plugins → Custom Tool Import** with the right `binary` |
| Lab-only tool refuses to run | add the target to **Scope Manager** (or set Settings → Security → scope mode to *Warn*) |
| Docker labs won't start | `sudo systemctl start docker`; ensure your user is in the `docker` group |
| CVE lookup / feeds empty | needs internet access; corporate proxies may block NVD/CISA |
| Running as root warning | KaliForge is designed to run as a normal user; enable *Allow launching as root* in Settings only if you must |

---

## Safe-testing checklist

- [ ] Targets are **my own lab** or explicitly authorised
- [ ] Lab is on an **isolated** (host-only / NAT) network
- [ ] Scope is defined **before** running any lab-only tool
- [ ] Running as a **normal user**, sudo only when prompted
- [ ] Audit log reviewed after the session (`~/.local/share/kaliforge/logs/audit.jsonl`)
