from __future__ import annotations

from typing import TYPE_CHECKING, Any

from anchor_bench.data.validation import validate_sage_dir

if TYPE_CHECKING:
    from anchor_bench.data.sage import SageDataset

_SAGE_EXPORTS = {
    "SageDataset",
    "load_joint_list",
    "load_real_data",
    "load_vector_csv",
    "parse_vector",
}


def __getattr__(name: str) -> Any:
    if name not in _SAGE_EXPORTS:
        raise AttributeError(name)
    from anchor_bench.data import sage

    return getattr(sage, name)


__all__ = [
    "SageDataset",
    "load_joint_list",
    "load_real_data",
    "load_vector_csv",
    "parse_vector",
    "validate_sage_dir",
]
