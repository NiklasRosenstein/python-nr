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
Converts from and to JSON like nested structures.
"""

import decimal
import six

from functools import partial
from nr.commons.py import classdef
from nr.collections import abc, OrderedDict
from nr.interface import implements
from .core.interfaces import IDeserializer, ISerializer
from .core.collection import Collection
from .core.errors import SerializationTypeError, SerializationValueError
from .core.datatypes import AnyType, BooleanType, StringType, IntegerType, \
  DecimalType, CollectionType, ObjectType, StructType, PythonClassType, \
  MultiType, UnionType
from .core.decoration import Decoration
from .core.metadata import DatabindMetadata
from .mapper import SimpleModule

__all__ = ['JsonModule', 'JsonFieldName', 'JsonRequired', 'JsonDeserializer',
           'JsonSerializer']


class JsonModule(SimpleModule):

  def setup_module(self, context):
    self.register_duplex(AnyType, AnyConverter())
    self.register_duplex(BooleanType, BooleanConverter())
    self.register_duplex(StringType, StringConverter())
    self.register_duplex(IntegerType, IntegerConverter())
    self.register_duplex(DecimalType, DecimalConverter())
    self.register_duplex(CollectionType, CollectionConverter())
    self.register_duplex(ObjectType, ObjectConverter())
    self.register_duplex(StructType, StructConverter())
    self.register_duplex(PythonClassType, PythonClassConverter())
    self.register_duplex(MultiType, MultiTypeConverter())
    self.register_duplex(UnionType, UnionTypeConverter())


@implements(IDeserializer, ISerializer)
class AnyConverter(object):

  def deserialize(self, context, location):
    return location.value

  def serialize(self, context, location):
    return location.value


@implements(IDeserializer, ISerializer)
class BooleanConverter(object):

  def deserialize(self, context, location):
    if isinstance(location.value, bool):
      return location.value
    raise SerializationTypeError(location)

  def serialize(self, context, location):
    if location.datatype.strict and not isinstance(location.value, bool):
      raise SerializationTypeError(location)
    return bool(location.value)


@implements(IDeserializer, ISerializer)
class StringConverter(object):

  def deserialize(self, context, location):
    if isinstance(location.value, six.string_types):
      return location.value
    if location.datatype.strict:
      raise SerializationTypeError(location)
    return str(location.value)

  def serialize(self, context, location):
    return location.value


@implements(IDeserializer, ISerializer)
class IntegerConverter(object):

  def deserialize(self, context, location):
    try:
      return location.datatype.check_value(location.value)
    except TypeError as exc:
      raise SerializationTypeError(location, exc)

  def serialize(self, context, location):
    return self.deserialize(context, location)


@implements(IDeserializer, ISerializer)
class DecimalConverter(object):

  def __init__(self, supports_decimal=False, as_string=False):
    super(DecimalConverter, self).__init__()
    self.supports_decimal = supports_decimal
    self.as_string = as_string

  def deserialize(self, context, location):
    if isinstance(location.value, location.datatype.accepted_input_types):
      return location.datatype.coerce(location.value)
    raise SerializationTypeError(location)

  def serialize(self, context, location):
    if self.as_string:
      return str(location.value)
    if self.supports_decimal and isinstance(location, decimal.Decimal):
      return location.value
    return float(location.value)


@implements(IDeserializer, ISerializer)
class CollectionConverter(object):
  """
  Serializes the [[CollectionType]] from a Python collection object to a
  list (for serialization in JSON). If the underlying Python type is
  unordered, the values will be sorted by their hash.
  """

  def __init__(self, json_type=list):
    super(CollectionConverter, self).__init__()
    self.json_type = json_type

  def deserialize(self, context, location):
    # Check if the value we receive is actually a collection.
    try:
      location.datatype.check_value(location.value, _convert=False)
    except TypeError:
      raise SerializationTypeError(location)

    # Deserialize child elements.
    item_type = location.datatype.item_type
    result = []
    for index, item in enumerate(location.value):
      result.append(context.deserialize(item, item_type, index))

    # Convert to the designated Python type.
    py_type = location.datatype.py_type
    if not isinstance(py_type, type) or not isinstance(result, py_type):
      result = py_type(result)

    if isinstance(result, Collection):
      result.__databind__ = DatabindMetadata(location)
    return result

  def serialize(self, context, location):
    # Check if the value we receive is actually a collection.
    try:
      location.datatype.check_value(location.value, _convert=False)
    except TypeError:
      raise SerializationTypeError(location)

    # Serialize child elements.
    item_type = location.datatype.item_type
    result = []
    for index, item in enumerate(location.value):
      result.append(context.serialize(iten, item_type, index))

    # Convert to the designated JSON type.
    json_type = self.json_type
    if not isinstance(json_type, type) or not isinstance(result, json_type):
      result = json_type(result)

    return result


@implements(IDeserializer, ISerializer)
class ObjectConverter(object):

  def __init__(self, json_type=OrderedDict):
    super(ObjectConverter, self).__init__()
    self.json_type = json_type

  def deserialize(self, context, location):
    if not isinstance(location.value, dict):
      raise SerializationTypeError(location)
    value_type = location.datatype.value_type
    result = location.datatype.py_type()
    for key in location.value:
      result[key] = context.deserialize(location.value[key], value_type, key)
    return result

  def serialize(self, context, location):
    result = self.json_type()
    value_type = location.datatype.value_type
    for key in location.value:
      result[key] = context.serialize(location.value[key], value_type, key)
    return result


@implements(IDeserializer, ISerializer)
class StructConverter(object):

  def _extract_kwargs(self, field, context, struct_cls, location, kwargs, handled_keys):
    assert field.name not in kwargs, (field, struct_cls, location)

    # Retrieve decorations that will affect the deserialization of this field.
    json_required = JsonRequired.first(field.decorations)
    json_field_name = JsonFieldName.first(field.decorations)

    key = json_field_name.name if json_field_name else field.name
    if key not in location.value:
      if json_required:
        raise SerializationValueError(location, "missing member \"{}\" for {} object"
                                .format(key, struct_cls.__name__))
      return

    value = location.value[key]
    if field.nullable and value is None:
      kwargs[field.name] = None
    else:
      kwargs[field.name] = context.deserialize(value, field.datatype, key)

    handled_keys.add(key)

  def deserialize(self, context, location):
    if not isinstance(location.value, abc.Mapping):
      raise SerializationTypeError(location)

    struct_cls = location.datatype.struct_cls
    fields = struct_cls.__fields__
    strict = getattr(struct_cls.Meta, 'strict', False)

    kwargs = {}
    handled_keys = set(location.datatype.ignore_keys)
    for name, field in fields.items().sortby(lambda x: x[1].get_priority()):
      assert name == field.name, "woops: {}".format((name, field))
      self._extract_kwargs(field, context, struct_cls, location, kwargs, handled_keys)

    if strict:
      remaining_keys = set(location.value.keys()) - handled_keys
      if remaining_keys:
        raise SerializationValueError(location, "strict object type \"{}\" does not "
          "allow additional keys on extract, but found {!r}".format(
            struct_cls.__name__, remaining_keys))

    obj = object.__new__(struct_cls)
    obj.__databind__ = DatabindMetadata(location)

    try:
      obj.__init__(**kwargs)
    except TypeError as exc:
      raise SerializationTypeError(location)
    return obj

  def serialize(self, context, location):
    struct_cls = location.datatype.struct_cls
    if not isinstance(location.value, struct_cls):
      raise SerializationTypeError(location)
    result = {}
    for name, field in struct_cls.__fields__.items():
      if field.is_derived():
        continue
      value = getattr(location.value, name)
      sub_location = location.sub(name, value, field.datatype)
      result[field.name] = context.serialize(sub_location)
    return result


@implements(IDeserializer, ISerializer)
class PythonClassConverter(object):
  """ Uses the #to_json()/#from_json() method that is defined on the class
  to serialize/deserialize the object. Raises a #SerializationTypeError if
  the class does not support it. """

  def deserialize(self, context, location):
    deserializer = JsonDeserializer.for_class(location.datatype.cls)
    if not deserializer:
      raise SerializationTypeError(location, 'No JsonDeserializer found '
        'on class {}'.format(location.datatype.cls.__name__))
    return deserializer.deserialize(context, location)

  def serialize(self, context, location):
    serializer = JsonSerializer.for_class(location.datatype.cls)
    if not serializer:
      raise SerializationTypeError(location, 'No JsonSerializer found '
        'on class {}'.format(location.datatype.cls.__name__))
    if not isinstance(location.value, location.datatype.cls):
      raise SerializationValueError(location, 'Expected {} instance, got {}'
        .format(location.datatype.cls.__name__, type(location.value).__name__))
    return serializer.serialize(context, location)


@implements(IDeserializer, ISerializer)
class MultiTypeConverter(object):

  def _do(self, context, location, method):
    errors = []
    for datatype in location.datatype.types:
      try:
        return getattr(context, method)(location.value, datatype)
      except SerializationTypeError as exc:
        errors.append(exc)
    error_lines = ['Unable to {} MultiType for value "{}".'.format(method, type(location.value).__name__)]
    for error in errors:
      error_lines.append('  * {}: {}'.format(
        type(error.location.datatype).__name__, error.message))
    raise SerializationTypeError(location, '\n'.join(error_lines))

  def deserialize(self, context, location):
    return self._do(context, location, 'deserialize')

  def serialize(self, context, location):
    return self._do(context, location, 'serialize')


@implements(IDeserializer, ISerializer)
class UnionTypeConverter(object):

  def deserialize(self, context, location):
    if not isinstance(location.value, abc.Mapping):
      raise SerializationTypeError(location)

    datatype = location.datatype  # type: UnionType
    type_key = datatype.type_key
    if type_key not in location.value:
      raise SerializationValueError(location,
        'required key "{}" not found'.format(type_key))

    type_name = location.value[type_key]
    try:
      member = datatype.type_resolver.resolve(type_name)
    except UnknownUnionTypeError:
      raise SerializationValueError(location,
        'unknown union type: "{}"'.format(type_name))

    if datatype.nested:
      struct_type = StructType(member.get_struct())
      key = type_key
      value = location.value[type_key]
    else:
      struct_type = StructType(member.get_struct(), ignore_keys=[type_key])
      key = None
      value = location.value

    return context.deserialize(value, struct_type, key)

  def serialize(self, context, location):
    datatype = location.datatype
    value = location.value
    try:
      member = datatype.type_resolver.reverse(value)
    except UnknownUnionTypeError as exc:
      try:
        members = datatype.type_resolver.members()
      except NotImplementedError:
        message = str(exc)
      else:
        message = 'expected {{{}}}, got {}'.format(
          '|'.join(sorted(x.get_type_name() for x in members)),
          type(value).__name__)
      raise SerializationTypeError(location, message)

    if datatype.nested:
      struct_type = StructType(member.get_struct())
      key = type_key
      value = location.value[type_key]
    else:
      struct_type = StructType(member.get_struct(), ignore_keys=[datatype.type_key])
      key = None
      value = location.value

    result = {datatype.type_key: member.get_name()}
    result.update(context.serialize(value, struct_type, key))
    return result


class JsonDecoration(Decoration):
  pass


class JsonFieldName(JsonDecoration):
  """ A decoration to define the name of a field in a JSON payload. """

  classdef.repr('name')

  def __init__(self, name):
    self.name = name


class JsonRequired(JsonDecoration):
  """ A decorator that defines if a JSON field is required. By default, a
  field that has a default value does not need to be specified in the JSON
  payload. If this decoration exists on a field, it is always required. """

  classdef.repr([])


class _JsonDeserializerSerializerBase(JsonDecoration):
  """ Private. Base class for #JsonDeserializer and #JsonSerializer. """

  classdef.repr([])
  _method_name = None

  def __init__(self, func):
    self.func = func

  @classmethod
  def for_class(cls, search_cls):
    value = cls.first(vars(search_cls).values())
    if value:
      # Make sure the wrapped function accepts the class as the first argument.
      return cls(partial(value.func, search_cls))
    # Fall back to the method name (defined in a sub class).
    if not value and hasattr(search_cls, cls._method_name):
      value = cls(getattr(search_cls, cls._method_name))
    return value


@implements(IDeserializer)
class JsonDeserializer(_JsonDeserializerSerializerBase):
  """ Decorator for a deserializer function on a class. Classes that have a
  member of this type can be deserialized under the #PythonClassType datatype.

  Functions decorated with #JsonDeserializer are invoked as classmethods
  by the deserialization process. """

  _method_name = 'from_json'

  def deserialize(self, context, location):
    return self.func(context, location)


@implements(ISerializer)
class JsonSerializer(_JsonDeserializerSerializerBase):
  """ Decorator for a serializer function on a class. Classes that have a
  member of this type can be deserialized under the #PythonClassType datatype.

  Functions decorated with #JsonSerializer are invoked as classmethods
  by the serialization process. """

  _method_name = 'to_json'

  def serialize(self, context, location):
    return self.func(context, location)
