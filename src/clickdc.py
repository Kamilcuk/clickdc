# Small library to convert dataclass into click arguments
# and get click arguments to parse.
import dataclasses
import functools
import logging
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    Iterator,
    Optional,
    Tuple,
    Union,
    get_type_hints,
)

import click
from typing_extensions import Protocol, Type, get_args, get_origin

try:
    from typing import NoneType  # pyright: ignore
except ImportError:
    NoneType = type(None)

###############################################################################

log = logging.getLogger(__name__)
Decorator = Union[
    type(click.group), type(click.command), type(click.option), type(click.group)
]


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Any]]


DataclassType = Type[DataclassInstance]


def is_type(orig: Type, types: Iterable[Type]) -> bool:
    return any(type(orig) is type(x) for x in types)


def is_optional(orig: Type) -> bool:
    return (
        get_origin(orig) is Union
        and len(get_args(orig)) == 2
        and get_args(orig)[1] is NoneType
    )


def is_tuple_arr(orig: Type) -> bool:
    return (
        get_origin(orig) in [Tuple, tuple]
        and len(get_args(orig)) == 2
        and get_args(orig)[1] is Ellipsis
    )


###############################################################################


@dataclasses.dataclass
class Opts:
    """The options of clickdc module. Not implemented. Make an issue to ping me."""

    no: bool = False
    """Set to true to disable all parsing and checking done by this module"""

    arg: bool = True
    """Add the long option with underscore replaced by dash to the options or argument"""

    char: str = "-"
    """Replace understore in the option by this character"""

    check: bool = True
    """Check if the declared type of the option is correct"""

    infer: bool = True
    """Infer some keyword arguments from the type of the field"""

    def __post_init__(self):
        if self.no:
            self.arg = self.check = self.infer = False


_OptsArg = Optional[Opts]
"""User can pass None, as a shurtcut to no=True"""


@dataclasses.dataclass(frozen=True)
class FieldDesc:
    """Additional data put with the field in metadata"""

    callback: Decorator
    """click.option or click.argument"""
    opts: Opts
    """Options of clickdc module"""
    args: Tuple[Any, ...]
    """Position arguments to callback"""
    kwargs: Dict[str, Any]
    """Dictionary argumetns to callback"""


@dataclasses.dataclass(frozen=True)
class Field(FieldDesc):
    """Internal iterate to iterate over fields"""

    field: dataclasses.Field
    """The field"""
    type: Type
    """Resolved type from type hints"""

    @property
    def name(self):
        return self.field.name

    def is_command(self):
        return self.callback in [click.group, click.command]

    def assert_type(self, arg_class: DataclassType):
        required = self.kwargs.get("required")
        multiple = self.kwargs.get("multiple")
        nargs = self.kwargs.get("nargs")
        is_flag = self.kwargs.get("is_flag")
        count = self.kwargs.get("count")
        shouldbetypeorig = self.kwargs.get("type")
        default = self.kwargs.get("default")
        # Determine what type should be the field.
        shouldbetype = shouldbetypeorig
        try:
            if shouldbetypeorig is not None:
                if callable(shouldbetypeorig):
                    shouldbetype = get_type_hints(shouldbetypeorig).get("return")
                elif issubclass(type(shouldbetypeorig), click.ParamType):
                    shouldbetype = get_type_hints(shouldbetypeorig.convert).get(
                        "return"
                    )
        except (NameError, TypeError):
            return
        #
        thetype = self.type
        infostr: str = (
            f"callback={self.callback.__name__}"
            f" required={required} multiple={multiple} is_flag={is_flag}"
            f" shouldbetypeorig={shouldbetypeorig} shouldbetype={shouldbetype} thetype={thetype}"
            f" nargs={nargs} default={default} count={count}"
        )
        if shouldbetype is None:
            return
        if thetype == Any:
            return
        try:
            if self.is_command():
                shouldbetype = NoneType
            elif self.callback == click.option:
                if is_flag:
                    shouldbetype = bool
                elif count:
                    shouldbetype = int
                if multiple:
                    shouldbetype = Tuple[shouldbetype, ...]
                elif not required and default is None:
                    shouldbetype = Optional[shouldbetype]
            elif self.callback == click.argument:
                if nargs != 0:
                    shouldbetype = Tuple[shouldbetype, ...]
            if shouldbetype is not Any:
                assert (
                    thetype is shouldbetype
                ), f"thetype={thetype} shouldbetype={shouldbetype}"
        except AssertionError:
            raise AssertionError(
                f"Field {arg_class!r}.{self.field.name!r}: {self.field.type} is wrong. {infostr}"
            )

    def __infer_opts_from_type(self, kwargs: Dict[str, Any]):
        """Infer click options from the typing of the field"""
        if self.type is not Any and all(
            kwargs.get(x) is None
            for x in "type required is_flag default nargs count flag_value".split()
        ):
            if self.callback == click.option and kwargs.get("is_flag") is None:
                # if the type is bool, add is_flag=True
                if self.type in [bool, Optional[bool]]:
                    kwargs.setdefault("is_flag", True)
                # if the type is Optional[T], add type=T
                elif is_optional(self.type):
                    kwargs.setdefault("type", get_args(self.type)[0])
                # if the type is Tuple[T, ...], add type=T, multiple=True,
                elif is_tuple_arr(self.type):
                    kwargs.setdefault("type", get_args(self.type)[0])
                    kwargs.setdefault("multiple", True)
                # if the type is T, add type=T, required=True
                else:
                    kwargs.setdefault("required", True)
                    kwargs.setdefault("type", self.type)
            elif self.callback == click.argument:
                # if the type is Tuple[T, ...], add type=T, nargs=-1
                if is_tuple_arr(self.type):
                    kwargs.setdefault("type", get_args(self.type)[0])
                    kwargs.setdefault("nargs", -1)
                else:
                    kwargs.setdefault("type", self.type)

    def apply(self) -> Callable[[Callable], Callable]:
        # Append the field name, with -- if it is an option, to the argument list.
        args = list(self.args)
        if self.opts.arg:
            name = self.field.name.replace("_", self.opts.char)
            name = f"--{name}" if self.callback == click.option else name
            if name not in args:
                args = [name, *args]
        #
        kwargs = self.kwargs
        if self.opts.infer:
            self.__infer_opts_from_type(kwargs)
        #
        try:
            # Finally, call the decorators.
            return self.callback(*args, **kwargs)
        except Exception:
            raise Exception(
                f"Error calling {self.callback.__name__}({args}, {kwargs}) for {self}"
            )


