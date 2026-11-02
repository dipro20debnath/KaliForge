"""Learning & Practice Mode backend — serves per-tool learning modules and a
command explainer that breaks a command into its program, flags and arguments
with plain-language descriptions."""
from __future__ import annotations

from dataclasses import dataclass, field

from core import command_utils as cu
from tools.learning_data import FLAGS, GENERIC_FLAGS, MODULES


@dataclass
class ExplainPart:
    token: str
    role: str           # program | flag | value | target | subcommand
    description: str = ""


@dataclass
class Explanation:
    command: str
    program: str
    parts: list[ExplainPart] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    summary: str = ""


def modules_for(tool_id: str) -> list[dict]:
    return MODULES.get(tool_id, [])


def has_learning(tool_id: str) -> bool:
    return tool_id in MODULES


def learnable_tool_ids() -> list[str]:
    return sorted(MODULES.keys())


def explain(command: str) -> Explanation:
    """Explain a shell command token by token."""
    command = command.strip()
    tokens = cu.tokenize(command)
    program = cu.program_name(command)
    targets = cu.extract_targets(command)
    exp = Explanation(command=command, program=program, targets=targets)

    flag_map = FLAGS.get(program, {})
    seen_program = False
    for i, token in enumerate(tokens):
        if token == "sudo":
            exp.parts.append(ExplainPart(token, "program", "run with elevated privileges"))
            continue
        if not seen_program and token == program:
            exp.parts.append(ExplainPart(token, "program", f"the {program} tool"))
            seen_program = True
            continue
        if token in targets:
            exp.parts.append(ExplainPart(token, "target", "the target being acted on"))
            continue
        if token.startswith("-"):
            key = token.split("=", 1)[0]
            desc = flag_map.get(key) or flag_map.get(token) or GENERIC_FLAGS.get(key, "")
            exp.parts.append(ExplainPart(token, "flag", desc or "option flag"))
            continue
        # subcommand right after the program (e.g. gobuster dir, dig ANY)
        if token in flag_map:
            exp.parts.append(ExplainPart(token, "subcommand", flag_map[token]))
            continue
        exp.parts.append(ExplainPart(token, "value", "argument / value"))

    described = [p for p in exp.parts if p.role in ("flag", "subcommand") and p.description not in ("", "option flag")]
    if program and (flag_map or described):
        exp.summary = (f"Runs {program}" +
                       (f" against {', '.join(targets)}" if targets else "") +
                       (f" with {len(described)} explained option(s)." if described else "."))
    else:
        exp.summary = (f"Runs {program}." if program else "No recognised program.")
    return exp
