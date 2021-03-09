from backend_api.app.models import db

class OidList(db.Model):
    __tablename__ = 'oid_list'

    id = db.Column(db.Integer, primary_key=True)
    device_model = db.Column(db.String(50), nullable=False)
    oid_key = db.Column(db.String(50), nullable=False)
    oid = db.Column(db.String(255), nullable=False)