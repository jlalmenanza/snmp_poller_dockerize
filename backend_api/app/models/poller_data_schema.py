from marshmallow import Schema, fields, validate
from backend_api.app.common import schema_fields
from marshmallow.validate import Range


class PollerDataSchema(Schema):
    community_string = schema_fields.String(validate=[validate.Length(min=1, max=255, 
        error="Field cannot be blank and must have a character limit of 255.")])

class IpListSchema(Schema):
    ip_address = schema_fields.String(validate=[validate.Length(min=1, max=50, 
        error="Field cannot be blank and must have a character limit of 50.")])
    device_model = schema_fields.String(validate=[validate.Length(min=1, max=50, 
        error="Field cannot be blank and must have a character limit of 50.")])