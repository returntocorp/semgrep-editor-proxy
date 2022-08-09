import asyncio
import json
import sys
from functools import partial
from os import environ
from pathlib import Path
from shutil import rmtree
from typing import Any
from urllib import parse

import yaml
from websockets.exceptions import ConnectionClosed
from websockets.server import serve
from websockets.server import WebSocketServerProtocol
from websockets.typing import Data

from semgrep_editor_proxy.constants import MESSAGE_TEMPLATE
from semgrep_editor_proxy.constants import WHITELISTED_LSP_METHODS
from semgrep_editor_proxy.lsp_process import LSPProcess
from semgrep_editor_proxy.util import get_content

ClientConnection = tuple[int, LSPProcess]
Config = dict[str, Any]


def validate_request(
    request: Data, client_connection: ClientConnection
) -> dict[str, Any]:
    request_data = ""
    if not isinstance(request, str):
        request_data = request.decode("utf-8")
    else:
        request_data = request
    data = get_content(request_data)
    assert data["jsonrpc"] == "2.0"
    assert data["id"] is not None
    assert data["method"] is not None
    assert data["method"] in WHITELISTED_LSP_METHODS
    if "textDocument" in data["params"]:
        assert data["params"]["textDocument"]["uri"] is not None
        path = parse.urlparse(data["params"]["textDocument"]["uri"]).path
        # Rewrite uri
        data["params"]["textDocument"][
            "uri"
        ] = f"file:///tmp/semgrep_editor_proxy/{client_connection[0]}/{Path(path).name}"
    return data


def sync_document(document: dict[str, Any]) -> None:
    if "textDocument" not in document["params"]:
        return
    if "uri" not in document["params"]["textDocument"]:
        return
    if (
        "text" not in document["params"]["textDocument"]
        and "contentChanges" not in document["params"]
    ):
        return
    uri = document["params"]["textDocument"]["uri"]
    path = Path(parse.urlparse(uri).path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = None
    changes = None
    if "text" in document["params"]["textDocument"]:
        text = document["params"]["textDocument"]["text"]
    else:
        changes = document["params"]["contentChanges"]
    with open(path, "a+") as f:
        f.seek(0)
        if text:
            f.truncate()
            f.write(text)
            f.flush()
        elif changes:
            buff = f.readlines()
            for change in changes:
                if "range" not in change:
                    to_write = change["text"]
                else:
                    start_line = change["range"]["start"]["line"]
                    start_col = change["range"]["start"]["character"]
                    end_line = change["range"]["end"]["line"]
                    end_col = change["range"]["end"]["character"]

                    # Truncate lines at the start and end of the range
                    buff[start_line] = buff[start_line][:start_col]
                    buff[end_line] = buff[end_line][end_col:]

                    # Remove lines in the middle of the range
                    buff_first_half = "".join(buff[: start_line + 1])
                    buff_second_half = "".join(buff[end_line:])

                    # Insert the new lines
                    to_write = buff_first_half + change["text"] + buff_second_half
                f.seek(0)
                f.truncate()
                f.write(to_write)
                f.flush()


async def process_request(data: Data, client_connection: ClientConnection) -> None:
    request = validate_request(data, client_connection)
    sync_document(request)
    await client_connection[1].write_stdin(json.dumps(request))


async def process_response(client_connection: ClientConnection) -> Data:
    response = await client_connection[1].read_stdout()

    response = MESSAGE_TEMPLATE % (len(response.encode("utf-8")), response)
    return response


# Seperate out websocket logic for easier testing


async def request_handler(
    websocket: WebSocketServerProtocol, client_connection: ClientConnection
) -> None:
    while True:
        data = await websocket.recv()
        await process_request(data, client_connection)


async def response_handler(
    websocket: WebSocketServerProtocol, client_connection: ClientConnection
) -> None:
    while True:
        response = await process_response(client_connection)
        await websocket.send(response)


async def proxy(websocket: WebSocketServerProtocol, config: Config) -> None:
    process = LSPProcess(config["command"], config["args"])
    print(f"Starting process with command: {process.command}")
    await process.start()
    print("Process started")
    connection_id = hash(websocket.remote_address)
    print(f"Connection id: {connection_id}")
    # Assuming this is unique
    client_connection = (connection_id, process)
    try:
        request = asyncio.create_task(request_handler(websocket, client_connection))

        response = asyncio.create_task(response_handler(websocket, client_connection))
        await asyncio.gather(request, response)
    except ConnectionClosed:
        print(f"Connection {connection_id} closed")
    finally:
        path = Path(f"/tmp/semgrep_editor_proxy/{connection_id}")
        rmtree(path)


async def run() -> None:
    # Do config/cli stuff here
    if len(sys.argv) == 3:
        print(sys.argv)
        config_file = open(sys.argv[2])
    elif environ.get("LSP_PROXY_CONFIG"):
        config_file = open(environ["LSP_PROXY_CONFIG"])
    else:
        print("No config file specified")
        sys.exit(1)
    # Should use CLoader here if we really cared
    configs = yaml.safe_load(config_file)
    servers = set()
    for config in configs["servers"]:
        print(config)
        proxy_server = partial(proxy, config=config)
        server = await serve(proxy_server, "", config["port"])
        servers.add(server)
    await asyncio.Future()  # run forever
