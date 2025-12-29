import os
import py_func.tm as tm
import textwrap
import sqlite3
from junit_xml import TestSuite, TestCase
from interpreter.test_items.test_result import TestValue


def _prepare_file_to_save(file_name, file_ext=""):
    iname = file_name
    if file_ext != "":
        iname = os.path.splitext(file_name)[0] + file_ext

    if os.path.isfile(iname):
        i = 0
        fname = iname
        while os.path.isfile(fname):
            i += 1
            fname = iname + "-" + str(i) + ".saved"
        os.rename(iname, fname)
    return iname


def _get_testSuite(test, cur):
    test_cases = []
    failures = 0
    failed_results = cur.execute(
        f"SELECT test_name, result, report_key, duration, log, data FROM tests WHERE report_key LIKE '{test}_%'"
    ).fetchall()
    for result in failed_results:
        tc = TestCase(
            name=f"[{test}] {result[0]}",
            elapsed_sec=result[3],
            stdout=result[4],
            log=result[5],
        )

        # Check the results of all
        if result[1] == str(TestValue.NORUN):
            tc.add_skipped_info("The test has not being runned")
        elif result[2] == f"{test}_PASS":
            if result[1] == str(TestValue.FAILURE):
                failures += 1
                print(f"Item [{test}] Failing on '{result[0]}' : The test should PASS")
                print("*" * 80)
                print(textwrap.indent(result[4], prefix="* "))
                print("*" * 80)
                tc.add_error_info("The test should PASS!\n\n" + result[4])
        elif result[2] == f"{test}_FAIL":
            if result[1] == str(TestValue.SUCCESS):
                failures += 1
                print(
                    f"Item [{test}] Failing on '{result[0]}' : \n\tThe test should FAIL"
                )
                print("*" * 80)
                print(textwrap.indent(result[4], prefix="* "))
                print("*" * 80)
                tc.add_error_info("The test should FAIL!\n\n" + result[4])

        # add to the test cases
        test_cases.append(tc)

    return failures, TestSuite(test, test_cases)


def exec():
    print("\n")
    print("*" * 80)
    print("* Post execution started")
    print("*" * 80)

    # Get the info
    report = (
        str(tm.gd("validation_report_path"))
        + str(tm.gd("validation_report_file"))
        + ".sqlite"
    )
    enabled_tests = tm.gd("items")

    # Open the database
    con = sqlite3.connect(report)
    cur = con.cursor()

    # Get the testsuit for every parts
    failures = 0
    for test in enabled_tests:
        failed, ts = _get_testSuite(test, cur)
        failures += failed
        # write to the file
        junit_report = report.replace(".sqlite", f"-{test}.xml")
        print(junit_report)
        _prepare_file_to_save(junit_report)
        with open(junit_report, "w") as f:
            f.write(TestSuite.to_xml_string([ts]))

    # cleanup
    con.close()
    print("*" * 80)
    if failures == 0:
        print("* Post execution finished : SUCCESS")
    else:
        print(f"* Post execution finished: {failures} test FAILED")
    print("*" * 80)

def post_exec():
    exec()

def post_exec_fail():
    exec()
