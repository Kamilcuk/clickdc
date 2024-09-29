import dataclasses
from typing import List, Tuple
import clickdc


@dataclasses.dataclass
class Args:
    a: List[int] = clickdc.option("-b", default=(1, 2))


print('(is not assignable to declared type|is incompatible with declared type)')
