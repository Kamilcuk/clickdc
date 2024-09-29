import dataclasses
from typing import Tuple
import clickdc


@dataclasses.dataclass
class Args:
    b: Tuple[int, ...] = clickdc.option("-b", is_flag=True)


print('(is not assignable to declared type|is incompatible with declared type)')
