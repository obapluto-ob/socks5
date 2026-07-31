from marshmallow import Schema, fields, validate

class AdminSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(min=3))
    created_at = fields.DateTime(dump_only=True)

class ProxyUserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=[
        validate.Length(min=3),
        validate.Regexp(r'^[a-zA-Z][a-zA-Z0-9_]{2,}$', error="Username must start with a letter and contain only letters, numbers, underscores.")
    ])
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=4))
    is_active = fields.Bool(dump_default=True)
    created_at = fields.DateTime(dump_only=True)
    last_rotated = fields.DateTime(dump_only=True)

class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class ConnectionLogSchema(Schema):
    id = fields.Int(dump_only=True)
    client_ip = fields.Str()
    connected_at = fields.DateTime()
    disconnected_at = fields.DateTime()
    bytes_sent = fields.Int()
    bytes_received = fields.Int()
    was_kicked = fields.Bool()

class SystemEventSchema(Schema):
    id = fields.Int(dump_only=True)
    event_type = fields.Str()
    message = fields.Str()
    created_at = fields.DateTime()

class BlockedIPSchema(Schema):
    id = fields.Int(dump_only=True)
    ip_address = fields.Str(required=True)
    reason = fields.Str()
    blocked_at = fields.DateTime(dump_only=True)
