"""Inspect the contract of the installed Concat binary (read-only)."""
import json
import subprocess
from pathlib import Path

p = subprocess.Popen(
    [r"C:\Program Files\Concat\concat.exe", "--mcp", "headless"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW,
)
try:
    for i, (method, params) in enumerate([
        ("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                        "clientInfo": {"name": "arroba-probe", "version": "0.1.0"}}),
        ("tools/list", {}),
    ], 1):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n")
        p.stdin.flush()
        while True:
            line = p.stdout.readline()
            if not line:
                raise RuntimeError("Concat closed its pipe")
            response = json.loads(line)
            if response.get("id") == i:
                break
        if method == "tools/list":
            Path(__file__).with_name("installed-contract.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
            wanted = {"project_create", "media_probe", "media_import", "clips_add_sequence", "clip_add", "captions_add", "clip_transform", "export_start", "export_status", "project_close"}
            for tool in response["result"]["tools"]:
                if tool["name"] in wanted:
                    print(json.dumps(tool, ensure_ascii=False))
        else:
            print(json.dumps(response))
finally:
    p.terminate()
    p.wait(timeout=10)
