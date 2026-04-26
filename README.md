# 🔐 TryHackMe Writeups

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Boxes](https://img.shields.io/badge/Boxes-32-blueviolet?style=for-the-badge)]()
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
| [Soupedecode](./soupedecode/) | Medium | Windows | Guest SMB RID cycling, username=password spray, Kerberoasting, machine account Pass-the-Hash |
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

The [`generic-agents/`](./generic-agents/) folder is a plug-and-play multi-agent framework for TryHackMe and CTF engagements, built for [Claude Code](https://claude.ai/code). Drop the folder into a working directory, open Claude Code, and the agents coordinate automatically — routing each task to the right specialist without you having to think about which one to call.

### How it works

Every task goes through the **Coordinator**, which reads your input, classifies it, and invokes the right agent. You never call a sub-agent directly. Type an IP and it kicks off recon. Say "got a shell" and it asks Linux or Windows, then hands off to the right privesc agent. Say "writeup" and the whole publish pipeline runs end to end.

When [HexStrike MCP](./generic-agents/hexstrike-agent.md) is running locally (port 8888), the coordinator routes recon, web enumeration, privesc, cracking, web vulns, stego, and forensics through it — 150+ tools in one call. When it's not available, it falls back to the individual specialist agents automatically.

### Quick start

**1. Copy the folder** into your CTF working directory:

```bash
cp -r generic-agents/ ~/your-ctf-dir/
cd ~/your-ctf-dir/
```

**2. Edit [`USER-CONFIG.md`](./generic-agents/USER-CONFIG.md)** — this is the only file you need to change:

```
WRITEUP_REPO_URL: https://github.com/YOUR_GITHUB_USERNAME/THM-writeup
COMMANDS_RAW_URL: https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/THM-writeup/main/COMMANDS.md
SECLISTS_PATH: ~/SecLists
```

Replace `YOUR_GITHUB_USERNAME` with your GitHub username. Set `SECLISTS_PATH` to wherever SecLists is installed on your machine (e.g. `/usr/share/seclists` on Kali).

**3. Create the wordlist symlinks** (run once from your working directory):

```bash
ln -sf ~/SecLists/Discovery/DNS/               DNS
ln -sf ~/SecLists/Passwords/                   Passwords
ln -sf ~/SecLists/Usernames/                   Usernames
ln -sf ~/SecLists/Discovery/Web-Content/       Web-Content
ln -sf /etc/hosts                              hosts
```

**4. Open Claude Code** in that directory and start a session. The framework bootstraps itself on first run.

> **No writeup repo yet?** Fork this repo to get a pre-built `COMMANDS.md` and writeup index to start from, then point `USER-CONFIG.md` at your fork.

---

### Agent roster

| Agent | Trigger | What it does |
|---|---|---|
| [Coordinator](./generic-agents/coordinator-agent.md) | Everything — entry point | Reads input, classifies the task, routes to the right agent. Never calls sub-agents directly. |
| [HexStrike](./generic-agents/hexstrike-agent.md) | IP, URL, hash, "shell", binary, OSINT *(MCP up)* | Primary agent when HexStrike MCP is running. Invokes 150+ tools via localhost:8888 — rustscan, nmap, feroxbuster, nuclei, linpeas/winpeas, hashcat, ghidra, volatility, shodan, and more. |
| [Recon](./generic-agents/recon-agent.md) | IP or hostname *(MCP down)* | Full TCP connect scan + top 200 UDP ports via nmap. Outputs open ports and service versions. |
| [ffuf](./generic-agents/ffuf-agent.md) | URL, web port discovered *(MCP down)* | Directory and file enumeration. Handles vhost fuzzing and extension sweeps. |
| [Brainstorm](./generic-agents/brainstorm-agent.md) | Recon dump, "stuck", "what next" | Reasons over findings and surfaces the most promising attack paths. Always available, runs after every recon. |
| [LinPrivesc](./generic-agents/linprivesc-agent.md) | "shell" + Linux *(MCP down)* | Runs the full Linux privesc checklist: sudo, SUID, cron, writable paths, capabilities, services. |
| [WinPrivesc](./generic-agents/winprivesc-agent.md) | "shell" + Windows *(MCP down)* | Windows privesc: token abuse, unquoted paths, AlwaysInstallElevated, scheduled tasks, credential hunting. |
| [Payload](./generic-agents/payload-agent.md) | LHOST + LPORT, "reverse shell", "web shell" | Generates reverse shells, web shells, and msfvenom payloads. Always available — HexStrike doesn't do this. |
| [Cracking](./generic-agents/cracking-agent.md) | Hash, "crack", credential file *(MCP down)* | Identifies hash type, picks the right hashcat mode or john rule, handles SSH/zip/KeePass extraction. |
| [Exploit Scripting](./generic-agents/exploit-scripting-agent.md) | CVE ID, "write an exploit" | Writes Python 3 exploit scripts from a CVE or vuln description. Always available. |
| [OWASP Top 10](./generic-agents/owasp-top-10-agent.md) | "OWASP", XSS/SSRF/IDOR/injection *(MCP down or chained)* | Full OWASP Top 10:2025 analysis and exploitation. Also chains after HexStrike for deep manual bypass logic. |
| [GTFOBins](./generic-agents/gtfo-agent.md) | Binary name + privesc context | Looks up shell escapes, file read/write, SUID, sudo, and capability abuse for any Unix binary. Always available. |
| [SearchSploit](./generic-agents/searchsploit-agent.md) | Service + version, "find exploit" | Searches Exploit-DB, evaluates matches, adapts the exploit to the target. Always available. |
| [CTF Commands](./generic-agents/ctf-commands-agent.md) | "how do I", "command for", technique name | Fetches the live `COMMANDS.md` from your repo on every call and returns exact, context-filled commands ready to run. |
| [THM Writeup](./generic-agents/THM-WRITEUP-AGENT.md) | "writeup", box completion | Generates the full writeup, runs a standards compliance check, audits `COMMANDS.md`, updates the repo index, and pushes everything in one commit. |

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
