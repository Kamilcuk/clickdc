import pytest
import subprocess
from pathlib import Path
import re

DIR = Path(__file__).parent.parent
pyright = ["python3", "-m", "pyright"]


def test_typing_check():
    assert files, f"{DIR}"


def test_typing():
    subprocess.check_call(pyright, cwd=DIR)


typing_tests = DIR / "typing_tests"
files = list(str(x.relative_to(typing_tests)) for x in typing_tests.glob("*.py"))


@pytest.mark.parametrize("filestr", files)
def test_typing_file(filestr: str):
    file = Path(typing_tests / filestr)
    pattern = subprocess.check_output(
        ["python3", str(file.absolute())],
        cwd=file.parent,
        text=True,
    ).strip()
    pp = subprocess.run(
        [*pyright, str(file.absolute())],
        cwd=file.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert pp.returncode == 1, f"pyright {file} failed, but should have succeeded"
    output = pp.stdout
    assert re.search(
        pattern, output
    ), f"Typing test failed of {file}\n---\n{pattern}\n---\n{output}\n"
