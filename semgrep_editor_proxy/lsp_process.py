import asyncio
from asyncio.subprocess import Process
from typing import Optional

from semgrep_editor_proxy.constants import MESSAGE_TEMPLATE
from semgrep_editor_proxy.util import content_length
from semgrep_editor_proxy.util import start_process


class LSPProcess:
    def __init__(self, command: str, args: Optional[list[str]] = None) -> None:
        self.command = command
        self.args = args
        self._write_lock = asyncio.Lock()
        self.process: Optional[Process] = None
        self.uri_map: dict[str, str] = {}

    async def start(self) -> None:
        self.process = await start_process(self.command, self.args)

    async def stop(self) -> None:
        if self.process is None:
            raise ValueError("process has not been started")
        self.process.terminate()
        await self.process.wait()

    async def read_stdout(self) -> str:
        if self.process is None:
            raise ValueError("process has not been started")
        if self.process.stdout is None:
            raise ValueError("stdout is None")
        line = await self.process.stdout.readline()
        if not line:
            raise ValueError("stdout is empty")
        length = content_length(line.decode("utf-8"))
        # Blindly consume all header lines
        while line and line.strip():
            line = await self.process.stdout.readline()
        return (await self.process.stdout.read(length)).decode("utf-8")

    async def write_stdin(self, data: str) -> None:
        if self.process is None:
            raise ValueError("process has not been started")
        if not self.process.stdin:
            raise ValueError("stdin is None")
        await self._write_lock.acquire()
        # Ensure we get the byte length, not the character length
        body = data
        # Ensure we get the byte length, not the character length
        content_length = (
            len(body) if isinstance(body, bytes) else len(body.encode("utf-8"))
        )

        request = MESSAGE_TEMPLATE % (content_length, body)

        self.process.stdin.write(request.encode("utf-8"))
        await self.process.stdin.drain()
        self._write_lock.release()
