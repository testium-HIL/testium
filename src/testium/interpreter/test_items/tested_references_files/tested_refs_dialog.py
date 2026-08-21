import sys
from multiprocessing import freeze_support

from PySide6.QtWidgets import (QApplication, QDialog, QTableWidgetItem)
from PySide6.QtCore import Qt, QSettings, QTimer

try:
    from interpreter.test_items.tested_references_files import tested_refs_win
except:
    import tested_refs_win

class TestedRefsWindow(QDialog, tested_refs_win.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

def main(args, conn=None):
    from interpreter.utils.settings import host_id
    SettingsCompagny = 'Testium'
    # Per-host storage, like TestiumSettings (network home shared by PCs).
    SettingsApplication = 'testium_ref_item.' + host_id()
    SettingsLastReference = 'lastReference'
    success = True
    from interpreter.test_items.dialog_presenter import (
        mute_frozen_streams)
    from interpreter.test_items import dialog_env
    dialog_env.setup()
    app = QApplication(['testium'])
    d = TestedRefsWindow()
    d.resize(481, 386)
    d.setMinimumSize(400, 300)
    d.setWindowFlags(Qt.WindowStaysOnTopHint)
    d.setWindowTitle(args[0])
    d.labelDialog.setText(args[1])
    d.tableReferences.horizontalHeader().setStretchLastSection(True)

    settings = QSettings(SettingsCompagny, SettingsApplication)
    last_reference = settings.value(SettingsLastReference, '')

    last_rows_content = last_reference.split(sep=',')
    args_rows_content = args[2].split(sep=',')

    d.tableReferences.setRowCount(len(args_rows_content))
    i = 0
    for row in args_rows_content:
        j = 0
        for val in row.split('/'):
            d.tableReferences.setItem(i, j, QTableWidgetItem(val))
            j += 1
        j = 0
        if i < len(last_rows_content):
            last_row = last_rows_content[i]
            for val in last_row.split('/'):
                if d.tableReferences.item(i, j) is None:
                    d.tableReferences.setItem(i, j, QTableWidgetItem(val))
                j += 1
        i += 1

    d.tableReferences.setFocus()
    auto_result = args[3] if len(args) > 3 else None
    if auto_result is not None:
        QTimer.singleShot(2000, lambda: d.accept() if auto_result.lower() == 'ok' else d.reject())
    dres = d.exec()

    if dres == QDialog.Rejected:
        success = False

    #build the answer:
    row_items=[]
    for i in range(d.tableReferences.rowCount()):
        col_items=[]
        for j in range(d.tableReferences.columnCount()):
            try:
                col_items.append(d.tableReferences.item(i,j).text())
            except:
                col_items.append('')

        row_items.append('/'.join(col_items))

    result=','.join(row_items)

    if conn:
        settings.setValue(SettingsLastReference, result)
        # Flush to disk *before* handing the result back: as soon as the parent
        # receives it on the pipe it terminates this subprocess (SIGTERM, no
        # handler), so the QSettings destructor never runs. Without sync() the
        # write races the kill and is lost — reliably so under Flatpak, where
        # the .conf is atomically renamed on the slower ~/.var/app overlay.
        settings.sync()
        conn.send([result, success])
        conn.close()
    else:
        print(result, end='')

    mute_frozen_streams()

if __name__ == '__main__':
    main(sys.argv[1:])
