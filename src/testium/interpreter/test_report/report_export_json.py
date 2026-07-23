import json
from runtime.testium_report import Exporter


class ReportExportJSON(Exporter):

    def export(self):
        tests = [row.to_dict() for row in self.rows]
        if self.no_header:
            json_export = {self.name if self.name != "" else "tests": tests}
        else:
            tests_name = "tests"
            if self.name != "":
                tests_name = self.name
            json_export = {"header": self.report.header}
            json_export.update({tests_name: tests})
        with open(self.out_path, "w", encoding="utf-8") as fd:
            fd.write(json.dumps(json_export, indent=4))
