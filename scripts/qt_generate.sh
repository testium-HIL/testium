#!/bin/bash

SCRIPT_DIR=$(realpath $( dirname "$0"))
MAIN_DIR=${SCRIPT_DIR}/../src/testium

EXE_UI=pyside6-uic
EXE_RCC=pyside6-rcc

UIFILES="main_win/testium_core_win.ui"
UIFILES+=" main_win/about_win/about_win.ui"
UIFILES+=" main_win/preference_win/preference_core_win.ui"
UIFILES+=" main_win/f1_win/f1_win_core.ui"
UIFILES+=" interpreter/test_items/dialog_choices_files/choices_dialog_win.ui"
UIFILES+=" interpreter/test_items/dialog_image_files/dialog_image_win.ui"
UIFILES+=" interpreter/test_items/dialog_note_files/dialog_note_win.ui"
UIFILES+=" interpreter/test_items/dialog_sleep_files/dialog_sleep_win.ui"
UIFILES+=" interpreter/test_items/dialog_value_files/dialog_value_win.ui"
UIFILES+=" interpreter/test_items/tested_references_files/tested_refs_win.ui"

RCFILES="main_win/resources/testium_core_win.qrc"
RCFILES+=" main_win/resources/about_win.qrc"
RCFILES+=" main_win/resources/f1_win.qrc"

for f in ${UIFILES}
do
    ${EXE_UI} "${MAIN_DIR}/$f" > "${MAIN_DIR}/${f%.*}.py"
done

for f in ${RCFILES}
do
    ${EXE_RCC} "${MAIN_DIR}/$f" > "${MAIN_DIR}/${f%.*}_rc.py"
done
