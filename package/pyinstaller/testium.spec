# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

# Language-server dependencies for `testium lsp`. pygls/lsprotocol register
# converters and features dynamically, so we collect their submodules wholesale
# and force-import their pure-python deps (cattrs/attrs/typing_extensions).
# The testium lsp modules are imported lazily by the CLI dispatch
# (`from lsp.server import serve`), which PyInstaller's static analysis misses —
# hence the explicit names. No source files need bundling: the schema export is
# now fully declarative (PARAMS + ACTIONS class attributes), so it no longer
# reads .py source via inspect.getsource (which fails in a frozen build).
_LSP_HIDDEN = (
    collect_submodules("pygls")
    + collect_submodules("lsprotocol")
    + ["cattrs", "attr", "attrs", "typing_extensions",
       "lsp", "lsp.server", "lsp.schema"]
)

# junit_xml is imported by post_exec scripts running under the *host* Python,
# not the frozen interpreter — so bundling it via hiddenimports alone is not
# enough. We also drop its source files at the _MEIPASS root so the host
# python3 finds them via the PYTHONPATH that py_process.py sets to
# tstium_path (= _MEIPASS when frozen).
import junit_xml as _junit_xml
JUNIT_XML_DIR = os.path.dirname(_junit_xml.__file__)

a = Analysis(
    ['../../src/testium/__main__.py'],
    pathex=['../../src/testium',
            '../../src/testium/main_win/resources'],
    binaries=[],
    # py_func/ and runtime/ are bundled at the _MEIPASS root because the
    # py_func subprocess is launched with the *host* Python (not the
    # frozen interpreter): it needs the source files on disk to find them
    # via cwd=subproc_path() and `python3 py_func` + `from runtime.*`.
    # py_func/, lua_func/ and runtime/ are bundled at the _MEIPASS root
    # because the py_func subprocess is launched with the *host* Python
    # (not the frozen interpreter): it needs the source files on disk to
    # find them via cwd=subproc_path() and `python3 py_func` +
    # `from runtime.*`. api/ and interpreter/ are intentionally NOT
    # exposed: user py_func scripts must go through py_func.tm
    # (JSON-RPC bridge) for any testium API call.
    datas=[('../../src/VERSION', '.'),
           ('../../src/testium/lua_func', 'lua_func'),
           ('../../src/testium/py_func', 'py_func'),
           ('../../src/testium/runtime', 'runtime'),
           (JUNIT_XML_DIR, 'junit_xml')],
    hiddenimports=["git",
                   "interpreter",
                   "main_win",
                   "runtime",
                   "py_func",
                   "py_func.tm",
                   "py_func.handle",
                   "py_func.func_call",
                   "api",
                   "api.console",
                   "api.termconsole",
                   "api.console_ssh",
                   "api.raw_tcp_console",
                   "api.runtime_plot",
                   "api.testium",
                   "matplotlib.backends.backend_pdf",
                   "telnetlib3",
                   "serial",
                   "yaml",
                   "pexpect",
                   "jinja2",
                   "colorama",
                   "matplotlib",
                   "junit_xml",
                   "lxml"] + _LSP_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

# TESTIUM_ONEDIR=1 => one-folder build (fast startup), used by the Windows
# installer; default one-file keeps the Linux build_all portable binary.
ONEDIR = bool(os.environ.get("TESTIUM_ONEDIR"))
# UPX skipped via TESTIUM_NO_UPX (build_all --ram) — slow for a marginal gain.
_upx = not os.environ.get("TESTIUM_NO_UPX")

if ONEDIR:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='testium',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=_upx,
        upx_exclude=[],
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        ico='../testium.ico'
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=_upx,
        upx_exclude=[],
        name='testium',
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='testium',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=_upx,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        ico='../testium.ico'
    )
