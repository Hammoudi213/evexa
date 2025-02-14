from datetime import datetime
from app import db
from sqlalchemy.orm import relationship

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DeliveryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('delivery.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)

    delivery = relationship("Delivery", back_populates="items")

class Delivery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_name = db.Column(db.String(200), nullable=False)
    recipient_job = db.Column(db.String(200), nullable=False)
    region = db.Column(db.String(200), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = relationship("DeliveryItem", back_populates="delivery", cascade="all, delete-orphan")