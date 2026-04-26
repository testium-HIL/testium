#!/usr/bin/env python
import sys
import os
import multiprocessing
from pathlib import Path

ourpath = Path(__file__)
ourpath = ourpath.resolve()
sys.path.append(os.path.abspath(ourpath.parent))

import interpreter.utils.constants as cst

def main():
    # This line sets the method for the "Process" function. It is required for Linux
    # support of the test dialogs.
    multiprocessing.set_start_method('spawn')

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--version",
                        help="Returns the version of testium", action='store_true')
    parser.add_argument("-b", "--batch-execution",
                        help="Executes the test in batch mode", action='store_true')
    parser.add_argument("-m", "--terminal",
                        help="Starts terminal mode", action='store_true')
    parser.add_argument("-o", "--no-color",
                        help="Deactivates stdout colors in batch and terminal mode", action='store_true')
    parser.add_argument("-c", "--config-file", help="Configuration file",
                        nargs='+',
                        default=[])
    parser.add_argument("-r", "--run-and-close", action='store_true',
                        help="Runs the test then closes the application",
                        required=False)
    parser.add_argument("-l", "--log-file", help="log file name", default='')
    parser.add_argument("-d", "--define",
                        help="Configuration passed to the executed tests.",
                        nargs='+',
                        type=str,
                        action='append',
                        default=[])
    parser.add_argument("-p", "--report-file",
                        help="report file name", default='')
    parser.add_argument("-t", "--report-type", help="report file type",
                        choices=cst.REP_TYPES,
                        default='')
    parser.add_argument("-n", "--report-pattern", help="report file pattern",
                        nargs='+',
                        default=[])
    parser.add_argument("-i", "--include-path",
                        help="Python modules search path",
                        nargs='+',
                        default=[])
    parser.add_argument("-g", "--debug", action='store_true',
                        help="GUI debug mode",
                        required=False)

    parser.add_argument(
        'test_file', help='the test script file', nargs='?', default='')
    args = parser.parse_args()

    if len(args.include_path)>0:
        for p in args.include_path:
            sys.path.append(p)

    defines = {}
    defs = []
    for define in args.define:
        defs += define
    for define in defs:
        d = define.split('=', 1)
        if d[0].strip() != '':
            if len(d) > 1:
                defines.update({d[0].strip(): d[1]})
            else:
                defines.update({d[0].strip(): True})

    cf = []
    for c in args.config_file:
        conf = c.strip('\"').strip("\'")
        if not os.path.isabs(conf):
            conf = os.path.join(os.getcwd(), conf)
        cf.append(conf)
    tf = args.test_file.strip('\"').strip("\'")
    rf = args.report_file.strip('\"').strip("\'")
    lf = args.log_file.strip('\"').strip("\'")
    pn = []
    for p in args.report_pattern:
        pn.append(p.strip('\"').strip("\'"))

    if args.version:
        # initilization of the settings (used to know if git supported)
        import interpreter.utils.settings as prefs
        prefs.init()

        from interpreter.utils.version import get_testium_version
        print(get_testium_version())

    elif args.terminal:
        import select
        from interpreter.terminal import Terminal

        if (lf != '') or (rf != '') or (tf != '') or (pn != []):
            print('"-l", "-p", "-t", "-n" options are not supported in this mode.')

        t = Terminal(os.getcwd(), cf, defines, args.no_color, text_mode=True)

        loop = 1
        while loop:
            try:
                loop = 0
                t.cmdloop()
            except KeyboardInterrupt:
                print("\n<ctrl-c>")
                loop = 1
            except Exception as exc:
                if str(exc) == 'quit':
                    break
                print(exc)
                loop = 1


    elif args.batch_execution:
        if (lf != ''):
            print('"-l" option is not supported in this mode.')

        from interpreter.batch import Batch
        b = Batch(tf, cf, defines, rf, args.report_type, pn, args.no_color, text_mode=True)

    else:
        from main_win.testium_win import MainWin
        MainWin(tf, config_files=cf,
                run=args.run_and_close,
                log_file=lf,
                defines=defines,
                report=rf,
                report_type=args.report_type,
                report_pattern=pn,
                debug=args.debug)
