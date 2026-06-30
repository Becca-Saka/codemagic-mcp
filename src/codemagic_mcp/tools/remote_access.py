"""Remote access tools — SSH/VNC connection details for a build machine.

Remote access must be enabled when the build is STARTED (the "Enable SSH/VNC
access" checkbox in the Start new build modal — UI only, manual builds only;
https://docs.codemagic.io/troubleshooting/accessing-builder-machine-via-ssh/).
Credentials are ephemeral: the machine stays reachable for ~10 minutes after the
build finishes.
"""

import platform
import shutil
from typing import Any

from codemagic_mcp import transform
from codemagic_mcp.app import mcp
from codemagic_mcp.auth import AuthError, require_token
from codemagic_mcp.client import CmApiClient, CmApiError
from codemagic_mcp.tools.common import no_token

# Third-party VNC clients to look for on PATH (macOS also has built-in Screen Sharing).
_VNC_CLIENT_BINARIES = ("vncviewer", "remmina", "vinagre", "krdc", "tigervnc")

_NOT_ENABLED = ("No remote access for this build. It must be enabled with the "
                "'Enable SSH/VNC access' checkbox when starting the build (UI only, "
                "manual builds).")


def _detect_vnc_clients() -> list[str]:
    """VNC clients available on this machine (the one the MCP server runs on)."""
    found = [b for b in _VNC_CLIENT_BINARIES if shutil.which(b)]
    if platform.system() == "Darwin":
        found.insert(0, "Screen Sharing (built-in)")  # macOS ships a VNC client
    return found


def _install_prompt() -> dict[str, Any]:
    """Per-OS guidance to install a VNC client when none is found."""
    system = platform.system()
    if system == "Windows":
        rec = "Install VNC Viewer from https://www.realvnc.com/connect/download/viewer/"
    elif system == "Linux":
        rec = ("Install a VNC client, e.g. VNC Viewer "
               "(https://www.realvnc.com/connect/download/viewer/), Remmina, or vinagre.")
    else:  # Darwin / unknown
        rec = ("macOS includes Screen Sharing — open it with `open \"vnc://<host>:<port>\"` "
               "— or install VNC Viewer from https://www.realvnc.com/connect/download/viewer/")
    return {"action_required": "install_vnc_client", "recommendation": rec}


@mcp.tool
async def get_remote_access(build_id: str) -> dict[str, Any]:
    """Get SSH/VNC connection details for a running (or just-finished) build machine.

    Requires remote access to have been enabled when the build was started (the
    "Enable SSH/VNC access" checkbox — UI only, manual builds). Returns the SSH
    script URL and the VNC host/port/username/password. These are ephemeral: the
    machine is reachable only during the build and for ~10 minutes after it finishes.
    To actually connect, use connect_remote_access.
    """
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await client.get_remote_access(build_id)
    except CmApiError as e:
        if e.status_code == 400:  # not enabled for this build
            return {"build_id": build_id, "remote_access": None, "note": _NOT_ENABLED}
        return {"error": e.message, "status_code": e.status_code, "build_id": build_id}
    access = transform.remote_access(payload)
    if not access.get("ssh") and not access.get("vnc"):
        return {"build_id": build_id, "remote_access": None, "note": _NOT_ENABLED}
    return {"build_id": build_id, "remote_access": access}


@mcp.tool
async def connect_remote_access(build_id: str, method: str = "vnc") -> dict[str, Any]:
    """Help connect to a build machine's remote access via SSH or VNC.

    SSH: returns the command to run in your terminal before the build finishes.
    VNC: checks whether a VNC client is installed on this machine; if one is found it
    returns the connection details (and, on macOS, a launch command), otherwise it
    prompts you to install a client first.

    Args:
        build_id: The build to connect to (remote access must have been enabled).
        method: "ssh" or "vnc" (default "vnc").
    """
    method = method.lower()
    if method not in ("ssh", "vnc"):
        return {"error": "method must be 'ssh' or 'vnc'."}
    try:
        client = CmApiClient(require_token())
    except AuthError as e:
        return no_token(e)
    try:
        payload = await client.get_remote_access(build_id)
    except CmApiError as e:
        if e.status_code == 400:
            return {"build_id": build_id, "error": _NOT_ENABLED}
        return {"error": e.message, "status_code": e.status_code, "build_id": build_id}
    access = transform.remote_access(payload)

    if method == "ssh":
        ssh = access.get("ssh")
        if not ssh:
            return {"build_id": build_id, "error": "No SSH access for this build. " + _NOT_ENABLED}
        return {
            "build_id": build_id,
            "method": "ssh",
            "instructions": ("Run the generated script in your terminal before the build "
                             "finishes (on Windows use Git Bash):"),
            "command": f'bash <(curl -s "{ssh["script_url"]}")',
            "script_url": ssh["script_url"],
            "note": "Access expires ~10 minutes after the build finishes.",
        }

    # VNC
    vnc = access.get("vnc")
    if not vnc:
        return {"build_id": build_id, "error": "No VNC access for this build. " + _NOT_ENABLED}
    address = f"{vnc['host']}:{vnc['port']}"
    connection = {**vnc, "address": address}

    clients = _detect_vnc_clients()
    result: dict[str, Any] = {"build_id": build_id, "method": "vnc",
                              "vnc_clients_found": clients, "connection": connection}
    if not clients:
        # No client installed — prompt the user to install one before connecting.
        result["instructions"] = ("No VNC client found on this machine. Install one, then "
                                   f"connect to {address} with the username/password above.")
        result.update(_install_prompt())
        return result

    result["instructions"] = (f"Open your VNC client and connect to {address} using the "
                              "username and password above.")
    if platform.system() == "Darwin":
        # macOS Screen Sharing opens vnc:// URLs; it will prompt for the password.
        result["launch_command"] = f'open "vnc://{address}"'
    return result
