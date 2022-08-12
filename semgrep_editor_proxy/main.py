#!/usr/bin/env python3

import asyncio

from semgrep_editor_proxy.proxy import run


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
