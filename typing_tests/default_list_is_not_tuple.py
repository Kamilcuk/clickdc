import dataclasses
from typing import Tuple
import clickdc


@dataclasses.dataclass
class Args:
    a: Tuple[int, ...] = clickdc.option("-b", default=[1, 2])


print("(is not assignable to declared type|is incompatible with declared type)")
