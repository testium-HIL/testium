# Documentation

[See here](doc/manual/testium_manual.pdf).

# run testium

From the root path, on windows `cmd`:

    run.bat

On windows powershell:

    run.ps1

On linux:

    ./run.sh

The virtual environment is created if needed and *testium* is started.

# Manual setup

A python virtual environment should be created:

    python3 -m venv <testium_venv>

## Requirements

In the virtual environment, the following modules must be installed:

* pyside6
* pyserial
* pyyaml
* pexpect
* gitpython
* jinja2
* colorama
* matplotlib
* junit-xml
* lxml

A `requirements.txt` file is also available in the git repository in the path `testium/src/`.


## run testium

from the testium path, execute

    python3 -m src/testium

# Doc generation

## Install sphinx

    pip install sphinx linuxdoc

## Generate the doc

Execute

    doc/manual/sphinx/./build_doc.sh

This command works if texlive package has been installed on the system. It can be done by invoking the following command.

    sudo apt install texlive-full

# QT GUI

## QT GUI modification

Open the ".ui" file with `qtcreator` and modify the gui. Then regenerate the python code.

On linux, a helper script has been created:
    scripts/./qt_generate.sh

# Debugging

In order to debug testium or your python script executed within testium.

## In VSCODE

This is the prefered method :

1. Create a debug configuration like the following:

```
    "configurations": [
        {
            "name": "Python : testium",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/testium",
            "console": "integratedTerminal",
            "args": ["-g"],
            "justMyCode": true
        },
    ]
```

2. Install debugpy module in python

   python -m pip install debugpy
3. Then get to the "RUN AND DEBUG" tab and press the play button.
4. A testium window will pops up ; start execution of your tum.
5. Do not forget to put breakpoints where you want to investigate.

## Icons

Icons are coming from the following site: https://github.com/free-icons/free-icons.git

# testium Release

## Pre-requisite

A `python` virtual environment must have been set as described above.

### Install pyinstaller

Install `pyinstaller` package using pip.

## Generate the binary package

The procedure for a binary release is as follows:

1. update the `release_note.txt` file
2. modify the version in `src/VERSION` file
3. be sure that the documentation is up to date, and if not execute `doc/manual/sphinx/build_doc.sh` script
4. push modifications and create a tag with the new version on the git repository
5. generate an executable file by calling `package/pyinstaller/./build.sh`
6. run the complete validation test for each generated binary
7. check that all the validation results are OK

# Troubleshooting

## The testium exe crashes `wl_proxy_marshal_flags`

### Error message

    /testium: symbol lookup error: /tmp/_MEIOhDCPF/libQt6WaylandClient.so.6: undefined symbol: wl_proxy_marshal_flags

### Solution

Set the appropriate environment variable

    export QT_QPA_PLATFORM=xcb
    testium

## xcb plugin missing

### Error message

    qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.

### Solution

A package is missing

    sudo apt install libxcb-cursor0
    sudo apt-get install libicu-dev
    sudo apt-get install libxcb-cursor-dev

## The testium appimage crashes when opening a file

This is usually because wayland is defined as the default X server.

To change it :

* Disable Wayland by uncommenting WaylandEnable=false in the `/etc/gdm3/daemon.conf`
* Add `QT_QPA_PLATFORM=xcb` in `/etc/environment`
* After a reboot, check that the environment variable value returns `x11`:

  $ echo $XDG_SESSION_TYPE
  x11
