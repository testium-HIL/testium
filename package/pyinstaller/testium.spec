# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['../../src/testium/__main__.py'],
    pathex=['../../src/testium',
            '../../src/testium/main_win/resources'],
    binaries=[],
    # py_func/ and runtime/ are bundled at the _MEIPASS root because the
    # py_func subprocess is launched with the *host* Python (not the
    # frozen interpreter): it needs the source files on disk to find them
    # via cwd=subproc_path() and `python3 py_func` + `from runtime.*`.
    datas=[('../../src/VERSION', '.'),
           ('../../src/testium/lua_func', 'lua_func'),
           ('../../src/testium/py_func', 'py_func'),
           ('../../src/testium/runtime', 'runtime')],
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
                   "lxml"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    ico='../testium.png'
)
