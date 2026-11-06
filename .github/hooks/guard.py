"""preToolUse hook: determinisztikus védőkorlát a coding agent köré.

stdin:  {"toolName": ..., "toolArgs": ...}  (Copilot preToolUse esemény)
stdout: {} (nincs döntés) | {"permissionDecision": "deny"|"ask", "permissionDecisionReason": "..."}
"""
import json
import re
import sys

DENY = [
    (r"git\s+push", "Push csak emberi jóváhagyással, a terminálból."),
    (r"rm\s+-rf|Remove-Item\s+.*-Recurse", "Rekurzív törlés tiltott."),
    (r"(?:^|[\s/\\\"'])(?:scenarios|eval[/\\]cases)[/\\]", "A forgatókönyveket és a golden setet nem módosíthatja agent."),
    (r"@pytest\.mark\.skip|deleted file mode .*tests/", "Teszt kikapcsolása vagy törlése tiltott."),
]
ASK_TOOLS = ("create_issue", "propose_patch")


def main():
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("{}")
        return
    name = str(event.get("toolName", ""))
    args = json.dumps(event.get("toolArgs", ""), ensure_ascii=False)
    for rx, reason in DENY:
        if re.search(rx, args):
            print(json.dumps({"permissionDecision": "deny", "permissionDecisionReason": reason}, ensure_ascii=False))
            return
    if name.endswith(ASK_TOOLS):
        print(json.dumps({"permissionDecision": "ask",
                          "permissionDecisionReason": "Mellékhatással járó MCP tool – nézd át a tartalmát."}, ensure_ascii=False))
        return
    print("{}")


if __name__ == "__main__":
    main()
