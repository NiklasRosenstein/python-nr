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
Describes a strong typing system that can then be extracted from a structured
object.
"""

import datetime
import decimal
import six
import typing

from nr.collections import abc
from nr.interface import implements, override
from nr.pylang.utils import classdef
from nr.pylang.utils.typing import is_generic, get_generic_args
from .decoration import Decoration
from .interfaces import IDataType
from .errors import InvalidTypeDefinitionError


@implements(IDataType)
class AnyType(object):
  """
  Represents an arbitrary type. The "Any" datatype is simply ignored by
  converters.
  """

  classdef.comparable([])

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if py_type_def is object:
      return cls()
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    return py_value


@implements(IDataType)
class BooleanType(object):

  classdef.comparable(['strict'])

  def __init__(self, strict=True):
    self.strict = strict

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if py_type_def is bool:
      return BooleanType()
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if (self.strict or strict) and not isinstance(py_value, bool):
      raise TypeError('expected bool')
    return bool(py_value) if coerce else py_value


@implements(IDataType)
class StringType(object):

  classdef.comparable(['strict'])

  def __init__(self, strict=True):
    self.strict = strict

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if py_type_def is str:
      return StringType()
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if isinstance(py_value, six.string_types):
      return py_value
    else:
      if self.strict or strict:
        raise TypeError('expected string, got {}'.format(
          type(py_value).__name__))
      return str(py_value) if coerce else py_value


@implements(IDataType)
class IntegerType(object):

  classdef.comparable(['strict'])

  def __init__(self, strict=True):
    self.strict = strict

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if py_type_def is int:
      return IntegerType()
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if isinstance(py_value, six.integer_types):
      return py_value
    else:
      if self.strict or strict:
        raise TypeError('expected int, got {}'.format(type(py_value).__name__))
      return int(py_value) if coerce else py_value


@implements(IDataType)
class DecimalType(object):
  """
  Represents a decimal value, backed by a float or [[decimal.Decimal]] object.
  If the selected Python type is Decimal, it will always accept strings which
  will be coerced to the correct type.

  If the selected type is float, it will only accept a string as input if
  *strict* is set to False.
  """

  classdef.comparable(['python_type', 'decimal_context', 'strict'])

  def __init__(self, python_type, decimal_context=None, strict=True):
    if python_type not in (float, decimal.Decimal):
      raise ValueError('python_type must be float or decimal.Decimal, got {!r}'
                       .format(python_type))
    if python_type is not decimal.Decimal and decimal_context:
      raise ValueError('decimal_context can only be used if python_type is '
                       'decimal.Decimal, but got {!r}'.format(python_type))
    self.python_type = python_type
    self.decimal_context = decimal_context
    self.strict = strict
    self.accepted_input_types = six.integer_types + (float, decimal.Decimal)
    if not self.strict or self.python_type is decimal.Decimal:
      self.accepted_input_types += six.string_types

  def coerce(self, value):
    if self.python_type is decimal.Decimal:
      return decimal.Decimal(value, self.decimal_context)
    elif self.python_type is float:
      return float(value)
    else:
      raise RuntimeError('python_type is invalid: {!r}'.format(
        self.python_type))

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if py_type_def in (float, decimal.Decimal):
      return DecimalType(py_type_def)
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if not isinstance(py_value, self.accepted_input_types):
      raise TypeError('expected {}'.format(
        '|'.join(x.__name__ for x in self.accepted_input_types)))
    return self.coerce(py_value) if coerce else py_value


@implements(IDataType)
class CollectionType(object):
  """
  Represents a collection of elements. The *py_type* represents the type for
  representing the collection in Python. It may also be a function that
  processes the returned list.
  """

  classdef.comparable(['item_type', 'py_type'])

  def __init__(self, item_type, py_type=list):
    self.item_type = item_type
    self.py_type = py_type

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    from .collection import Collection
    # []
    if isinstance(py_type_def, list) and len(py_type_def) == 0:
      return cls(AnyType())
    # [<type>]
    elif isinstance(py_type_def, list) and len(py_type_def) == 1:
      return cls(recursive(py_type_def[0]))
    # list
    elif py_type_def is list:
      return cls(AnyType())
    # set
    elif py_type_def is set:
      return cls(AnyType(), py_type=set)
    # typing.List
    elif is_generic(py_type_def, typing.List):
      item_type_def = get_generic_args(py_type_def)[0]
      if isinstance(item_type_def, typing.TypeVar):
        item_type_def = object
      return cls(recursive(item_type_def))
    # typing.Set
    elif is_generic(py_type_def, typing.Set):
      item_type_def = get_generic_args(py_type_def)[0]
      if isinstance(item_type_def, typing.TypeVar):
        item_type_def = object
      return cls(recursive(item_type_def), py_type=set)
    # nr.databind.core.collection.Collection
    elif isinstance(py_type_def, type) and issubclass(py_type_def, Collection):
      return py_type_def.datatype
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if isinstance(py_value, six.string_types) \
        or not isinstance(py_value, abc.Iterable):
      raise TypeError('expected a collection type, got {}'.format(
        type(py_value).__name__))
    if coerce and (not isinstance(self.py_type, type) or
        not isinstance(py_value, self.py_type)):
      py_value = self.py_type(py_value)
    return py_value


@implements(IDataType)
class ObjectType(object):
  """
  Represents an object (ie. a dictionary in Python lingo).
  """

  classdef.comparable(['value_type'])

  def __init__(self, value_type, py_type=dict):
    assert IDataType.provided_by(value_type), value_type
    self.value_type = value_type
    self.py_type = py_type

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    # {}
    if isinstance(py_type_def, dict) and len(py_type_def) == 0:
      return cls(AnyType())
    # {<type>}
    elif isinstance(py_type_def, set) and len(py_type_def) == 1:
      return cls(recursive(next(iter(py_type_def))))
    # {'value_type': <type>}
    elif isinstance(py_type_def, dict) and len(py_type_def) == 1 and \
        'value_type' in py_type_def:
      return cls(recursive(py_type_def['value_type']))
    # dict
    elif py_type_def is dict:
      return cls(AnyType())
    # typing.Dict
    elif is_generic(py_type_def, typing.Dict):
      key_type_def, value_type_def = get_generic_args(py_type_def)
      if not isinstance(key_type_def, typing.TypeVar) and key_type_def is not str:
        raise InvalidTypeDefinitionError(py_type_def)
      if isinstance(value_type_def, typing.TypeVar):
        value_type_def = object
      return cls(recursive(value_type_def))
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if not isinstance(py_value, abc.Mapping):
      raise TypeError('expected a mapping')
    if coerce and (not isinstance(self.py_type, type) or
        not isinstance(py_value, self.py_type)):
      py_value = self.py_type(py_value)
    return py_value


@implements(IDataType)
class DatetimeType(object):

  classdef.comparable([])

  class Format(Decoration):
    """ A decoration that can be associated with the datatype on a field to
    specify the format the this datetime is serialized/deserialized as.
    Multiple formats are only used during deserialization (if supported by the
    deserializer).

    A format may instead of a string also be an object with a #parse() and
    #format() function that accepts a datetime object. """

    def __init__(self, *formats):  # type: (str) -> None
      self.formats = formats

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if py_type_def is datetime.datetime:
      return cls()
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if not isinstance(py_value, datetime.datetime):
      raise TypeError('expected datetime.datetime, got {!r}'.format(
        type(py_value).__name__))
    return py_value