###############################################################################

TAG = "clickdc"
"""The metadata name used in dataclass field for arguments of this module"""


def _myfields(arg_class) -> Iterator[Field]:
    """Iterate over fields that we handle"""
    hints = get_type_hints(arg_class)
    for field in reversed(dataclasses.fields(arg_class)):
        desc: Optional[FieldDesc] = field.metadata.get(TAG)
        if desc:
            yield Field(
                desc.callback,
                desc.opts,
                desc.args,
                desc.kwargs,
                field=field,
                type=hints[field.name],
            )


def _mkfield(func: Decorator, clickdc: _OptsArg, args, kwargs):
    clickdc = Opts(no=True) if clickdc is None else clickdc
    return dataclasses.field(
        metadata={TAG: FieldDesc(func, clickdc, args, kwargs)},
    )


###############################################################################


@functools.wraps(click.group)
def group(*args, clickdc: _OptsArg = Opts(), **kwargs):
    return _mkfield(click.group, clickdc, args, kwargs)


@functools.wraps(click.command)
def command(*args, clickdc: _OptsArg = Opts(), **kwargs):
    return _mkfield(click.command, clickdc, args, kwargs)


@functools.wraps(click.option)
def option(*args, clickdc: _OptsArg = Opts(), **kwargs):
    return _mkfield(click.option, clickdc, args, kwargs)


@functools.wraps(click.argument)
def argument(*args, clickdc: _OptsArg = Opts(), **kwargs):
    return _mkfield(click.argument, clickdc, args, kwargs)


def _assert_annotations(arg_class: DataclassType):
    """Assert the type annotations are correct with the click types."""
    for ff in _myfields(arg_class):
        ff.assert_type(arg_class)


def adddc(kw_name: str, arg_class: DataclassType):
    """Add dataclass as arguments to the function.
    Pass the constructed dataclass as kw_name"""
    assert dataclasses.is_dataclass(arg_class), f"is not a dataclass: {arg_class}"
    # _assert_annotations(arg_class)

    def dataclass_click_in(func: Callable) -> Callable:
        @functools.wraps(func)
        def dataclass_click_wrapper(*args, **kwargs):
            # Given command line arguments in kwargs, collect and remove the ones in our dataclass.
            arg_class_args = {}
            for ff in _myfields(arg_class):
                name = ff.name
                if name in kwargs:
                    arg_class_args[name] = kwargs[name]
                    del kwargs[name]
                # Check for any command and group fields, and construct them with None.
                elif ff.is_command():
                    arg_class_args[name] = None
            # Construct the dataclass and assign it to kw_name.
            kwargs[kw_name] = arg_class(**arg_class_args)
            # Call the inner function.
            return func(*args, **kwargs)

        wrapper = dataclass_click_wrapper
        # For each field, apply the click.option() decorators over the function.
        for ff in _myfields(arg_class):
            try:
                call = ff.apply()
                wrapper = call(wrapper)
            except Exception:
                raise Exception(
                    f"Error when creating options for class {arg_class.__name__!r} field {ff.name!r}."
                    f" Internal object: {ff}"
                )

        return wrapper

    return dataclass_click_in


###############################################################################


def __alias_option_callback(
    aliased: Dict[str, Any],
    ctx: click.Context,
    param: click.Parameter,
    value: Any,
):
    """Callback called from alias_option option."""
    if value:
        for paramname, val in aliased.items():
            try:
                aliasparam = next(p for p in ctx.command.params if p.name == paramname)
            except KeyError:
                raise Exception(
                    f"Did not found option named {paramname} aliased by {param.name}"
                )
            if aliasparam.multiple:
                orig: Iterable = aliasparam.default or []  # pyright: ignore
                try:
                    aliasparam.default = list(orig) + [val]
                except TypeError:
                    raise Exception(
                        f"alias_option {param.name} cannot append to default of param {paramname}"
                        f" because the default is not a iterable"
                    )
            else:
                aliasparam.default = val
    return value


def alias_option(
    *param_decls: str,
    aliased: Dict[str, Any],
    **attrs: Any,
):
    """Add this to click options to have an alias for other options"""
    aliasedhelp = " ".join(
        "--"
        + k.replace("_", "-")
        + ("" if v is True else f"={v}" if isinstance(v, int) else f"={v!r}")
        for k, v in aliased.items()
    )
    return option(
        *param_decls,
        is_flag=True,
        help=f"Alias to {aliasedhelp}",
        callback=lambda *args: __alias_option_callback(aliased, *args),
        **attrs,
    )
