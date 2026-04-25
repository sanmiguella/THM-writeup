# TryHackMe Writeup Agent Instructions

This file contains the full system prompt, formatting rules, and learned preferences for the CTF writeup agent. Drop it into your new server's project instructions or CLAUDE.md.

---

## Configuration

> **Required before first use:** Set your GitHub repo URL below. Replace the placeholder with your own repo.

```
GITHUB_REPO: https://github.com/<your-username>/<your-writeup-repo>
```

Edit this file and update `GITHUB_REPO` to point to your own TryHackMe writeup repository. All git push steps use this value.

---

## Project Goal

Document TryHackMe CTF rooms and publish them to your configured GitHub writeup repository.

When given notes for a room, do the following in order:
1. Generate the room writeup (`<roomname>/README.md`)
2. Update the repo-level `README.md` index
3. Push both files to GitHub

---

## Writing Style

All writeup text must follow these rules. Apply them to every sentence — the overview paragraph, step descriptions, and key takeaways.

**Keep sentences short.** One idea per sentence. If a sentence needs a comma to survive, split it.

**Use plain words.**
| Don't say | Say instead |
|---|---|
| leverage / utilize | use |
| identify | find |
| demonstrate | show |
| enumerate | list / check / scan |
| it is worth noting | (just say it) |
| this allows an attacker to | this lets you |
| exploitation vector | attack path |
| it should be noted that | (cut it entirely) |

**Write in active voice.** "The filter blocks `../..`" — not "The path is blocked by the filter."

**Explain first, then show the command.** One short sentence saying what the command does goes above the code block. Don't explain it after.

**For each step, answer three things in plain terms:** what you did, what you found, what you did next.

**Key Takeaways should read like tips from a friend**, not lessons from a textbook. Start each with a verb: "Always read the PHP source before guessing filter bypass strings", not "It is important to read the PHP source code prior to attempting filter bypass."

**Technical terms are okay.** Just explain them briefly the first time: "LFI (Local File Inclusion) — a bug where the app includes a file you control via a URL parameter."

**Overview paragraph limit:** 4 sentences maximum.

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

| Repo folder | Room slug |
|---|---|
| `blueprint` | `blueprint` |
| `cheese` | `cheesectfv10` |
| `chill` | `chillhack` |
| `colddbox` | `colddboxeasy` |
| `creative` | `creative` |
| `cyberlens` | `cyberlensp6` |
| `dav` | `bsidesgtdav` |
| `gamingServer` | `gamingserver` |
| `ide` | `ide` |
| `lazyadmin` | `lazyadmin` |
| `lianyu` | `lianyu` |
| `mkingdom` | `mkingdom` |
| `Mustacchio` | `mustacchio` |
| `overpass3` | `overpass3hosting` |
| `pyrat` | `pyrat` |
| `rootme` | `rrootme` |
| `service` | `services` |
| `silverplatter` | `silverplatter` |
| `source` | `source` |
| `thompson` | `bsidesgtthompson` |
| `tomghost` | `tomghost` |
| `ua` | `yueiua` |
| `vulnnet-internal` | `vulnnetinternal` |
| `vulnnet-node` | `vulnnetnode` |
| `vulnnet-roasted` | `vulnnetroasted` |
| `vulnnet-entertainment` | `vulnnet1` |
| `wgel` | `wgelctf` |
| `whiterose` | `whiterose` |

For new rooms not in this list, use the slug from the TryHackMe room URL.

---

## Reference Writeup

A canonical formatting example is the `chill` room writeup in the original framework repo:
`https://github.com/sanmiguella/THM-writeup/blob/main/chill/README.md`

Use this as a visual reference for structure and style. Your own writeups go to your configured `GITHUB_REPO`.

