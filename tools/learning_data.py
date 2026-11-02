"""Learning content for the Practice Mode.

Per-tool modules (beginner → advanced) and a per-tool flag dictionary used by the
command explainer. Content is concise and practical; it is educational material,
not a substitute for authorisation.
"""
from __future__ import annotations

# tool id -> list of modules {level, title, body, example}
MODULES: dict[str, list[dict]] = {
    "nmap": [
        {"level": "Beginner", "title": "What Nmap does",
         "body": "Nmap discovers hosts and the services running on them by sending "
                 "probes and interpreting the responses. Start with a simple scan of "
                 "a single authorised host.",
         "example": "nmap 192.168.56.101"},
        {"level": "Beginner", "title": "Service & version detection",
         "body": "-sV asks Nmap to interrogate open ports to identify the service and "
                 "version; -sC runs the default safe NSE scripts for extra detail.",
         "example": "nmap -sV -sC 192.168.56.101"},
        {"level": "Intermediate", "title": "Scanning all ports efficiently",
         "body": "-p- scans all 65535 TCP ports; -T4 speeds up timing on reliable "
                 "networks. Combine with -sV once you know which ports are open.",
         "example": "nmap -p- -T4 192.168.56.101"},
        {"level": "Advanced", "title": "OS detection & output",
         "body": "-O fingerprints the operating system; -oA writes results in all "
                 "formats for later parsing or reporting.",
         "example": "nmap -O -oA scan 192.168.56.101"},
    ],
    "gobuster": [
        {"level": "Beginner", "title": "Directory discovery",
         "body": "Gobuster brute-forces paths on a web server using a wordlist to "
                 "reveal hidden directories and files.",
         "example": "gobuster dir -u http://target -w /usr/share/wordlists/dirb/common.txt"},
        {"level": "Intermediate", "title": "Filtering & extensions",
         "body": "-x appends file extensions to each word; -s / -b control which HTTP "
                 "status codes are shown or hidden.",
         "example": "gobuster dir -u http://target -w list.txt -x php,txt,html"},
    ],
    "sqlmap": [
        {"level": "Beginner", "title": "Finding SQL injection",
         "body": "SQLmap automates detection and exploitation of SQL injection. Only "
                 "run it against applications you are authorised to test — it is a "
                 "high-impact, lab-only tool.",
         "example": "sqlmap -u \"http://target/item?id=1\" --batch"},
        {"level": "Advanced", "title": "Enumerating data",
         "body": "After confirming injection, --dbs lists databases, --tables and "
                 "--dump extract structure and data. Use --batch for non-interactive runs.",
         "example": "sqlmap -u \"http://target/item?id=1\" --batch --dbs"},
    ],
    "hydra": [
        {"level": "Beginner", "title": "Online password testing",
         "body": "Hydra tests credentials against a network service. Authorised, "
                 "lab-only use — brute forcing real systems is illegal without consent.",
         "example": "hydra -l admin -P wordlist.txt ssh://192.168.56.101"},
    ],
    "hashcat": [
        {"level": "Beginner", "title": "Cracking a hash offline",
         "body": "Hashcat recovers passwords from captured hashes using the GPU. The "
                 "-m flag selects the hash mode (e.g. 0 = MD5, 1000 = NTLM).",
         "example": "hashcat -m 0 hashes.txt rockyou.txt"},
    ],
    "nuclei": [
        {"level": "Beginner", "title": "Template-based scanning",
         "body": "Nuclei checks a target against community templates for known issues. "
                 "Great for a fast first pass on an authorised web target.",
         "example": "nuclei -u http://target"},
        {"level": "Intermediate", "title": "Targeting specific checks",
         "body": "-tags lets you run only certain template groups, e.g. cve or misconfig.",
         "example": "nuclei -u http://target -tags cve"},
    ],
    "wireshark": [
        {"level": "Beginner", "title": "Capturing traffic",
         "body": "Wireshark captures and dissects packets on an interface. Use display "
                 "filters (e.g. http, tcp.port==80) to focus on what matters.",
         "example": "wireshark"},
    ],
    "ffuf": [
        {"level": "Beginner", "title": "Fuzzing with FUZZ keyword",
         "body": "FFUF replaces the FUZZ keyword in the URL with each wordlist entry — "
                 "use it for directories, parameters or virtual hosts.",
         "example": "ffuf -u http://target/FUZZ -w list.txt"},
    ],
    "john": [
        {"level": "Beginner", "title": "Cracking with a wordlist",
         "body": "John the Ripper cracks password hashes. --wordlist runs a dictionary "
                 "attack; --show reveals already-cracked passwords.",
         "example": "john --wordlist=rockyou.txt hashes.txt"},
    ],
    "metasploit": [
        {"level": "Beginner", "title": "The Metasploit console",
         "body": "msfconsole is the main interface. search finds modules, use selects "
                 "one, show options lists what to set. Lab-only, authorised targets.",
         "example": "msfconsole -q"},
    ],
    "binwalk": [
        {"level": "Beginner", "title": "Analysing firmware",
         "body": "Binwalk scans a binary for embedded files and filesystems; -e "
                 "extracts what it finds.",
         "example": "binwalk -e firmware.bin"},
    ],
}

