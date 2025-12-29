# Documentation

[See here](doc/manual/testium_manual.pdf).

# Installation

## Installation from local pypi repository

### Virtualenv

It is strongly recommended to create a python virtual environment to be able to install testium with pip.

This method is also required for git sources install and debug.

#### Virtualenv setup

Creation of the python virtual environment:

    python3 -m venv <my_venv_dir>/<my_python_venv>

Each time it is needed to enter the virtual environment, just execute:

    source <my_venv_dir>/<my_python_venv>/bin/activate

this line can also be inserted in the `.bashrc` to be automatically called in a linux terminal.

It is possible to configure the *code* IDE to use this virtual environment by setting it
in the preferences: "File->Settings", search "venv", then setup the virtual env.

And when properly set, you can select the interpreter from your newly created venv.

### install testium

From the python virtual environment run:

    pip install testium

all the dependencies are automatically installed in the virtual env.

### run testium

From the python virtual environment just run:

    python -m testium

or simply

    testium

## Installation from sources

The python virtual environment should be installed first (see above).

### Requirements

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

### Git repository

Clone testium from the company's git repository.

### Tagged version

In the case testium must be executed at a given release, the tagged version
is expected.

To know the tags which exist for the software, just execute the following command in the `testium` directory:

    $ git tag --list

Then the list of tags is displayed.

To switch to the considered tag, execute the following commands:

    $ git checkout <tag_name>

If you want to be sure that you're on the right tag, just execute:
    $ git status

And the console may return:

    HEAD detached at <tag_name>
    nothing to commit, working tree clean
    $

### Execution from sources

**Windows**

    $ python.exe <path_to_testium>\src\testium

**Linux**

    $ python <path_to_testium>/src/testium

# Documentation generation

This section describes how to generate the documentation.

The testium's user's manual is genearted with the help of the sphinx
framework.

## Install sphinx

    pip install sphinx

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
3. Then got to the "RUN AND DEBUG" tab and press the play button.
4. A testium window will pops up ; start execution of your tum.
5. Do not forget to put breakpoints where you want to investigate.

## Icons

Icons are coming from the following site: https://github.com/free-icons/free-icons.git

# testium Release

## Pre-requisite

A `python` virtual environment must have been set as described above.

### Install appimage-builder

Install `appimage-builder` package using pip.

### Install pyinstaller

Install `pyinstaller` package using pip.

## Generate the binary package

The procedure for a binary release is as follows:

1. update the `release_note.txt` file
2. modify the version in `src/VERSION` file
3. be sure that the documentation is up to date, and if not execute `doc/manual/sphinx/build_doc.sh` script
4. push modifications and create a tag with the new version on the git repository
5. generate an appimage by calling `package/appimage/./build.sh`
6. generate an executable file by calling `package/pyinstaller/./build.sh`
7. run the complete validation test for each generated binary
8. check that all the validation results are OK
9. On artifactory add the following files to a new testium version:

    * release note
    * testium binary(ies)
    * testium user's manual
    * validation results

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
