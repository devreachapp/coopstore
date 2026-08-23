from datetime import datetime
import uuid

from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db
from decimal import Decimal

class Tenant(db.Model):
    __tablename__ = 'tenants'
    
    id = db.Column(db.Integer, primary_key=True)
    username_slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    business_name = db.Column(db.String(100), nullable=False)
    admin_email = db.Column(db.String(120), unique=True, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    brand_color = db.Column(db.String(7), default="#3b82f6")
    whatsapp_number = db.Column(db.String(20), nullable=True)
    coop_social_user_id = db.Column(db.String(36), unique=True,  index=True) #nullable=False,
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='tenant', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            # --- CRITICAL MAPS TO MATCH YOUR FRONTEND TYPES TYPE DEFINITION ---
            "id": self.id,
            "username": self.username_slug,       # React expects 'username'
            "businessName": self.business_name,   # React expects 'businessName'
            "email": self.admin_email,            # React expects 'email'
            "bio": self.bio,
            "brandColor": self.brand_color,       # React expects 'brandColor'
            "whatsapp": self.whatsapp_number,     # React expects 'whatsapp'

            
            # --- THE MISSING LINK FIX ---
            # Safely serialize child products into a clean dictionary list array.
            # If the list is empty, it returns [], completely satisfying the frontend framework constraints.
            "products": [p.to_dict() for p in self.products] if self.products else []
        }

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(20), nullable=False) # 'Good' or 'Service'
    image_url = db.Column(db.String(255), nullable=True, default="https://placehold.co/300")

    def to_dict(self):
        # Everything inside a function must be indented by an extra 4 spaces
        return {
            "id": self.id, 
            "name": self.name, 
            "description": self.description, 
            "price": self.price, 
            "category": self.category,
            "kind": self.category.lower() if self.category else "good", 
            "imageUrl": self.image_url  # Maps the db snake_case column back to camelCase for React
        }

class Marketer(db.Model):
    __tablename__ = 'marketers'
    
    id = db.Column(db.Integer, primary_key=True)
    cooplead_user_id = db.Column(db.String(100), unique=True, nullable=False, index=True) # ID from Cooplead DB
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    conversions = db.relationship('Conversion', backref='marketer', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "coopleadUserId": self.cooplead_user_id,
            "name": self.name,
            "email": self.email,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }
class Conversion(db.Model):
    __tablename__ = 'conversions'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    marketer_id = db.Column(db.Integer, db.ForeignKey('marketers.id', ondelete="CASCADE"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id', ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete="CASCADE"), nullable=False)
    
    sale_amount = db.Column(db.Float, nullable=False)
    commission_earned = db.Column(db.Float, nullable=False)
    
    # ─── UPDATED LIFECYCLE STATES ───
    # Now supports: 'held' (in escrow), 'seller_fulfilled', 'released' (completed), or 'refunded'
    status = db.Column(db.String(50), default="held") 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ─── NEW ESCROW FIELDS TO ADD ───
    reference = db.Column(db.String(100), unique=True, nullable=True) # Matches tx_coopmart_... from Fincra/Frontend
    gateway = db.Column(db.String(50), default="fincra")             # 'fincra' or 'payaza'
    customer_email = db.Column(db.String(150), nullable=True)         # Customer context tracking
    released_at = db.Column(db.DateTime, nullable=True)               # Audit trail for escrow clearing

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "marketerId": self.marketer_id,
            "tenantId": self.tenant_id,
            "productId": self.product_id,
            "saleAmount": self.sale_amount,
            "commissionEarned": self.commission_earned,
            "status": self.status,
            "reference": self.reference,
            "gateway": self.gateway,
            "customerEmail": self.customer_email,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "releasedAt": self.released_at.isoformat() if self.released_at else None
        }


from datetime import datetime

class EscrowOrder(db.Model):
    __tablename__ = 'escrow_orders'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), unique=True, nullable=False) # tx_coopmart_...
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    marketer_id = db.Column(db.Integer, db.ForeignKey('marketers.id'), nullable=True) # None if organic purchase
    
    # Financial breakdowns
    total_amount = db.Column(db.Float, nullable=False)
    commission_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default="USD")
    gateway = db.Column(db.String(50), default="fincra")
    
    # Lifecycle Status
    status = db.Column(db.String(50), default="held") # "held" | "seller_fulfilled" | "released" | "refunded"
    
    # Customer Metadata
    customer_name = db.Column(db.String(150))
    customer_email = db.Column(db.String(150))
    customer_phone = db.Column(db.String(50))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seller_fulfilled_at = db.Column(db.DateTime, nullable=True)
    buyer_confirmed_at = db.Column(db.DateTime, nullable=True)
    released_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    tenant = db.relationship('Tenant', backref='escrow_orders')
    product = db.relationship('Product', backref='escrow_orders')
    marketer = db.relationship('Marketer', backref='escrow_orders')

class Buyer(db.Model):
    __tablename__ = 'buyers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Password utility helpers
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "createdAt": self.created_at.isoformat() if self.created_at else None
        }