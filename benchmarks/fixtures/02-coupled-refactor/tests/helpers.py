import os
import tempfile


def write_config(text):
    handle = tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False, encoding="utf-8")
    handle.write(text)
    handle.close()
    return handle.name


def remove(path):
    os.unlink(path)
