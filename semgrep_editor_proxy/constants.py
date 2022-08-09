WHITELISTED_LSP_METHODS = [
    "initialize",
    "initialized",
    "textDocument/didOpen",
    "textDocument/didChange",
    "textDocument/didClose",
]

SUPPORTED_LANGUAGES = ["python"]

MESSAGE_TEMPLATE = (
    f"Content-Length: %s\r\n"
    f"Content-Type: application/vscode-jsonrpc; charset=utf8\r\n\r\n"
    f"%s"
)