# tool id -> {flag: explanation}. Used by the command explainer.
FLAGS: dict[str, dict[str, str]] = {
    "nmap": {
        "-sV": "probe open ports to determine service/version",
        "-sC": "run the default NSE script set",
        "-sS": "TCP SYN (stealth) scan",
        "-sU": "UDP scan",
        "-sn": "ping scan — host discovery only, no port scan",
        "-p-": "scan all 65535 ports",
        "-p": "scan the specified port(s)",
        "-T4": "aggressive timing template (faster)",
        "-A": "enable OS detection, version, scripts and traceroute",
        "-O": "enable OS detection",
        "-oA": "output in all formats with the given base name",
        "-Pn": "treat all hosts as online (skip host discovery)",
        "--top-ports": "scan the N most common ports",
        "--traceroute": "trace the network path to the host",
    },
    "gobuster": {
        "dir": "directory/file brute-force mode",
        "dns": "DNS subdomain brute-force mode",
        "-u": "target URL",
        "-d": "target domain",
        "-w": "wordlist file",
        "-x": "file extensions to append",
        "-q": "quiet output",
        "-t": "number of concurrent threads",
    },
    "sqlmap": {
        "-u": "target URL",
        "--batch": "never ask for input; use defaults",
        "--dbs": "enumerate databases",
        "--tables": "enumerate tables",
        "--dump": "dump table contents",
        "--level": "level of tests to perform (1-5)",
        "--risk": "risk of tests to perform (1-3)",
    },
    "hydra": {
        "-l": "single login name",
        "-L": "login name list file",
        "-p": "single password",
        "-P": "password list file",
        "-t": "number of parallel tasks",
        "-f": "stop after the first valid pair",
    },
    "hashcat": {
        "-m": "hash type/mode",
        "-a": "attack mode (0=straight,3=brute)",
        "-b": "benchmark",
        "-d": "select device(s)",
        "--force": "ignore warnings",
    },
    "ffuf": {
        "-u": "target URL with the FUZZ keyword",
        "-w": "wordlist",
        "-mc": "match these HTTP status codes",
        "-fc": "filter out these status codes",
        "-recursion": "recurse into discovered directories",
    },
    "nuclei": {
        "-u": "target URL",
        "-t": "templates to run",
        "-tags": "run templates with these tags",
        "-severity": "filter by severity",
        "-silent": "show only results",
    },
    "nikto": {"-h": "target host/URL", "-ssl": "force SSL", "-port": "target port"},
    "john": {"--wordlist": "dictionary file", "--show": "show cracked passwords",
             "--format": "hash format", "--rules": "enable word-mangling rules"},
    "whatweb": {"-a": "aggression level (1-4)", "-v": "verbose output"},
    "dig": {"ANY": "request all record types", "+short": "terse output",
            "AXFR": "attempt a zone transfer", "MX": "mail records", "A": "address records"},
}

# generic flags understood across many tools
GENERIC_FLAGS = {
    "-v": "verbose output", "-vv": "more verbose output", "-q": "quiet output",
    "-o": "write output to a file", "-h": "show help / target host (tool-specific)",
    "-i": "input file or interface", "-t": "threads or target (tool-specific)",
    "--help": "show help", "-w": "wordlist or write-file (tool-specific)",
}
