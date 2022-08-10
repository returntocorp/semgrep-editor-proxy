import glob
import json
import os
from asyncio import sleep
from pathlib import Path

import pytest
from websockets.client import connect

from tests.conftest import _client
from tests.conftest import CHANGED_FILE_CONTENT
from tests.conftest import FINAL_FILE_CONTENT
from tests.conftest import lsp_did_change_full
from tests.conftest import lsp_did_change_message
from tests.conftest import lsp_initialize_message
from tests.conftest import lsp_initialized_message
from tests.conftest import lsp_open_message
from tests.conftest import ORIGINAL_FILE_CONTENT


@pytest.mark.asyncio
async def test_proxy(client, tmp_path):
    async with client as c:
        await c.send(lsp_initialize_message(tmp_path))
        response = await c.recv()
        request_data = json.loads(response)
        assert "result" in request_data
        assert "capabilities" in request_data["result"]
        assert "textDocumentSync" in request_data["result"]["capabilities"]
        assert "serverInfo" in request_data["result"]


@pytest.mark.asyncio
async def test_multiple(server, tmp_path):
    for _ in range(0, 5):
        print(lsp_initialize_message(tmp_path))
        await test_proxy(connect(await _client(server)), tmp_path)


@pytest.mark.asyncio
async def test_open_sync(client, tmp_path):
    async with client as c:
        await c.send(lsp_initialize_message(tmp_path))
        _ = await c.recv()
        await c.send(lsp_initialized_message())
        _ = await c.recv()
        await c.send(lsp_open_message(tmp_path))
        response = await c.recv()
        request_data = json.loads(response)
        assert "error" not in request_data
        # Needed for possibly async race condition
        # This wouldn't happen outside testing
        await sleep(0.5)
        list_of_files = glob.glob("/tmp/semgrep_editor_proxy/**/test.txt")
        latest_file = max(list_of_files, key=os.path.getctime)
        assert os.path.exists(latest_file)
        assert open(latest_file).read() == ORIGINAL_FILE_CONTENT

        await c.send(lsp_did_change_message(tmp_path))
        response = await c.recv()
        request_data = json.loads(response)
        assert "error" not in request_data
        await sleep(0.5)
        assert open(latest_file).read() == CHANGED_FILE_CONTENT

        await c.send(lsp_did_change_full(tmp_path))
        response = await c.recv()
        request_data = json.loads(response)
        assert "error" not in request_data
        await sleep(0.5)
        assert open(latest_file).read() == FINAL_FILE_CONTENT

    await sleep(0.5)
    # Make sure the file was cleaned up
    assert not Path(latest_file).parent.exists()
