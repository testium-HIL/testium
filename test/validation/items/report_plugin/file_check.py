import os


def file_contains(path, text):
    if not os.path.isfile(path):
        return False
    with open(path, 'r') as f:
        return text in f.read()
