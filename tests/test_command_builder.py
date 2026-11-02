from core import command_builder as cb


def test_placeholders_unique_order():
    assert cb.placeholders("nmap {target} {target} {port}") == ["target", "port"]


def test_build_substitutes_and_reports_missing():
    cmd, missing = cb.build("nmap -sV {target} -p {port}", {"target": "10.0.0.1"})
    assert cmd == "nmap -sV 10.0.0.1 -p {port}"
    assert missing == ["port"]


def test_build_quotes_dangerous_values():
    cmd, missing = cb.build("sqlmap -u {url}", {"url": "http://x/?a=1&b=2"})
    assert "'" in cmd or '"' in cmd
    assert not missing


def test_target_values_only_target_placeholders():
    vals = {"target": "10.0.0.1", "wordlist": "rockyou.txt"}
    assert cb.target_values("nmap {target} -w {wordlist}", vals) == ["10.0.0.1"]


def test_build_complete_command():
    cmd, missing = cb.build("gobuster dir -u {url} -w {wordlist}",
                            {"url": "http://t.test", "wordlist": "list.txt"})
    assert missing == []
    assert cmd == "gobuster dir -u http://t.test -w list.txt"
