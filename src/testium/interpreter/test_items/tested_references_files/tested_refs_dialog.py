import sys
from multiprocessing import freeze_support

from PySide6.QtWidgets import (QApplication, QDialog, QTableWidgetItem)
from PySide6.QtCore import (Qt, QSettings)

try:
    from interpreter.test_items.tested_references_files import tested_refs_win
except:
    import tested_refs_win

class TestedRefsWindow(QDialog, tested_refs_win.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

def main(args, conn=None):
    SettingsCompagny = 'Testium'
    SettingsApplication = 'testium_ref_item'
    SettingsLastReference = 'lastReference'
    success = True
    from interpreter.test_items import dialog_env
    dialog_env.setup()
    app = QApplication(['testium'])
    d = TestedRefsWindow()
    d.setFixedSize(481,386)
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
        conn.send([result, success])
        conn.close()
    else:
        print(result, end='')

    if hasattr(sys, "frozen"):
        #all standard streams are replaced by dummy one to avoid cx_freeze flushing bug.
        class dummyStream:
            ''' dummyStream behaves like a stream but does nothing. '''
            def __init__(self): pass
            def write(self,data): pass
            def read(self,data): pass
            def flush(self): pass
            def close(self): pass

        # and now redirect all default streams to this dummyStream:
        sys.stdout = dummyStream()
        sys.stderr = dummyStream()
        sys.stdin = dummyStream()
        sys.__stdout__ = dummyStream()
        sys.__stderr__ = dummyStream()
        sys.__stdin__ = dummyStream()

if __name__ == '__main__':
    main(sys.argv[1:])
