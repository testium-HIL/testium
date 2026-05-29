"""Entry point for ``python -m testium.lsp`` (alternative to ``testium lsp``)."""

from lsp.server import serve

if __name__ == "__main__":
    serve()
