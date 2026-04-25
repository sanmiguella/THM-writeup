# 🔐 TryHackMe Writeups

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Boxes](https://img.shields.io/badge/Boxes-31-blueviolet?style=for-the-badge)]()
[![Focus](https://img.shields.io/badge/Focus-Realistic_Chains-informational?style=for-the-badge)]()

Writeups for TryHackMe rooms. Emphasis on methodology, realistic attack chains, and understanding the *why* behind each step — not just dumping commands. Written as personal reference between professional engagements.

Each writeup covers: enumeration → initial access → privilege escalation, with an ASCII attack chain diagram, key takeaways, tools used, and captured flags.

---

## 📋 Table of Contents

- [📁 Index](#-index)
- [🤖 Generic Agents](#-generic-agents)
- [🗂️ Structure](#%EF%B8%8F-structure)
- [⚙️ Methodology](#%EF%B8%8F-methodology)
- [📋 Command Reference](#-command-reference)
- [⚠️ Disclaimer](#%EF%B8%8F-disclaimer)

---

## 📁 Index

| Room | Difficulty | OS | Key Techniques |
|---|---|---|---|
| [Archangel](./archangel/) | Easy | Linux | Vhost discovery via email leak, LFI filter bypass, PHP filter chain RCE, cron world-writable script, PATH hijacking SUID binary |
| [Blueprint](./blueprint/) | Easy | Windows | Unpatched service exploit, hash dump, pass-the-hash |
| [The Cheese Shop](./cheese/) | Easy | Linux | SQLi OR filter bypass, LFI via php://filter, PHP filter chain RCE, SUID xxd privesc |
| [Chill Hack](./chill/) | Easy | Linux | Command injection + blacklist bypass, steganography, Docker group abuse |
| [ColddBox: Easy](./colddbox/) | Easy | Linux | WPScan, reversePress, lxd privesc |
| [Creative](./creative/) | Easy | Linux | SSRF, path traversal, SSH key abuse |
| [CyberLens](./cyberlens/) | Easy | Windows | Apache Tika RCE, AlwaysInstallElevated |
| [Dav](./dav/) | Easy | Linux | WebDAV default credentials, PHP shell upload via PUT, sudo cat arbitrary read |
| [Gaming Server](./gamingServer/) | Easy | Linux | LFI, SSH key leak, lxd privesc |
| [IDE](./ide/) | Easy | Linux | Anonymous FTP, Codiad 2.8.4 RCE (CVE-2018-14009), writable systemd service |
| [Jack-of-all-trades](./jack/) | Easy | Linux | Swapped ports, multi-layer encoding, steganography, SUID strings arbitrary file read |
| [Lazy Admin](./lazyadmin/) | Easy | Linux | SweetRice CMS exploit, sudo backup script abuse |
| [Lian Yu](./lianyu/) | Easy | Linux | FTP enumeration, steganography, sudo pkexec |
| [mKingdom](./mkingdom/) | Easy | Linux | Concrete5 default creds, PHP webshell, /etc/hosts poison, cron HTTP hijack |
| [Mustacchio](./Mustacchio/) | Easy | Linux | XXE injection, SSH key crack, sudo path hijack |
| [Overpass 3: Hosting](./overpass3/) | Medium | Linux | GPG credential leak, FTP webroot upload, NFS no_root_squash |
| [Pyrat](./pyrat/) | Easy | Linux | Python eval RCE, git history credential leak |
| [Publisher](./publisher/) | Easy | Linux | SPIP CVE-2023-27372 RCE, SSH key leak, AppArmor bypass via at |
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
| [Wgel CTF](./wgel/) | Easy | Linux | Exposed SSH key via web directory, sudo wget /etc/passwd overwrite |
| [Whiterose](./whiterose/) | Easy | Linux | IDOR, EJS prototype pollution RCE (CVE-2022-29078), sudoedit bypass (CVE-2023-22809) |

---

## 🤖 Generic Agents

The [`generic-agents/`](./generic-agents/) folder contains a collection of reusable Claude agent definitions for common CTF and penetration testing workflows. These agents are available for anyone to use — feel free to copy, adapt, or extend them for your own engagements.

| Agent | Purpose |
|---|---|
| [Coordinator Agent](./generic-agents/coordinator-agent.md) | Entry point — routes input to the correct sub-agent automatically |
| [Recon Agent](./generic-agents/recon-agent.md) | Full TCP + top UDP nmap scan against a target |
| [ffuf Agent](./generic-agents/ffuf-agent.md) | Directory and file enumeration via ffuf |
| [Brainstorm Agent](./generic-agents/brainstorm-agent.md) | Attack path reasoning from recon output or when stuck |
| [Payload Agent](./generic-agents/payload-agent.md) | Reverse shells, web shells, msfvenom payloads, shellcode |
| [Exploit Scripting Agent](./generic-agents/exploit-scripting-agent.md) | Python3 exploit scripts from CVE or vulnerability description |
| [LinPrivesc Agent](./generic-agents/linprivesc-agent.md) | Linux privilege escalation enumeration and analysis |
| [WinPrivesc Agent](./generic-agents/winprivesc-agent.md) | Windows privilege escalation enumeration and analysis |
| [Cracking Agent](./generic-agents/cracking-agent.md) | Hash identification, hashcat/john cracking, extraction guides |
| [OWASP Top 10 Agent](./generic-agents/owasp-top-10-agent.md) | Web vulnerability analysis and exploitation (OWASP Top 10:2025) |
| [GTFOBins Agent](./generic-agents/gtfo-agent.md) | GTFOBins lookup for SUID, sudo, capabilities, and shell escapes |
| [SearchSploit Agent](./generic-agents/searchsploit-agent.md) | Exploit-DB search, evaluation, and adaptation |
| [CTF Commands Agent](./generic-agents/ctf-commands-agent.md) | Exact ready-to-run command reference for any CTF technique |
| [HexStrike Agent](./generic-agents/hexstrike-agent.md) | MCP-backed agent for binary RE, OSINT, memory forensics, and multi-tool chains |
| [THM Writeup Agent](./generic-agents/THM-WRITEUP-AGENT.md) | Generates structured TryHackMe writeups and pushes to GitHub |

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
├── generic-agents/
│   └── ...                ← reusable Claude agent definitions (open for anyone to use)
├── COMMANDS.md            ← personal command cheatsheet
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
6. **MITRE ATT&CK Mapping** — techniques mapped to ATT&CK tactics and IDs
7. **Tools Used** — table of every tool used during the engagement
8. **Flags** — captured flag values

---

## 📋 Command Reference

Commonly used commands across recon, enumeration, exploitation, and post-exploitation are documented in [COMMANDS.md](./COMMANDS.md). Covers nmap, ffuf, wpscan, cadaver, sqlmap, LFI via `php://filter` and PHP filter chain RCE, SMB/NFS/Redis enumeration, Tomcat WAR deployment, GPG decryption, hash cracking (MD5 through Kerberoasting), steganography, shell stabilisation, and Linux/Windows privilege escalation.

---

## ⚠️ Disclaimer

All activity documented here was conducted exclusively within TryHackMe's isolated lab environments. These writeups are intended for educational purposes and personal reference.

---