@implements(IDataType)
class DateType(object):

  classdef.comparable([])

  Format = DatetimeType.Format

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if py_type_def is datetime.date:
      return cls()
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if not isinstance(py_value, datetime.date):
      raise TypeError('expected datetime.date, got {!r}'.format(
        type(py_value).__name__))
    return py_value


@implements(IDataType)
class PythonClassType(object):
  """ A wrapper for Python type object's when they don't fit into any of the
  other types. The adapter for this datatype takes the lowest priority and
  only applies to custom defined types (not built-in types). """

  classdef.comparable(['cls'])
  priority = -1000

  def __init__(self, cls):
    assert isinstance(cls, type)
    self.cls = cls

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if isinstance(py_type_def, type) and py_type_def.__module__ not in (
        'builtin', '__builtin__', 'typing'):
      return cls(py_type_def)
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    if not isinstance(py_value, self.cls):
      raise TypeError('expected {} instance, got {}'.format(
        self.cls.__name__, type(py_value).__name__))
    return py_value

  @classmethod
  def make_check(cls, py_type): # type: (Type) -> Callable[bool, [IDataType]]
    """ Returns a test function that accepts an #IDataType instance and
    returns #True if it is a #PythonClassType of the specified *py_type*. """

    def check(datatype):
      return isinstance(datatype, PythonClassType) and issubclass(datatype.cls, py_type)
    check.__qualname__ = 'PythonClassType.of.{}.check'.format(py_type.__name__)
    return check


