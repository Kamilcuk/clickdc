# clickdc

This is a package to define click command line options from a python `dataclass`.

You can define a python `dataclass` from `dataclasses` with fields that have
proper types when assigned by click parsing library. Then each field is
initialized with a option, argument, command or group from `clickdc` library.

```python
from dataclasses import dataclass
import clickdc
import click

@dataclass
class Args:
   option: bool = clickdc.option(is_flag=True, help="This is an option")
   command: int = clickdc.argument(type=int)
```

When the `dataclass` is decorated with `clickdc.adddc` to a function, this
library collects all options and arguments from the `dataclass` definition and
decorates the function. Then upon calling the function, this library
reconstructs the object using only arguments with names equal to the fields in
the `dataclass`, removing the arguments in the process.

```python
@click.command(help="This is a command")
@clickdc("args", Args)
def cli(args: Args):
   print(args)
```

If a keyword argument `clickdc` is missing, the field name is added with
an underscore replaced by dashes with two front dashes in front, and the
argument is added as a string as positional argument to `click.argument`
call. If the argument already exists, it is not added twice, for ease
of porting.

```python
   long_option: Optional[str] = clickdc.option("-o", help="--long-option is added automatically")
   args: str = clickdc.option(help="Positional argument 'args' is added automatically")
```


Additionally, some keyword arguments to the underlying `click.option` or
`click.argument` are inferred from the `dataclass` field type depending on
on the following conditions. Use field type `Any` or add `type=`, for example
`type=str`, to ad-hoc disable the mechanisms.

- If the field:
   - is initialized using an `option` or `argument`,
   - does not have the type `Any`,
   - does not have any keyword argument `type required is_flag default nargs count flag_value`
   - and does not have an argument `clickdc` passed with `None`
- Then:
  - if the field is an option, then if the field type
      - is `bool`, add `is_flag=True`
      - is `Optional[T]`, add `type=T`
      - is `Tuple[T, ...]`, add type=T, multiple=True,
      - is any other type `T`, add `type=T, required=True`
  - if the field is an argument, then if the field type:
      - is `Tuple[T, ...]`, add `type=T, nargs=-1`
      - is any other type `T`, add `type=T`

The correct type for multiple arguments returned by `click` is `Tuple[T, ...]`.

```python
   custom: Tuple[float, ...] = clickdc.option(type=float, multiple=True)
   moreargs: Tuple[int, ...] = clickdc.argument(type=int, nargs=5)
   options: Tuple[float, ...] = clickdc.option()
   arguments: Tuple[int, ...] = clickdc.argument()
```


The `dataclass` field initializes functions - command, group, option, argument - take the
same options as their click counterparts with one additional positional
argument called `clickdc` for this module options. The `clickdc` can be assigned
just to `None` to disable automatic adding of the options and keyword
arguments by this module.

```python
   option: bool = clickdc.option("--option", is_flag=True, clickdc=None)
   command: int = clickdc.argument("command", type=int, clickdc=None)
```

You can use `from pydantic.dataclasses import dataclass` to have type checking
for your `dataclass`.

You can safely mix any `clickdc` options with `click` options. Typically, I
would do:

```python
@dataclass
class Args:
   options: bool = clickdc.option(help="Options here")

@click.command(help="But command here")
@clickdc.adddc("args", Args)
@click.option("-v", "--verbose", count=True)
def cli(args: Args, verbose: int):
    print(args)
    print(verbose)
```

You can inherit `dataclasses` and decorate using multiple. It works just by
decorating the function with the proper `click.` function inferred from the
field type.

# TODO

`dataclasses(default, default_factory)` require some questionable polishing.

# Epilogue

Written by Kamil Cukrowski

