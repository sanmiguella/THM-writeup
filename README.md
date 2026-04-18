# 🔐 TryHackMe Writeups

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Boxes](https://img.shields.io/badge/Boxes-25-blueviolet?style=for-the-badge)]()
[![Focus](https://img.shields.io/badge/Focus-Realistic_Chains-informational?style=for-the-badge)]()

Writeups for TryHackMe rooms. Emphasis on methodology, realistic attack chains, and understanding the *why* behind each step — not just dumping commands. Written as personal reference between professional engagements.

Each writeup covers: enumeration → initial access → privilege escalation, with an ASCII attack chain diagram, key takeaways, tools used, and captured flags.

---

## 📋 Table of Contents

- [📁 Index](#-index)
- [🗂️ Structure](#️-structure)
- [⚙️ Methodology](#️-methodology)
- [📋 Command Reference](#-command-reference)
- [⚠️ Disclaimer](#️-disclaimer)

---

## 📁 Index

| Room | Difficulty | OS | Key Techniques |
|---|---|---|---|
| [Blueprint](./blueprint/) | Easy | Windows | Unpatched service exploit, hash dump, pass-the-hash |
| [Chill Hack](./chill/) | Easy | Linux | Command injection + blacklist bypass, steganography, Docker group abuse |
| [ColddBox: Easy](./colddbox/) | Easy | Linux | WPScan, reversePress, lxd privesc |
| [Creative](./creative/) | Easy | Linux | SSRF, path traversal, SSH key abuse |
| [CyberLens](./cyberlens/) | Easy | Windows | Apache Tika RCE, AlwaysInstallElevated |
| [Dav](./dav/) | Easy | Linux | WebDAV default credentials, PHP shell upload via PUT, sudo cat arbitrary read |
| [Gaming Server](./gamingServer/) | Easy | Linux | LFI, SSH key leak, lxd privesc |
| [IDE](./ide/) | Easy | Linux | Anonymous FTP, Codiad 2.8.4 RCE (CVE-2018-14009), writable systemd service |
| [Lazy Admin](./lazyadmin/) | Easy | Linux | SweetRice CMS exploit, sudo backup script abuse |
| [Lian Yu](./lianyu/) | Easy | Linux | FTP enumeration, steganography, sudo pkexec |
| [Mustacchio](./Mustacchio/) | Easy | Linux | XXE injection, SSH key crack, sudo path hijack |
| [Overpass 3: Hosting](./overpass3/) | Medium | Linux | GPG credential leak, FTP webroot upload, NFS no_root_squash |
| [Pyrat](./pyrat/) | Easy | Linux | Python eval RCE, git history credential leak |
| [RootMe](./rootme/) | Easy | Linux | File upload bypass, SUID Python privesc |
| [Service](./service/) | Easy | Linux | Docker abuse, service misconfiguration |
| [Silver Platter](./silverplatter/) | Easy | Linux | Silverpeas CVE, lateral movement, sudoers misconfiguration |
| [Source](./source/) | Easy | Linux | Webmin CVE-2019-15107 pre-auth RCE |
| [Thompson](./thompson/) | Easy | Linux | Tomcat Manager default creds, WAR upload, cron script poisoning |
| [Tomghost](./tomghost/) | Easy | Linux | Ghostcat (CVE-2020-1938), GPG key crack, zip2john |
| [U.A. High School](./ua/) | Easy | Linux | PHP RCE, base64 credential leak, sudo env abuse |
| [VulnNet: Internal](./vulnnet-internal/) | Easy | Linux | Redis RCE, SMB enumeration, TeamCity privesc |
| [VulnNet: Node](./vulnnet-node/) | Easy | Linux | node-serialize deserialization RCE, npm sudo abuse, writable systemd service |
| [VulnNet: Roasted](./vulnnet-roasted/) | Easy | Windows | AS-REP roasting, Kerberoasting, DCSync |
| [VulnNet Entertainment](./vulnnet-entertainment/) | Medium | Linux | JS bundle subdomain leak, LFI via php://filter, ClipBucket 4.0 file upload RCE, SSH backup crack, tar wildcard injection |
| [Whiterose](./whiterose/) | Easy | Linux | IDOR, EJS prototype pollution RCE (CVE-2022-29078), sudoedit bypass (CVE-2023-22809) |

---

## 🗂️ Structure

Each room lives in its own folder with a `README.md` writeup following a consistent format:

```
THM-writeup/
├── <room>/
│   └── README.md          ← full writeup
├── Exploit-Scripts/
│   └── ...                ← exploit scripts written during engagements
├── Powershell-Scripts/
│   └── ...                ← PowerShell utility scripts
├── COMMANDS.md            ← personal command cheatsheet (nmap, ffuf, hydra, etc.)
└── README.md              ← this file
```

---

## ⚙️ Methodology

Every writeup follows the same skeleton:

1. **Enumeration** — port scan (TCP + UDP), directory/vhost bruteforce, service fingerprinting
2. **Initial Access** — exploitation with full request/response context where relevant
3. **Privilege Escalation** — from foothold to root, with sudo/SUID/capability checks documented
4. **Attack Chain** — ASCII diagram of the full kill chain
5. **Key Takeaways** — what the box teaches, why it matters in real engagements
6. **Tools Used** — table of every tool used during the engagement
7. **Flags** — captured flag values

---

## 📋 Command Reference

Commonly used commands across recon, enumeration, exploitation, and post-exploitation are documented in [COMMANDS.md](./COMMANDS.md). Covers nmap, ffuf, gobuster, feroxbuster, hydra, hash cracking, vhost fuzzing, shell stabilisation, and more.

---

## ⚠️ Disclaimer

All activity documented here was conducted exclusively within TryHackMe's isolated lab environments. These writeups are intended for educational purposes and personal reference.

---
