
.. _sec_templates:

Templates
---------------------------

*testium* embeds the `jinja2 <https://jinja.palletsprojects.com>`_ template engine. It allows extensive customization of
test files and makes test scripts reusable.

Templates are rendered at load time.

In the main test file
^^^^^^^^^^^^^^^^^^^^^^^

The *testium* main test files are always passed through the jinja template engine.

The variables available to jinja are the
:ref:`configuration file<sec_configuration_files>` entries plus the
:ref:`built-in values<sec_global_variables_builtin>`. Jinja receives
their resolved values, as they are at load time.

In ``!include`` directive
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to basic inclusion, ``!include`` accepts arguments.
These arguments replace the corresponding ``{{ keyword }}`` placeholders in the included file.

.. code-block:: yaml
    :caption: including a template

    main:
        name: Test example
        steps:
            - test_item1:
                name: test_1

            #include can also be inserted directly within the steps list
            - !include
                file: included_template_file.tum
                inclusion_parameter_1: param1
                inclusion_parameter_2: param2


.. code-block:: yaml
    :caption: included template

    - test_item:
        name: {{ inclusion_parameter_1 }}
    - {{ inclusion_parameter_2 }}:
        name: test_3

Include arguments and resolution time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml
    :caption: calling file

    - !include {file: bench.tum, cfg: $(bench_config)}

.. code-block:: yaml+jinja
    :caption: bench.tum

    {% set _cfg = expand(cfg) %}
    {% if _cfg.mode == "fast" %}
    - sleep: {name: warmup, timeout: 0.1}
    {% endif %}

    - py_func:
        name: run bench
        file: bench.py
        func_name: run
        param:
            - {{ cfg }}

* An argument is passed to the template as declared: ``{{ cfg }}``
  writes the text ``$(bench_config)`` into the file.
* That text is resolved when the item runs, with the value in force at
  that moment. A later redefinition of ``bench_config`` applies.
* ``expand(value)`` resolves ``$( )`` and ``<| |>`` at load time. Use
  it to access the value inside the template itself: attribute access,
  ``{% if %}``, ``{% for %}``. ``expand()`` exists only in templates.
* Mixing the two syntaxes in one expression is not allowed:
  ``{{ $(inclusion)_parameter }}`` fails to load. Write the ``$( )``
  part as text and let it resolve at run time.
