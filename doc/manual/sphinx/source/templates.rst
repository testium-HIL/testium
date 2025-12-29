
Templates
---------------------------

*testium* embeds the `jinja2 <hhttps://jinja.palletsprojects.com>`_ template engine. It allows a great customization of the
test files, and enforces reusability of test scripts.

In the main test file
^^^^^^^^^^^^^^^^^^^^^^^

The *testium* main test files are systematically passed through the jinja template engine.

The parameters passed to jinja are all the variables contained into the
:ref:`configuration files<sec_configuration_files>` plus the
:ref:`built-in values<sec_global_variables_builtin>`.

In ``!include`` directive
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Along with the basic inclusion capability, there is the possibility to use file inclusion parameters.
Theses parameters are replacing corresponding keywords in bracket in the included file.

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

