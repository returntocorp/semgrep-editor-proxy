import json
from functools import partial

import pytest_asyncio
from websockets.client import connect
from websockets.server import serve

from semgrep_editor_proxy.constants import MESSAGE_TEMPLATE
from semgrep_editor_proxy.proxy import proxy

CONFIG = {"command": "semgrep", "args": ["lsp"], "port": 8000}
ORIGINAL_FILE_CONTENT = """test
 test2
 test3
 test4
"""


CHANGED_FILE_CONTENT = """test
 test2!
 test3!
 test4
"""

FINAL_FILE_CONTENT = ""


@pytest_asyncio.fixture
async def server():
    proxy_server = partial(proxy, config=CONFIG)
    server = await serve(proxy_server, "localhost", CONFIG["port"])
    yield server
    server.close()
    await server.wait_closed()


async def _client(server):
    socket = next(iter(server.sockets)).getsockname()
    ws_uri = f"ws://localhost:{socket[1]}"
    return ws_uri


@pytest_asyncio.fixture
async def client(server):
    yield connect(await _client(server))


def lsp_initialize_message(tmp_path):
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": 1,
            "rootUri": f"file://{tmp_path}/",
        },
    }
    message = json.dumps(message)
    length = len(message.encode("utf-8"))
    return MESSAGE_TEMPLATE % (length, message)


def lsp_initialized_message():
    message = {"jsonrpc": "2.0", "id": 1, "method": "initialized", "params": {}}
    message = json.dumps(message)
    length = len(message.encode("utf-8"))
    return MESSAGE_TEMPLATE % (length, message)


def lsp_open_message(tmp_path):
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": f"file://{tmp_path}/test.txt",
                "languageId": "plaintext",
                "version": 1,
                "text": ORIGINAL_FILE_CONTENT,
            }
        },
    }
    message = json.dumps(message)
    length = len(message.encode("utf-8"))
    return MESSAGE_TEMPLATE % (length, message)


def lsp_did_change_message(tmp_path):
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "textDocument/didChange",
        "params": {
            "textDocument": {
                "uri": f"file://{tmp_path}/test.txt",
                "version": 2,
            },
            "contentChanges": [
                {
                    "range": {
                        "start": {"line": 1, "character": 6},
                        "end": {"line": 3, "character": 0},
                    },
                    "text": "!\n test3!\n",
                }
            ],
        },
    }
    message = json.dumps(message)
    length = len(message.encode("utf-8"))
    return MESSAGE_TEMPLATE % (length, message)


def lsp_did_change_full(tmp_path):
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "textDocument/didChange",
        "params": {
            "textDocument": {
                "uri": f"file://{tmp_path}/test.txt",
                "version": 2,
            },
            "contentChanges": [{"text": ""}],
        },
    }
    message = json.dumps(message)
    length = len(message.encode("utf-8"))
    return MESSAGE_TEMPLATE % (length, message)
