
Includes
---------

It is possible to include TUM files from another one by using the ``!include`` tag before the included file.

This feature is a testium specific implementation and is not part of the YAML language,
although it is based on the tagging feature of the language and the customization possibility
offered by the python pyYaml package.

Here is a basic example of file inclusion:

.. code-block:: yaml
    :caption: included_file.tum

    - test_item:
        name: test_2
    - test_item:
        name: test_3


.. code-block:: yaml
    :caption: main.tum

    #include with the sub-sequence reference mechanism
    sequence: &included_sequence
        !include included_file.tum

    main:
        name: Test example
        steps:
            - test_item1:
                name: test_1
            - *included_sequence

            #include can also be inserted directly within the steps list
            - !include included_file.tum