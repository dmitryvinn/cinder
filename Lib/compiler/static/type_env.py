# Copyright (c) Facebook, Inc. and its affiliates. (http://www.facebook.com)
from __future__ import annotations

from typing import Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .types import Class, GenericClass, Value, TypeName


GenericTypeIndex = Tuple["Class", ...]
GenericTypesDict = Dict["Class", Dict[GenericTypeIndex, "Class"]]


class TypeEnvironment:
    def __init__(
        self,
        builtin_type_env: Optional[TypeEnvironment] = None,
    ) -> None:
        # We need to clone the dictionaries for each type so that as we populate
        # generic instantations that we don't store them in the global dict for
        # built-in types
        self._generic_types: GenericTypesDict = (
            {k: v.copy() for k, v in builtin_type_env._generic_types.items()}
            if builtin_type_env is not None
            else {}
        )

    def get_generic_type(
        self, generic_type: GenericClass, index: GenericTypeIndex
    ) -> Class:
        instantiations = self._generic_types.get(generic_type)
        if instantiations is not None:
            instance = instantiations.get(index)
            if instance is not None:
                return instance
        else:
            self._generic_types[generic_type] = instantiations = {}
        concrete = generic_type.make_generic_type(index, self)
        instantiations[index] = concrete
        return concrete