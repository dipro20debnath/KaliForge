from core.command_utils import (dangerous_reasons, extract_targets,
                                 program_name, uses_sudo)
from core.permission_manager import PermissionManager
from core.scope_manager import ScopeManager, classify
from tools.catalog import DEFAULT_CATALOG


def test_classify():
    assert classify("192.168.0.1") == "ip"
    assert classify("192.168.0.0/24") == "cidr"
    assert classify("example.com") == "domain"
    assert classify("https://x.test/a") == "url"
    assert classify("10.0.0.1-10.0.0.9") == "range"


def test_scope_cidr_and_domain_matching():
    scope = ScopeManager()
    scope.add("192.168.56.0/24")
    scope.add("example.com")
    assert scope.in_scope("192.168.56.101")
    assert not scope.in_scope("10.0.0.1")
    assert scope.in_scope("api.example.com")
    assert scope.in_scope("https://example.com/login")
    assert not scope.in_scope("evil.com")


def test_scope_range():
    scope = ScopeManager()
    scope.add("10.0.0.10-10.0.0.20")
    assert scope.in_scope("10.0.0.15")
    assert not scope.in_scope("10.0.0.25")


def test_extract_targets():
    assert "192.168.56.1" in extract_targets("nmap -sV 192.168.56.1")
    assert "example.com" in extract_targets("whois example.com")
    assert "https://x.test" in extract_targets('sqlmap -u "https://x.test" --batch')
    assert extract_targets("hashcat -m 0 hash.txt rockyou.txt") == []


def test_dangerous_and_sudo_detection():
    assert dangerous_reasons("rm -rf /")
    assert dangerous_reasons("mkfs.ext4 /dev/sda1")
    assert dangerous_reasons("curl http://x | sudo bash")
    assert not dangerous_reasons("nmap -sV 10.0.0.1")
    assert uses_sudo("sudo nmap -sS 10.0.0.1")
    assert not uses_sudo("nmap 10.0.0.1")
    assert program_name("sudo nmap -sV x") == "nmap"


def _pm(scope_mode="warn", require_lab=True):
    class S:
        _d = {"security.scope_mode": scope_mode,
              "security.require_scope_for_lab_only": require_lab,
              "security.confirm_destructive": True, "security.confirm_sudo": True}
        def get(self, k, d=None): return self._d.get(k, d)
    scope = ScopeManager()
    scope.add("192.168.56.0/24")
    return PermissionManager(S(), scope), scope


def test_permission_in_scope_ok():
    pm, _ = _pm()
    d = pm.evaluate("nmap -sV 192.168.56.10", tool=DEFAULT_CATALOG.get("nmap"))
    assert d.allowed and not d.needs_confirm


def test_permission_labonly_out_of_scope_blocked():
    pm, _ = _pm()
    d = pm.evaluate('sqlmap -u "http://8.8.8.8/?id=1" --batch', tool=DEFAULT_CATALOG.get("sqlmap"))
    assert not d.allowed
    assert d.out_of_scope


def test_permission_enforce_mode_blocks_any_out_of_scope():
    pm, _ = _pm(scope_mode="enforce")
    d = pm.evaluate("nmap -sV 1.2.3.4", tool=DEFAULT_CATALOG.get("nmap"))
    assert not d.allowed


def test_permission_destructive_requires_confirm():
    pm, _ = _pm()
    d = pm.evaluate("rm -rf /tmp/x")
    assert d.allowed and d.needs_confirm and d.risk == "dangerous"


def test_permission_sudo_requires_confirm():
    pm, _ = _pm()
    d = pm.evaluate("sudo apt update")
    assert d.needs_confirm and d.uses_sudo
