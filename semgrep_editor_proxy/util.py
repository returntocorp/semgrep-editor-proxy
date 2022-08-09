import asyncio
import json
from asyncio.subprocess import Process
from typing import Any
from typing import Optional


def content_length(line: str) -> int:
    """Extract the content length from an input line."""
    if line.startswith("Content-Length: "):
        _, value = line.split("Content-Length: ")
        value = value[: value.find("\r")]
        value = value.strip()
        try:
            return int(value)
        except ValueError as e:
            raise ValueError(f"Invalid Content-Length header: {value}") from e

    raise ValueError("No Content-Length header found")


def get_content(message: str) -> dict[str, Any]:
    length = content_length(message)
    message = message.encode("utf-8")[-length:].decode("utf-8")
    data: dict[str, Any] = json.loads(message)
    return data


async def start_process(command: str, args: Optional[list[str]] = None) -> Process:

    cmd = f"{command} {' '.join(args)}" if args else command
    return await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
