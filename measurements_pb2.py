# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: measurements.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='measurements.proto',
  package='measurements',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x12measurements.proto\x12\x0cmeasurements\"\xea\x03\n\nSessionMsg\x12\x0b\n\x03sid\x18\x01 \x01(\x05\x12\x0c\n\x04uuid\x18\x02 \x01(\x05\x12.\n\x04type\x18\x03 \x01(\x0e\x32 .measurements.SessionMsg.MsgType\x12\x32\n\x08peertype\x18\x04 \x01(\x0e\x32 .measurements.SessionMsg.MsgType\x12\x12\n\nstart_time\x18\x05 \x01(\x01\x12\x0f\n\x07\x63lients\x18\x06 \x03(\t\x12\x31\n\x07samples\x18\x07 \x03(\x0b\x32 .measurements.SessionMsg.Complex\x12\x14\n\x0cmeasurements\x18\x08 \x03(\x02\x12\x33\n\nattributes\x18\t \x03(\x0b\x32\x1f.measurements.SessionMsg.KeyVal\x1a\x1f\n\x07\x43omplex\x12\t\n\x01r\x18\x01 \x01(\x01\x12\t\n\x01j\x18\x02 \x01(\x01\x1a\"\n\x06KeyVal\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\x0b\n\x03val\x18\x02 \x01(\t\"<\n\x07MsgType\x12\x08\n\x04INIT\x10\x00\x12\t\n\x05\x43LOSE\x10\x01\x12\x08\n\x04\x43\x41LL\x10\x02\x12\n\n\x06RESULT\x10\x03\x12\x06\n\x02HB\x10\x04\"7\n\x08PeerType\x12\x0f\n\x0bMEAS_CLIENT\x10\x00\x12\x10\n\x0cIFACE_CLIENT\x10\x01\x12\x08\n\x04ORCH\x10\x02\x62\x06proto3'
)



_SESSIONMSG_MSGTYPE = _descriptor.EnumDescriptor(
  name='MsgType',
  full_name='measurements.SessionMsg.MsgType',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='INIT', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='CLOSE', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='CALL', index=2, number=2,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='RESULT', index=3, number=3,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='HB', index=4, number=4,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=410,
  serialized_end=470,
)
_sym_db.RegisterEnumDescriptor(_SESSIONMSG_MSGTYPE)

_SESSIONMSG_PEERTYPE = _descriptor.EnumDescriptor(
  name='PeerType',
  full_name='measurements.SessionMsg.PeerType',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='MEAS_CLIENT', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='IFACE_CLIENT', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ORCH', index=2, number=2,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=472,
  serialized_end=527,
)
_sym_db.RegisterEnumDescriptor(_SESSIONMSG_PEERTYPE)


_SESSIONMSG_COMPLEX = _descriptor.Descriptor(
  name='Complex',
  full_name='measurements.SessionMsg.Complex',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='r', full_name='measurements.SessionMsg.Complex.r', index=0,
      number=1, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='j', full_name='measurements.SessionMsg.Complex.j', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=341,
  serialized_end=372,
)

_SESSIONMSG_KEYVAL = _descriptor.Descriptor(
  name='KeyVal',
  full_name='measurements.SessionMsg.KeyVal',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='measurements.SessionMsg.KeyVal.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='val', full_name='measurements.SessionMsg.KeyVal.val', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=374,
  serialized_end=408,
)

_SESSIONMSG = _descriptor.Descriptor(
  name='SessionMsg',
  full_name='measurements.SessionMsg',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='sid', full_name='measurements.SessionMsg.sid', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='uuid', full_name='measurements.SessionMsg.uuid', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='type', full_name='measurements.SessionMsg.type', index=2,
      number=3, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='peertype', full_name='measurements.SessionMsg.peertype', index=3,
      number=4, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='start_time', full_name='measurements.SessionMsg.start_time', index=4,
      number=5, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='clients', full_name='measurements.SessionMsg.clients', index=5,
      number=6, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='samples', full_name='measurements.SessionMsg.samples', index=6,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='measurements', full_name='measurements.SessionMsg.measurements', index=7,
      number=8, type=2, cpp_type=6, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='attributes', full_name='measurements.SessionMsg.attributes', index=8,
      number=9, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_SESSIONMSG_COMPLEX, _SESSIONMSG_KEYVAL, ],
  enum_types=[
    _SESSIONMSG_MSGTYPE,
    _SESSIONMSG_PEERTYPE,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=37,
  serialized_end=527,
)

_SESSIONMSG_COMPLEX.containing_type = _SESSIONMSG
_SESSIONMSG_KEYVAL.containing_type = _SESSIONMSG
_SESSIONMSG.fields_by_name['type'].enum_type = _SESSIONMSG_MSGTYPE
_SESSIONMSG.fields_by_name['peertype'].enum_type = _SESSIONMSG_MSGTYPE
_SESSIONMSG.fields_by_name['samples'].message_type = _SESSIONMSG_COMPLEX
_SESSIONMSG.fields_by_name['attributes'].message_type = _SESSIONMSG_KEYVAL
_SESSIONMSG_MSGTYPE.containing_type = _SESSIONMSG
_SESSIONMSG_PEERTYPE.containing_type = _SESSIONMSG
DESCRIPTOR.message_types_by_name['SessionMsg'] = _SESSIONMSG
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

SessionMsg = _reflection.GeneratedProtocolMessageType('SessionMsg', (_message.Message,), {

  'Complex' : _reflection.GeneratedProtocolMessageType('Complex', (_message.Message,), {
    'DESCRIPTOR' : _SESSIONMSG_COMPLEX,
    '__module__' : 'measurements_pb2'
    # @@protoc_insertion_point(class_scope:measurements.SessionMsg.Complex)
    })
  ,

  'KeyVal' : _reflection.GeneratedProtocolMessageType('KeyVal', (_message.Message,), {
    'DESCRIPTOR' : _SESSIONMSG_KEYVAL,
    '__module__' : 'measurements_pb2'
    # @@protoc_insertion_point(class_scope:measurements.SessionMsg.KeyVal)
    })
  ,
  'DESCRIPTOR' : _SESSIONMSG,
  '__module__' : 'measurements_pb2'
  # @@protoc_insertion_point(class_scope:measurements.SessionMsg)
  })
_sym_db.RegisterMessage(SessionMsg)
_sym_db.RegisterMessage(SessionMsg.Complex)
_sym_db.RegisterMessage(SessionMsg.KeyVal)


# @@protoc_insertion_point(module_scope)
