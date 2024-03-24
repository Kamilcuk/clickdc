#!/usr/bin/env python3
import shlex
import traceback
from typing import Any, Optional, Tuple

import click
from click.testing import CliRunner
from pydantic.dataclasses import dataclass

import clickdc


def invoke(*args, **kwargs):
    return CliRunner(mix_stderr=True).invoke(*args, **kwargs)


def run(arg_class, input: str, output: Any = None, fail: int = 0, toargs: bool = False):
    @clickdc.adddc("args", arg_class)
    def cli(args):
        try:
            if not toargs:
                click.echo(args)
            else:
                click.echo(" ".join(clickdc.to_args(args)))
        except Exception:
            traceback.print_exc()
            raise

    r = invoke(cli, shlex.split(input))
    info = f"{arg_class} {input} {r.output}"
    if fail:
        assert r.exit_code != 0, info
    else:
        assert r.exit_code == 0, info
    if output is not None:
        assert r.output == f"{output}\n", info


def test_command():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        cmd: int = clickdc.argument()

    run(Args, "123", Args(_=None, cmd=123))


def test_option_int():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        option: int = clickdc.option("-o")

    run(Args, "", fail=1)
    run(Args, "-o 123", Args(_=None, option=123))


def test_option_optional_int():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        option: Optional[int] = clickdc.option("-o")

    run(Args, "", Args(_=None, option=None))
    run(Args, "-o 123", Args(_=None, option=123))


def test_flag():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        option: bool = clickdc.option()

    run(Args, "", Args(_=None, option=False))
    run(Args, "--option", Args(_=None, option=True))


def test_float_option():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        option: float = clickdc.option(default=1.0)

    run(Args, "", Args(_=None, option=1.0))
    run(Args, "--option str", fail=1)
    run(Args, "--option 2.0", Args(_=None, option=2.0))


def test_float_argument():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        arg: float = clickdc.argument()

    run(Args, "", fail=1)
    run(Args, "str", fail=1)
    run(Args, "2.0", Args(_=None, arg=2.0))


def test_multiple():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        arg: Tuple[float, ...] = clickdc.argument(nargs=-1, type=float, required=True)

    run(Args, "", fail=1)
    run(Args, "str", fail=1)
    run(Args, "2.0", Args(_=None, arg=(2.0,)))
    run(Args, "2.0 3.0", Args(_=None, arg=(2.0, 3.0)))


def test_multiple_auto():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        arg: Tuple[float, ...] = clickdc.argument()

    run(Args, "str", fail=1)
    run(Args, "", Args(_=None, arg=tuple()))
    run(Args, "2.0", Args(_=None, arg=(2.0,)))
    run(Args, "2.0 3.0", Args(_=None, arg=(2.0, 3.0)))


def test_example1():
    @dataclass
    class Args:
        _: Any = clickdc.command(help="This is a command")
        option: bool = clickdc.option(is_flag=True, help="This is an option")
        command: int = clickdc.argument(type=int)

    run(Args, "str", fail=1)
    run(Args, "1", Args(_=None, option=False, command=1))


def test_example2():
    @dataclass
    class Args:
        _: Any = clickdc.command(help="This is a command")
        custom: Tuple[float, ...] = clickdc.option(type=float, multiple=True)
        moreargs: Tuple[int, ...] = clickdc.argument(type=int, nargs=5)
        options: Tuple[float, ...] = clickdc.option()
        arguments: Tuple[int, ...] = clickdc.argument()

    run(Args, "1 2 3 4", fail=1)
    run(
        Args,
        "1 2 3 4 5",
        Args(
            _=None,
            custom=tuple(),
            moreargs=(1, 2, 3, 4, 5),
            options=tuple(),
            arguments=tuple(),
        ),
    )
    run(
        Args,
        "--custom=1.0 --options=2.0 1 2 3 4 5 6",
        Args(
            _=None,
            custom=(1.0,),
            moreargs=(1, 2, 3, 4, 5),
            options=(2.0,),
            arguments=(6,),
        ),
    )


def test_disable():
    @dataclass
    class Args:
        _: Any = clickdc.command(help="This is a command")
        option: bool = clickdc.option("--option", is_flag=True, clickdc=None)
        command: int = clickdc.argument("command", type=int, clickdc=None)

    run(Args, "", fail=1)
    run(Args, "--option 123", Args(_=None, option=True, command=123))


def test_alias_multiple():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        sum: Tuple[int, ...] = clickdc.option(multiple=True, type=int, default=[3, 4])
        add: bool = clickdc.option(is_flag=True)
        add1: bool = clickdc.alias_option(aliased=dict(sum="1"))
        add2: bool = clickdc.alias_option(aliased=dict(sum="2"))

    run(Args, "--add", Args(_=None, sum=(3, 4), add=True, add1=False, add2=False))
    run(Args, "--add1", Args(_=None, sum=(3, 4, 1), add=False, add1=True, add2=False))
    run(Args, "--add2", Args(_=None, sum=(3, 4, 2), add=False, add1=False, add2=True))
    run(
        Args,
        "--add1 --add2",
        Args(_=None, sum=(3, 4, 1, 2), add=False, add1=True, add2=True),
    )


def test_to_args():
    @dataclass
    class Args:
        _: Any = clickdc.command()
        opta: bool = clickdc.option("-a")
        optb: Tuple[int, ...] = clickdc.option("-b")
        cmda: int = clickdc.argument()
        cmdb: int = clickdc.argument()
        cmdc: Tuple[int, ...] = clickdc.argument()

    run(Args, "1 2 3 4 5 6", "1 2 3 4 5 6", toargs=True)
    run(Args, "--opta 1 2 3 4", "--opta 1 2 3 4", toargs=True)
    run(Args, "-a 1 2 3 4", "--opta 1 2 3 4", toargs=True)
    run(Args, "-a -b 1 -b 2 1 2 3", "--opta --optb 1 --optb 2 1 2 3", toargs=True)
