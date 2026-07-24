
Templates
---------------------------

*testium* embeds the `jinja2 <https://jinja.palletsprojects.com>`_ template engine. It allows extensive customization of
test files and makes test scripts reusable.

In the main test file
^^^^^^^^^^^^^^^^^^^^^^^

The *testium* main test files are always passed through the jinja template engine.

The parameters passed to jinja are all the variables contained into the
:ref:`configuration files<sec_configuration_files>` plus the
:ref:`built-in values<sec_global_variables_builtin>`.

In ``!include`` directive
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to basic inclusion, ``!include`` accepts parameters.
These parameters replace the corresponding ``{{ keyword }}`` placeholders in the included file.

See examples below.

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
    # The following construction is not allowed and will fail to load:
    - test_item:
        name: {{ $(inclusion)_parameter_3 }}

