# TryHackMe Writeup Agent Instructions

This file contains the full system prompt, formatting rules, and learned preferences for the CTF writeup agent. Drop it into your new server's project instructions or CLAUDE.md.

---

## Project Goal

Document TryHackMe CTF rooms and publish them to the GitHub repo at `https://github.com/YOUR_GITHUB_USERNAME/THM-writeup`.

When given notes for a room, do the following in order:
1. Generate the room writeup (`<roomname>/README.md`)
2. Update the repo-level `README.md` index
3. Push both files to GitHub

---

## Step 1 — Generate the Room Writeup

Create `<roomname>/README.md` following this exact structure:

### Header

```markdown
# <emoji> <Room Name>

[![Platform](https://img.shields.io/badge/Platform-TryHackMe-red?style=for-the-badge&logo=tryhackme)](https://tryhackme.com/room/<slug>)
[![Difficulty](https://img.shields.io/badge/Difficulty-<Level>-<color>?style=for-the-badge)](https://tryhackme.com/room/<slug>)
[![Status](https://img.shields.io/badge/Status-Completed-brightgreen?style=for-the-badge)](https://tryhackme.com/room/<slug>)
[![Type](https://img.shields.io/badge/Type-<CTF|Boot2Root|...>-blue?style=for-the-badge)](https://tryhackme.com/room/<slug>)
```

All four badges should link to the specific room URL.

### Overview Table

```markdown
| | |
|---|---|
| **Target** | `<IP>` |
| **OS** | Linux / Windows |
| **Attack Surface** | <e.g. HTTP, SSH, FTP> |
| **Privesc** | <e.g. SUID binary, sudo -l, cron> |
```

Follow with a short paragraph (2–4 sentences) summarising the full attack chain from initial recon to root.

### Sections (in this order)

```
## 🔍 Enumeration
## 💀 Initial Access
## 🔁 Privilege Escalation
## 🗺️ Attack Chain
## 📌 Key Takeaways
## 🎯 MITRE ATT&CK Mapping
## 🛠️ Tools Used
## 🚩 Flags
```

---

## Section Formatting Rules

**Code blocks** — wrap all commands and terminal output in fenced code blocks with the appropriate language tag (e.g. ` ```bash `, ` ```text `).

**Inline backticks** — use for paths, filenames, usernames, tool names (e.g. `/etc/passwd`, `www-data`, `gobuster`).

**Attack Chain** — ASCII art diagram showing the full exploitation path, e.g.:

```
[Attacker]
    |
    | HTTP enumeration (gobuster)
    v
[Web Server :80]
    |
    | Upload bypass → reverse shell
    v
[www-data shell]
    |
    | SUID find → root
    v
[root]
```

**Key Takeaways** — 3–5 concise lessons from the room.

---

## 🎯 MITRE ATT&CK Mapping

Include a table mapping tactics and techniques actually used in the room. Link each technique ID to `https://attack.mitre.org/techniques/TXXXX`.

```markdown
## 🎯 MITRE ATT&CK Mapping

| Tactic | Technique | ID |
|---|---|---|
| Reconnaissance | Active Scanning | [T1595](https://attack.mitre.org/techniques/T1595) |
| Initial Access | Exploit Public-Facing Application | [T1190](https://attack.mitre.org/techniques/T1190) |
```

Only include techniques that were actually used — don't pad the table.

---

## 🛠️ Tools Used

```markdown
## 🛠️ Tools Used

| Tool | Purpose |
| --- | --- |
| `nmap` | Port and service enumeration |
| `gobuster` | Directory brute-forcing |
```

Only list tools actually used in the room.

---

## 🚩 Flags

Use `<details>`/`<summary>` collapsible blocks — one per flag. Do **not** use a plain table.

```markdown
## 🚩 Flags

<details>
<summary><code>user.txt</code></summary>

`THM{...}`

</details>

<details>
<summary><code>root.txt</code></summary>

`THM{...}`

</details>
```

Flag filenames should match exactly what was found on the target.

---

## Disclaimer

If a disclaimer section is included, keep it professional and neutral. Preferred wording:

> All activity documented here was conducted exclusively within TryHackMe's isolated lab environments. These writeups are intended for educational purposes and personal reference.

Do not use casual or dismissive language. The repo is used as a professional portfolio visible to potential employers.

---

## Step 2 — Update the Repo-Level README

Add the new room to the index table in **alphabetical order**:

```markdown
| [Room Name](./roomname/) | Difficulty | OS | Key techniques |
```

Bump the Boxes badge count by 1.

---

## Step 3 — Push to GitHub

- Create `<roomname>/README.md` with the writeup
- Update root `README.md` with the new index entry
- Commit message format: `Add <RoomName> writeup (<key technique>)`

---

## Room URL Reference

Platform badge slug format: `https://tryhackme.com/room/<slug>`

The slug is the last path segment of the TryHackMe room URL. It is not always the same as the room name — some rooms have versioned or abbreviated slugs. When writing a writeup, find the slug from the browser URL bar on the room page.

Populate this table as you complete rooms. The left column is your local repo folder name; the right is the TryHackMe URL slug. Examples of non-obvious mappings:

| Repo folder | Room slug |
|---|---|
| `cheese` | `cheesectfv10` |
| `chill` | `chillhack` |
| `dav` | `bsidesgtdav` |
| `rootme` | `rrootme` |
| `ua` | `yueiua` |
| `wgel` | `wgelctf` |

**Fallback:** If a room is not in the table, extract the slug directly from `https://tryhackme.com/room/<slug>` and use it for all badge links. Add it to the table after.

---

## Reference Writeup

Once you have completed your first room, set that writeup as the canonical formatting reference here. Update this section with:

```
https://github.com/YOUR_GITHUB_USERNAME/THM-writeup/blob/main/<first-room>/README.md
```

Until then, use the section formatting rules above as the sole reference.

