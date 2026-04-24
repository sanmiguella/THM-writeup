# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

A collection of **system prompt files** (Markdown) for a multi-agent CTF/penetration testing orchestration framework targeting TryHackMe engagements. There is no build system, no source code, and no test suite — these are instruction files loaded into Claude instances.

## Agent Architecture

The system uses a **coordinator + specialist** pattern:

- **`coordinator-agent.md`** — Entry point. Reads `box-state.md` on start, classifies user input, routes to sub-agents, chains multi-agent workflows, and writes state updates after every agent completes.
- **Specialist agents** — Each handles one domain; the coordinator never performs tasks directly, only delegates.

| Agent File | Responsibility |
|---|---|
| `recon-agent.md` | Full TCP connect scan (`-sT -sC -sV -p- -T4`) + top-200 UDP scan, run in parallel |
| `ffuf-agent.md` | Directory + file enumeration via ffuf, two scans in parallel |
| `brainstorm-agent.md` | Attack path analysis from recon output — **no commands, reasoning only** |
| `linprivesc-agent.md` | Linux privesc: Phase 1 quick wins → linpeas → manual deep dive |
| `winprivesc-agent.md` | Windows privesc (standalone only, no AD): Phase 1 quick wins → winPEAS → manual |
| `payload-agent.md` | Reverse shells, web shells, msfvenom payloads, shell upgrade steps |
| `exploit-scripting-agent.md` | Python3 CVE exploit development using one of six templates (Web RCE, Authenticated Web, LFI/Traversal, SQLi, Buffer Overflow via pwntools, Raw Socket) |
| `cracking-agent.md` | Hash identification, hashcat/john cracking — see Platform Setup section in that file for macOS vs Linux paths |
| `THM-WRITEUP-AGENT.md` | Writeup generation and push to your configured GitHub writeup repo |

## Coordinator Routing Logic

The coordinator uses this decision tree (defined in `coordinator-agent.md` lines 39–74):

| Input signal | Agent triggered |
|---|---|
| IP or hostname only | recon-agent → brainstorm (automatic) |
| URL (`http://` or `https://`) | ffuf-agent |
| "shell" / "got access" + Linux | linprivesc-agent |
| "shell" / "got access" + Windows | winprivesc-agent |
| LHOST + LPORT, or payload/reverse shell request | payload-agent |
| CVE ID, exploit request, version + vuln behaviour | exploit-scripting-agent |
| Recon dump, "stuck", "dead end", "what should I try" | brainstorm-agent |
| Hash string, "crack", "john", "hashcat", "kerberoast" | cracking-agent |
| "writeup", "publish", room name + notes | THM-WRITEUP-AGENT |
| OS unclear with shell access confirmed | Ask: "Linux or Windows?" (one question only) |

**Ambiguity rule:** Ask exactly one clarifying question before routing. Never ask multiple questions.

| Ambiguous input | Ask |
|---|---|
| Bare IP with no context | "Scan only, or do you have a service/port in mind?" |
| "Got a shell" with no OS | "Linux or Windows?" |
| URL with no port | "HTTP or HTTPS? Any non-standard port?" |
| CVE with no target OS | "Is the target Linux or Windows?" |
| Generic "exploit this" | "What service, version, and OS?" |
| "Post writeup" with no notes | "Paste your notes for the room and confirm the room name." |

## Predefined Multi-Agent Chains

The coordinator runs these automatically without user re-triggering:

1. **Full Recon:** `recon-agent` → `brainstorm-agent` → `ffuf-agent` (if web port found)
2. **Shell to Root:** Ask OS → `payload-agent` (shell upgrade) → `(lin|win)privesc-agent`
3. **CVE Exploitation:** `exploit-scripting-agent` → `payload-agent` (if RCE)
4. **Dead End Recovery:** → `brainstorm-agent` → route to top recommended agent
5. **Writeup Publication:** → `THM-WRITEUP-AGENT` (generates room README + updates repo index + pushes)

## Session State

The coordinator maintains two files per engagement (not tracked by the repo):

- **`box-state.md`** — Read at session start; created after first agent completes; overwritten after every agent with current target, ports, shell user, dead ends, and pending action.
- **`progress.md`** — Append-only timestamped log; never overwritten.

**Box completion:** When root/SYSTEM is achieved or writeup is posted, both files are archived:
```
box-state.md  → <boxname>-completed.md
progress.md   → <boxname>-progress.md
```

## Output Format Contracts

Each agent produces a structured output block that the coordinator and chaining logic depend on. When editing an agent:
- Preserve the output format sections exactly — downstream agents parse them.
- Keep tool flags explicit (exact nmap flags, ffuf wordlist paths, etc.) rather than leaving them for the runtime agent to infer.
- `ffuf-agent.md` has a 3-tier wordlist fallback: `/usr/share/seclists/` → `/usr/share/wordlists/dirbuster/` → `/opt/SecLists/` — preserve this order if editing wordlist paths.
- If adding a new agent, update the routing table and agent registry in `coordinator-agent.md`.

## Required External Tools

Agents assume these are available in `PATH`:

- `nmap`, `ffuf`, `msfvenom`, `rlwrap`
- `john` (jumbo build — required for `ssh2john`, `zip2john`, etc.), `hashcat`
- `python3` with `requests` and `pwntools`
- `git` with push access to `https://github.com/YOUR_GITHUB_USERNAME/THM-writeup`
- Wordlists: SecLists at `/usr/share/seclists/`, `rockyou.txt`
- linpeas / linenum / winPEAS (served on demand via `python3 -m http.server`)

**cracking-agent platform note:** The file has a Platform Setup section covering both macOS (Homebrew, `~/wordlists/`, Metal GPU) and Linux/Kali (`apt`, `/usr/share/wordlists/`, CUDA/OpenCL GPU). Read that section before running extraction commands — the john helper script paths differ by OS.

## Other Files

- **`frequently-used-commands.md`** — Placeholder for a personal command reference link. Update it with your own cheat sheet URL.

## Writeup Agent Notes

- `THM-WRITEUP-AGENT.md` contains a room slug table (folder name → TryHackMe URL slug) with example non-obvious mappings. Users populate it as they complete rooms; the agent falls back to extracting the slug from the TryHackMe URL if a room isn't listed.
- The canonical formatting reference is the first writeup you complete — update the reference in `THM-WRITEUP-AGENT.md` to point to it once it exists.
- Flags must use `<details>`/`<summary>` collapsible blocks — never a plain table.
- The repo is used as a professional portfolio, so writeup language should be neutral and educational.

## Getting Started

These are system prompt files. Load them into Claude like this:

1. **Create a Claude Project** at [claude.ai/projects](https://claude.ai/projects)
2. **Paste `coordinator-agent.md`** as the project's system prompt / custom instructions
3. **Upload all other agent files** to the project knowledge base so the coordinator can reference them by filename
4. **For each new box**, start a fresh conversation in a dedicated working directory — state files (`box-state.md`, `progress.md`) are created there automatically
5. **Before using the writeup agent**, create your GitHub writeup repo and replace `YOUR_GITHUB_USERNAME` in `THM-WRITEUP-AGENT.md` with your actual username