@implements(IDataType)
class MultiType(object):
  """ Represents a collection of datatypes. Uses the first type of the list
  of types that successfully serializes/deserializes. Multi types can be
  defined conveniently using tuples. """

  classdef.comparable(['types'])

  def __init__(self, *types):
    if len(types) == 1:
      types = types[0]
    self.types = [translate_type_def(x) for x in types]

  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    if isinstance(py_type_def, tuple):
      return MultiType([recursive(x) for x in py_type_def])
    raise InvalidTypeDefinitionError(py_type_def)

  def isinstance_check(self, py_value, strict, coerce):
    errors = []
    for datatype in self.types:
      try:
        return datatype.isinstance_check(py_value, strict, coerce)
      except TypeError as exc:
        errors.append(exc)
    raise TypeError(errors)


@implements(IDataType)
class ProxyType(object):
  """ Proxy for another datatype. Used with #forward_decl(). """

  classdef.comparable(['wrapped_type'])
  classdef.repr(['wrapped_type'])

  def __init__(self, wrapped_type):  # type: (Optional[IDataType]) -> None
    self.wrapped_type = wrapped_type

  @override
  def to_human_readable(self):
    return self.wrapped_type.to_human_readable()

  @override
  def propagate_field_name(self, name):
    pass

  @override
  @classmethod
  def from_typedef(cls, recursive, py_type_def):
    raise InvalidTypeDefinitionError(py_type_def)

  @override
  def isinstance_check(self, py_value, strict, coerce):
    return self.wrapped_type.isinstance_check(py_value, strict, coerce)


def forward_decl(proxy=None):
  if proxy is None:
    return ProxyType(None)
  if not isinstance(proxy, ProxyType):
    raise TypeError('expected ProxyType, got {}'.format(type(proxy).__name__))
  def decorator(cls):
    proxy.wrapped_type = translate_type_def(cls)
    return cls
  return decorator


def translate_type_def(py_type_def, fallback=None):
  if IDataType.provided_by(py_type_def):
    return py_type_def
  elif isinstance(py_type_def, type) and IDataType.implemented_by(py_type_def):
    try:
      return py_type_def()
    except TypeError:
      raise InvalidTypeDefinitionError(py_type_def)
  for adapter in sorted(IDataType.implementations(), key=lambda x: -x.priority):
    try:
      return adapter.from_typedef(translate_type_def, py_type_def)
    except InvalidTypeDefinitionError:
      pass
  if fallback:
    return fallback
  raise InvalidTypeDefinitionError(py_type_def)


__all__ = [
  'AnyType',
  'BooleanType',
  'StringType',
  'IntegerType',
  'DatetimeType',
  'DateType',
  'DecimalType',
  'CollectionType',
  'ObjectType',
  'PythonClassType',
  'MultiType',
  'forward_decl',
  'translate_type_def',
]
