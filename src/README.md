# testium

testium is a YAML-driven test sequencer for hardware-in-the-loop and
integration testing. A test campaign is described in a `.tum` file as a tree
of items (checks, console interactions, Python/Lua functions, parallel blocks,
dialogs, …); testium executes the tree, captures results, and produces
reports in several formats.

![testium running a test session](https://raw.githubusercontent.com/testium-HIL/testium/main/doc/testium_session.gif)

```sh
pip install testium-hil
testium              # GUI mode
testium -b test.tum  # batch mode
```

Documentation, tutorials and pre-built binaries:
<https://github.com/testium-HIL/testium>
