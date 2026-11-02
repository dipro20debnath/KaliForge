"""Permission manager — turns a raw command plus the current scope/settings
into a structured *decision* the UI can act on.

The manager never executes anything; it only decides what guard-rails apply.
The UI is responsible for showing the right confirmation dialog based on the
returned :class:`Decision`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core import command_utils as cu
from core.scope_manager import ScopeManager


@dataclass
class Decision:
    command: str
    allowed: bool = True            # may it run at all (after confirmations)?
    needs_confirm: bool = False     # should the UI show a confirm dialog?
    requires_scope: bool = False    # command touches a target that must be scoped
    out_of_scope: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    risk: str = "info"              # info | caution | dangerous
    dangerous_reasons: list[str] = field(default_factory=list)
    uses_sudo: bool = False
    reasons: list[str] = field(default_factory=list)   # why confirm / block
    blockers: list[str] = field(default_factory=list)  # hard blocks

    def summary(self) -> str:
        if not self.allowed:
            return "Blocked: " + "; ".join(self.blockers)
        if self.needs_confirm:
            return "Confirmation required: " + "; ".join(self.reasons)
        return "OK to run"


class PermissionManager:
    def __init__(self, settings, scope: ScopeManager, audit=None):
        self.settings = settings
        self.scope = scope
        self.audit = audit

    # ------------------------------------------------------------------ core
    def evaluate(self, command: str, tool: dict | None = None,
                 lab_only: bool | None = None) -> Decision:
        command = command.strip()
        decision = Decision(command=command)
        if not command:
            decision.allowed = False
            decision.blockers.append("empty command")
            return decision

        targets = cu.extract_targets(command)
        decision.targets = targets
        decision.uses_sudo = cu.uses_sudo(command)
        decision.dangerous_reasons = cu.dangerous_reasons(command)

        if lab_only is None:
            lab_only = bool(tool.get("lab_only")) if tool else False
        tool_risk = (tool.get("risk") if tool else None) or "info"

        # --- risk classification -------------------------------------------
        if decision.dangerous_reasons:
            decision.risk = "dangerous"
        elif tool_risk == "dangerous" or lab_only:
            decision.risk = "dangerous" if tool_risk == "dangerous" else "caution"
        else:
            decision.risk = tool_risk

        # --- scope enforcement ---------------------------------------------
        scope_mode = self.settings.get("security.scope_mode", "warn") if self.settings else "warn"
        require_for_lab = self.settings.get("security.require_scope_for_lab_only", True) if self.settings else True

        if targets:
            _, denied = self.scope.check_targets(targets)
            decision.out_of_scope = denied
            if denied:
                decision.requires_scope = True
                # lab-only / dangerous tools: out-of-scope is a hard block in
                # enforce mode and whenever require_for_lab applies.
                hard = (scope_mode == "enforce") or (lab_only and require_for_lab)
                if hard:
                    decision.allowed = False
                    decision.blockers.append(
                        "target(s) not in authorised scope: " + ", ".join(denied)
                    )
                else:
                    decision.needs_confirm = True
                    decision.reasons.append(
                        "target(s) outside the defined scope: " + ", ".join(denied)
                    )

        # --- destructive confirmation --------------------------------------
        confirm_destructive = self.settings.get("security.confirm_destructive", True) if self.settings else True
        if decision.dangerous_reasons and confirm_destructive:
            decision.needs_confirm = True
            decision.reasons.extend(decision.dangerous_reasons)

        # --- sudo confirmation ---------------------------------------------
        confirm_sudo = self.settings.get("security.confirm_sudo", True) if self.settings else True
        if decision.uses_sudo and confirm_sudo:
            decision.needs_confirm = True
            decision.reasons.append("command runs with elevated (sudo) privileges")

        # --- lab-only / dangerous tool confirmation ------------------------
        if decision.allowed and decision.risk == "dangerous" and not decision.needs_confirm:
            decision.needs_confirm = True
            decision.reasons.append("high-impact tool — confirm authorised use")

        return decision

    def log_decision(self, decision: Decision, source: str, tool_id: str = "",
                     resolved: str = "", workspace_id: int | None = None) -> None:
        if self.audit is None:
            return
        self.audit.record(
            source=source, tool=tool_id, command=decision.command,
            targets=", ".join(decision.targets), risk=decision.risk,
            decision=resolved or decision.summary(),
            detail="; ".join(decision.reasons + decision.blockers),
            workspace_id=workspace_id,
        )
