# Summary of the Archangel CTF Challenge

The Archangel room is a TryHackMe boot-to-root challenge rated Easy that demonstrates multiple attack vectors from reconnaissance through full system compromise.

## Attack Flow

**Initial Reconnaissance:** The attacker discovers that examining page source reveals "support@mafialive.thm," exposing a hidden virtual host not linked in navigation.

**Web Exploitation:** The mafialive.thm vhost contains a Local File Inclusion vulnerability in `/test.php?view=`. Although the application blocks the string "../.." and requires paths containing "/var/www/html/development_testing," the filter can be bypassed by substituting ".././" for each "../" instance.

**Code Execution:** Rather than attempting log poisoning, the attacker leverages "a PHP filter chain generator to construct a remote code execution payload from iconv encoding tricks." The technique appends the required path string as a URL query parameter to `php://temp`, which passes the `strpos()` validation check without disrupting the filter chain functionality.

**Lateral Escalation:** A world-writable script at `/opt/helloworld.sh` is executed by cron as the archangel user. By overwriting this script, www-data gains archangel-level access.

**Stable Shell via SSH:** After gaining code execution as the archangel user through the cron job, the next step is to establish a stable interactive shell over SSH. Generate an SSH key pair on the victim machine (`ssh-keygen`), append the public key to `/home/archangel/.ssh/authorized_keys`, then copy the generated private key (`id_rsa`) to the attacker machine. Use that private key to SSH in directly as archangel (`ssh -i id_rsa archangel@<target-ip>`), replacing the fragile reverse shell with a full TTY session.

**Privilege Escalation:** The `/home/archangel/secret/backup` binary runs as root but invokes `cp` without specifying its full path. By prepending the current directory to the PATH environment variable and placing a malicious `cp` script there, the SUID binary executes attacker-controlled code with root privileges.

## Key Security Lessons

- Email addresses in source code reveal undocumented internal infrastructure
- Filter bypasses require reading the actual validation logic before guessing techniques
- PHP filter chains achieve RCE through LFI alone, without file uploads
- Cron-executed scripts owned by other users represent direct lateral movement paths
- SSH key generation on the victim and transferring the private key to the attacker box is a reliable way to upgrade a cron-based shell to a stable, interactive SSH session
- SUID binaries calling unqualified command names are vulnerable to PATH hijacking attacks
