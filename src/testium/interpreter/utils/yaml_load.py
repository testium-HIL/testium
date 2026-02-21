from yaml.parser import ParserError
from yaml import load, Loader
from yaml.scanner import ScannerError
from libs.testium import print_debug
from lib.tum_except import ETUMSyntaxError
import io


def print_yaml(file: io.TextIOWrapper, file_name):
    """ Prints YAML file if debug mode is activated.
    """
    file.seek(0)
    print_debug(f"Dump of \"{file_name}\":")
    lines = file.read().splitlines()
    lines = [f"{i+1:>3d}: " + lines[i] for i in range(len(lines))]
    print_debug("\n".join(lines))


def yaml_load(file, real_file_name: str, loader: Loader):
    try:
        return load(file, loader)

    except ParserError as e:
        if isinstance(file, io.TextIOWrapper):
            print_yaml(file, real_file_name)
        raise ETUMSyntaxError(f"yaml file parsing error: " + str(e), real_file_name)
    except ScannerError as e:
        if isinstance(file, io.TextIOWrapper):
            print_yaml(file, real_file_name)
        raise ETUMSyntaxError("yaml file scanning error: " + str(e), real_file_name)
