# -*- coding: utf8 -*-
# Copyright (c) 2019 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
Utilities for working with the Python [[typing]] module.
"""

from __future__ import absolute_import
import typing


def is_generic(
  x,                    # type: Any
  generic_types=None    # type: Union[None, typing._GenericAlias, Tuple[typing._GenericAlias]]
):
  # type: (...) -> bool
  """
  Checks if *x* is a specialized version of the specified *generic_types*.

  Examples:

  ```py
  assert is_generic(List[str])
  assert not is_generic(str)
  assert is_generic(List[str], List)
  assert is_generic(List[str], (Dict, List))
  assert is_generic(List, List)
  assert not is_generic(List, Dict)
  assert not is_generic(List[str], Dict)
  ```
  """

  has_special_form = hasattr(typing, '_SpecialForm')
  is_special_form = has_special_form and isinstance(x, typing._SpecialForm)

  if (not hasattr(x, '__origin__') or not hasattr(x, '__args__')) and \
      not is_special_form:
    return False
  if generic_types is None:
    return True
  if not isinstance(generic_types, (list, tuple)):
    generic_types = (generic_types,)

  def eq(a, b):
    # NOTE (@NiklasRosenstein): Due to a bug in Python 3.6, comparing
    #   typing.Union without args with another type causes a RecursionError.
    #   See https://bugs.python.org/issue29246
    if a is typing.Union:
      return b is typing.Union
    elif b is typing.Union:
      return False
    return a == b

  if is_special_form and generic_types:
    return x in generic_types

  for gtype in generic_types:
    # Special handling for Optional, subscripting it gives a Union.
    if gtype == typing.Optional and extract_optional(x) is not None:
      return True
    if eq(x, gtype) or eq(x.__origin__, gtype):
      return True
    if getattr(gtype, '__origin__', None) is not None and eq(x.__origin__, gtype.__origin__):
      return True
  return False


def get_generic_args(x):  # type: Any -> Tuple[Any]
  """
  Returns the arguments to a generic. If the generic is not specialized,
  the typevars are returned instead.
  """

  # Special handling for Optional, as subscripting it gives a Union with
  # two arguments.
  v = extract_optional(x)
  if v is not None:
    return (v,)

  return x.__args__ or x.__parameters__


def extract_optional(x):  # type: (Any, Any) -> Optional[Type]
  """
  Returns the type wrapped in [[Optional]] if *x* is an optional, otherwise
  returns `None`.
  """

  if getattr(x, '__origin__', None) is typing.Union:
    if len(x.__args__) == 2 and x.__args__[1] is type(None):
      return x.__args__[0]
  return None