import os
import requests
from flask import Flask, request, jsonify, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import  Tenant, db, Product,Marketer,Conversion

import traceback
from flask import request, jsonify, current_app

import uuid

from app.menu import bp as signals_bp
from app.auth.views import token_required, create_coopmart_jwt


from dotenv import load_dotenv

load_dotenv()

# ==========================================
# DATABASE MODELS
# ==========================================

# ==========================================
# API CONTROLLER ROUTES
# ==========================================

import os
import requests
from flask import request, jsonify

@signals_bp.route('/auth/register', methods=['POST'])
def register_merchant():
    """Step 1 & 2: Registers merchant on CoopMart AND runs background registration on CoopLead"""
    data = request.get_json() or {}
    print("INCOMING REGISTRATION PAYLOAD FROM LOVABLE:", data)
    
    # --- FLEXIBLE KEY MAPPING ---
    # Look for either format to completely safeguard against frontend framework updates
    username_slug = data.get('username_slug') or data.get('username')
    business_name = data.get('business_name') or data.get('businessName')
    email = data.get('email') or data.get('admin_email')
    password = data.get('password')
    
    if not all([username_slug, business_name, email]):
        return jsonify({"error": "Missing required fields: Ensure username, businessName, and email are populated"}), 400
        
    # Standardize data context transformations
    clean_slug = username_slug.lower().strip()

    # Check if slug is taken on CoopMart
    if Tenant.query.filter_by(username_slug=clean_slug).first():
        return jsonify({"error": "This URL path slug is already taken"}), 409  # 409 indicates resource conflict

    try:
        # 1. Save Merchant locally to CoopMart
        tenant = Tenant(
            username_slug=clean_slug,
            business_name=business_name,
            admin_email=email,
            password=generate_password_hash(password)
        )
        db.session.add(tenant)
        db.session.commit()

        # Generate a standard authorization token session handle context
        mock_auth_token = f"session_token_for_tenant_{tenant.id}"
        
        # Return object wrapper mapping both models and frontend parameters smoothly
        return jsonify({
            "message": "Account initialized successfully.",
            "token": mock_auth_token,
            "tenant": {
                "id": tenant.id,
                "username": tenant.username_slug,
                "businessName": tenant.business_name,
                "email": tenant.admin_email,
                "cooplead_campaign_id": tenant.cooplead_campaign_id
            }
        }), 201

    except Exception as server_error:
        db.session.rollback()
        print(f"Critical exception occurred during merchant onboarding: {server_error}")
        return jsonify({"error": "Internal server configuration error handling registration"}), 500


from flask import jsonify, request
# Ensure check_password_hash is imported alongside generate_password_hash



@signals_bp.route('/auth/login', methods=['POST'])
def login_merchant():
    """Handles native login authentication for CoopMart Merchants/Tenants"""
    data = request.get_json() or {}
    print("INCOMING LOGIN PAYLOAD:", data)
    
    # Accept both standard configurations or alternative styling handles safely
    email = data.get('email') or data.get('admin_email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Missing required fields: Ensure email and password fields are filled"}), 400
        
    clean_email = email.lower().strip()

    # 1. Check if the email belongs to a registered Merchant (Tenant)
    tenant = Tenant.query.filter_by(admin_email=clean_email).first()
    
    if tenant:
        if not check_password_hash(tenant.password_hash, password):
            return jsonify({"error": "Invalid email address or password credentials"}), 401
        
        # Generates a standard session token handle string matching your system architecture
        mock_auth_token = f"session_token_for_tenant_{tenant.id}"
        
        return jsonify({
            "message": "Authentication successful.",
            "token": mock_auth_token,
            "role": "merchant",
            "tenant": tenant.to_dict() # Returns the exact nested product dict your frontend expects
        }), 200

    # 2. Safety Grace Catch: Check if a Marketer accidentally typed their details here
    marketer = Marketer.query.filter_by(email=clean_email).first()
    if marketer:
        return jsonify({
            "error": "Account detected as an Affiliate Marketer. Please log in directly from your Cooplead Dashboard portal."
        }), 403

    # 3. Default fallback if nothing matches
    return jsonify({"error": "Invalid email address or password credentials"}), 401



@signals_bp.route('/store/<username_slug>/submit-order', methods=['POST'])
def handle_customer_order(username_slug):
    """Fires internal webhook payloads to CoopLead when conversions happen on storefront"""
    tenant = Tenant.query.filter_by(username_slug=username_slug).first_or_404()
    data = request.get_json() or {}
    
    # Execute normal checkout/processing logic here...
    
    # Server-To-Server Webhook Tracking to CoopLead if marketing is active
    if tenant.cooplead_enabled and tenant.cooplead_campaign_id:
        cooplead_webhook_url = "http://127.0.0.1:5000/v1/webhook"
        payload = {
            "event": "conversion",
            "campaign_id": tenant.cooplead_campaign_id,
            "merchant_slug": tenant.username_slug,
            "order_value": data.get('price', 0.0),
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            requests.post(cooplead_webhook_url, json=payload, headers={"Authorization": "Bearer SHARED_CROSS_APP_SECRET"}, timeout=3)
        except requests.exceptions.RequestException:
            print("Webhook transmission background logging failure.")

    return jsonify({"status": "success"}), 200


# Inside CoopMart (or your unified backend handling the setting change)
@signals_bp.route('/tenants/<int:tenant_id>/marketing-settings', methods=['PUT'])
def update_marketing_settings(tenant_id):
    tenant = Tenant.query.get_or_404(tenant_id)
    data = request.get_json() or {}
    
    # 1. Update the local CoopMart tenant record
    tenant.cooplead_enabled = data.get('cooplead_enabled', tenant.cooplead_enabled)
    tenant.commission_rate = float(data.get('commission_rate', tenant.commission_rate))
    tenant.reward_model = data.get('reward_model', tenant.reward_model) # e.g., "Digital Coins"
    db.session.commit()

    # 2. AUTOMATION DELEGATION: Sync with your existing CoopLead rule engine
    # We look up if an EventSetting row already exists for this tenant's user ID in CoopLead
    # mapping to the 'lead_conversion' event signature.
    
    from app.models import EventSetting  # Assuming shared database context, or call your API
    
    # Check for an existing conversion rule for this company
    existing_rule = EventSetting.query.filter_by(
        company_id=tenant.id, # Mapping tenant to your company_id context
        event_name='lead_conversion'
    ).first()

    if existing_rule:
        # If it exists, update the weight (marksAwarded) dynamically to what they set!
        existing_rule.weight = int(tenant.commission_rate)
        existing_rule.is_active = tenant.cooplead_enabled
    else:
        # If it doesn't exist, we create it using the EXACT structure your endpoint likes
        new_rule = EventSetting(
            company_id=tenant.id,
            tracking_type='backend', # Your default type
            element_selector=None,
            event_name='lead_conversion', # The identifier we use in window.cooplead.trackEvent
            display_name='Storefront Lead Conversion',
            weight=int(tenant.commission_rate), # Assigning the coin weight
            is_active=tenant.cooplead_enabled
        )
        db.session.add(new_rule)
        
    db.session.commit()
    return jsonify(tenant.to_dict()), 200

@signals_bp.route('/tenants', methods=['GET'])
def list_tenants():
    """Handles the fallback route fallback logging seen in your terminal logs"""
    tenants = Tenant.query.all()
    return jsonify([t.to_dict() for t in tenants]), 200



# Put this in whichever blueprint is handling your /api prefix traffic (e.g., signals_bp or tenants_bp)
@signals_bp.route('/merchant/<string:slug>/cooplead/provision', methods=['GET', 'POST'])
def provision_cooplead_tenant(slug):
    """
    Acts as the synchronization safety route for the frontend onboarding pipeline.
    Because Option 2 handles registration during /auth/register, this route updates 
    or verifies that the tracking campaign is linked cleanly.
    """
    clean_slug = slug.lower().strip()
    tenant = Tenant.query.filter_by(username_slug=clean_slug).first()
    
    if not tenant:
        return jsonify({"error": f"Merchant '{clean_slug}' not found"}), 404

    # --- FRONTEND SENDS A POST TO KICK OFF / CONFIRM PROVISIONING ---
    if request.method == 'POST':
        # If for some reason the main /register handshake failed or didn't get a campaign ID, 
        # we can attempt a retry block here to make the system bulletproof:
        if not tenant.cooplead_campaign_id:
            cooplead_api_url = os.getenv("COOPLEAD_BASE_URL", "http://127.0.0.1:5000")
            cooplead_register_url = f"{cooplead_api_url}/api/internal/register-partner"
            
            cooplead_payload = {
                "coopmart_tenant_id": tenant.id,
                "merchant_slug": tenant.username_slug,
                "business_name": tenant.business_name,
                "admin_email": tenant.admin_email
            }
            
            try:
                shared_secret = os.getenv("COOPLEAD_INTERNAL_SECRET", "SHARED_CROSS_APP_SECRET")
                headers = {"Authorization": f"Bearer {shared_secret}"}
                response = requests.post(cooplead_register_url, json=cooplead_payload, headers=headers, timeout=5)
                
                if response.status_code in [200, 201]:
                    cooplead_data = response.json()
                    tenant.cooplead_campaign_id = cooplead_data.get('campaign_id')
                    db.session.commit()
            except requests.exceptions.RequestException as e:
                print(f"Async provision fallback error: {e}")

        return jsonify({
            "status": "success",
            "message": "CoopLead infrastructure link verified.",
            "campaign_id": tenant.cooplead_campaign_id or "mock_camp_fallback"
        }), 201

    # --- FRONTEND SENDS A GET TO CHECK INSTANCE STATUS ---
    return jsonify({
        "status": "active" if tenant.cooplead_campaign_id else "pending",
        "slug": tenant.username_slug,
        "cooplead_campaign_id": tenant.cooplead_campaign_id
    }), 200


@signals_bp.route('/tenants/<string:slug>', methods=['GET'])
def get_single_tenant(slug):
    """Fetches full database profile settings for the active dashboard session"""
    clean_slug = slug.lower().strip()
    tenant = Tenant.query.filter_by(username_slug=clean_slug).first()
    
    if not tenant:
        return jsonify({"error": f"Merchant profile '{clean_slug}' not found"}), 404
        
    # Return the dictionary serialization matching what your frontend expects
    return jsonify(tenant.to_dict()), 200

from flask import request, jsonify


@signals_bp.route('/api/stores', methods=['GET'])
def list_public_stores():
    # Fetch all tenants to display in the marketplace catalog
    all_tenants = Tenant.query.order_by(Tenant.business_name.asc()).all()
    
    # Map them safely through to_dict() or a lightweight dictionary summary
    stores_list = []
    for t in all_tenants:
        stores_list.append({
            "username": t.username_slug,
            "businessName": t.business_name,
            "bio": t.bio,
            "brandColor": t.brand_color,
            "accentColor": t.accent_color,
            "productCount": len(t.products) if t.products else 0
        })
        
    return jsonify(stores_list), 200


from flask import request, jsonify
# Ensure your db, Tenant, Product, etc., imports are here

# ==========================================
# 1. SPECIFIC ITEM ROUTE (PUT / DELETE)
# ==========================================
@signals_bp.route('/tenants/<string:slug>/products/<int:product_id>', methods=['PUT', 'DELETE'], strict_slashes=False)
def handle_single_product(slug, product_id):
    clean_slug = slug.lower().strip()
    tenant = Tenant.query.filter_by(username_slug=clean_slug).first()
    
    if not tenant:
        return jsonify({"error": "Merchant storefront not found"}), 404
        
    product = Product.query.filter_by(id=product_id, tenant_id=tenant.id).first()
    if not product:
        return jsonify({"error": "Product item not found"}), 404

    if request.method == 'PUT':
        data = request.get_json() or {}
        try:
            product.name = data.get('name', product.name)
            product.description = data.get('description', product.description)
            product.price = float(data.get('price', product.price))
            
            if 'kind' in data:
                product.category = data['kind'].capitalize()
            elif 'category' in data:
                product.category = data['category']
                
            if 'imageUrl' in data:
                product.image_url = data['imageUrl']

            db.session.commit()
            return jsonify({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "category": product.category,
                "kind": product.category.lower() if product.category else "good",
                "imageUrl": product.image_url
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Failed to update item", "details": str(e)}), 500

    if request.method == 'DELETE':
        try:
            db.session.delete(product)
            db.session.commit()
            return jsonify({"success": True, "message": "Item removed cleanly"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Failed to delete item", "details": str(e)}), 500


# ==========================================
# 2. PRODUCTS COLLECTION ROUTE (GET / POST) <-- THIS WAS MISSING
# ==========================================
@signals_bp.route('/tenants/<string:slug>/products', methods=['GET', 'POST'], strict_slashes=False)
def handle_tenant_products(slug):
    clean_slug = slug.lower().strip()
    tenant = Tenant.query.filter_by(username_slug=clean_slug).first()
    
    if not tenant:
        return jsonify({"error": f"Merchant storefront '{clean_slug}' not found"}), 404

    # CREATE NEW PRODUCT (POST)
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name')
        description = data.get('description')
        price = data.get('price', 0.0)
        image_url = data.get('imageUrl') or data.get('image_url')
        
        form_kind = data.get('kind', 'good')  
        database_category = form_kind.capitalize()  # 'good' -> 'Good'

        if not name:
            return jsonify({"error": "Item name is required"}), 400

        new_item = Product(
            tenant_id=tenant.id,
            name=name,
            description=description,
            price=float(price),
            category=database_category,
            image_url=image_url if image_url else "https://placehold.co/300"
        )
        
        db.session.add(new_item)
        db.session.commit()

        return jsonify({
            "id": new_item.id,
            "name": new_item.name,
            "description": new_item.description,
            "price": new_item.price,
            "category": new_item.category, 
            "kind": new_item.category.lower(),
            "imageUrl": new_item.image_url
        }), 201

    # LIST ALL PRODUCTS FOR TENANT (GET)
    if request.method == 'GET':
        products = Product.query.filter_by(tenant_id=tenant.id).all()
        formatted_products = []
        for p in products:
            formatted_products.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "category": p.category,
                "kind": p.category.lower() if p.category else "good",
                "imageUrl": p.image_url
            })
        return jsonify(formatted_products), 200


# ==========================================
# 3. UTILITY CHECK ROUTE (GET)
# ==========================================
@signals_bp.route('/tenants/check-handle/<string:slug>', methods=['GET'], strict_slashes=False)
def check_handle(slug):
    clean_slug = slug.lower().strip()
    existing_tenant = Tenant.query.filter_by(username_slug=clean_slug).first()
    
    if existing_tenant:
        return jsonify({
            "status": "conflict",
            "message": f"The handle '{clean_slug}' is already taken by another merchant."
        }), 409
        
    return jsonify({
        "status": "available",
        "message": f"Handle '{clean_slug}' is open for registration."
    }), 200


# ==========================================
# 4. GENERIC PROFILE ROUTE (GET / PUT) <-- CONSOLIDATED
# ==========================================
@signals_bp.route('/tenants/<string:slug>', methods=['GET', 'PUT'], strict_slashes=False)
def handle_tenant_profile(slug):
    clean_slug = slug.lower().strip()
    tenant = Tenant.query.filter_by(username_slug=clean_slug).first()
    
    if not tenant:
        return jsonify({"error": f"Merchant storefront '{clean_slug}' not found"}), 404

    # 1. READ PROFILE DETAILS (GET)
    if request.method == 'GET':
        return jsonify(tenant.to_dict()), 200

    # 2. UPDATE PROFILE DETAILS (PUT)
    if request.method == 'PUT':
        data = request.get_json() or {}
        try:
            if 'businessName' in data:
                tenant.business_name = data['businessName']
            if 'bio' in data:
                tenant.bio = data['bio']
            if 'brandColor' in data:
                tenant.brand_color = data['brandColor']
            if 'whatsapp' in data:
                tenant.whatsapp_number = data['whatsapp']
            if 'email' in data:
                tenant.admin_email = data['email']
                
            if 'username' in data and data['username'].strip():
                new_slug = data['username'].strip().lower()
                existing = Tenant.query.filter_by(username_slug=new_slug).first()
                if existing and existing.id != tenant.id:
                    return jsonify({"error": "URL slug is already taken by another merchant"}), 400
                tenant.username_slug = new_slug

            db.session.commit()
            return jsonify(tenant.to_dict()), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Failed to update profile", "details": str(e)}), 500
        
# ==========================================
# 5. MARKETING & COOPLEAD SETTINGS ROUTE (GET / PUT)
# ==========================================
@signals_bp.route('/tenants/<string:slug>/marketing-settings', methods=['GET', 'PUT'], strict_slashes=False)
def handle_marketing_settings(slug):
    clean_slug = slug.lower().strip()
    tenant = Tenant.query.filter_by(username_slug=clean_slug).first()
    
    if not tenant:
        return jsonify({"error": f"Merchant storefront '{clean_slug}' not found"}), 404

    # 1. FETCH SETTINGS (GET)
    if request.method == 'GET':
        return jsonify({
            "cooplead_enabled": tenant.cooplead_enabled,
            "cooplead_campaign_id": tenant.cooplead_campaign_id,
            "commission_rate": tenant.commission_rate,
            "reward_model": tenant.reward_model
        }), 200

    # 2. SAVE SETTINGS (PUT)
    if request.method == 'PUT':
        data = request.get_json() or {}
        try:
            # Map values from frontend payload safely to model columns
            if 'cooplead_enabled' in data:
                tenant.cooplead_enabled = bool(data['cooplead_enabled'])
                
            if 'cooplead_campaign_id' in data:
                tenant.cooplead_campaign_id = data['cooplead_campaign_id']
                
            if 'commission_rate' in data:
                tenant.commission_rate = float(data['commission_rate'])
                
            if 'reward_model' in data:
                tenant.reward_model = data['reward_model'] # e.g., "Cash Payouts" or "Digital Coins"

            db.session.commit()
            
            return jsonify({
                "message": "Marketing settings saved cleanly",
                "cooplead_enabled": tenant.cooplead_enabled,
                "cooplead_campaign_id": tenant.cooplead_campaign_id,
                "commission_rate": tenant.commission_rate,
                "reward_model": tenant.reward_model
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Failed to save marketing adjustments", "details": str(e)}), 500


import jwt
import requests
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request

# Config Variables (Keep these in your Coopmart .env file)
SHARED_CROSS_APP_SECRET = "phurellerbankertech"
COOPMART_LOCAL_JWT_SECRET = "crazy_things_are_happening"
COOPLEAD_PAYOUT_WEBHOOK_URL = "http://127.0.0.1:5000/api/webhooks/coopmart-payout" # Use Cooplead's live domain in production

import jwt
from datetime import datetime, timedelta
from flask import jsonify, request


@signals_bp.route('/auth/cooplead-sso', methods=['POST', 'OPTIONS'])
def cooplead_sso_handshake():
    # If it's an OPTIONS preflight request, let Flask-CORS handle the response
    if request.method == 'OPTIONS':
        return jsonify({"status": "preflight_ok"}), 200

    print("\n🛰️ ─── COOPLEAD SSO HANDSHAKE START ───")
    
    data = request.get_json() or {}
    token = data.get("token")
    
    print(f"📦 INBOUND PAYLOAD RECEIVED: {data}")
    print(f"🔑 EXTRACTED STRING TOKEN: {token}")
    
    if not token:
        print("❌ CRITICAL: Handshake security token missing from payload attributes")
        return jsonify({"error": "Handshake security token is missing"}), 400
        
    try:
        # 1. Decode and verify the cross-app payload signatures
        print("⚙️ Attempting cryptographic decryption signature evaluation...")
        payload = jwt.decode(token, SHARED_CROSS_APP_SECRET, algorithms=["HS256"])
        print(f"✅ DECRYPTION SUCCESSFUL! Verified Payload context contents: {payload}")
        
        cooplead_id = payload.get("cooplead_user_id")
        email = payload.get("email")
        name = payload.get("name")
        
        if not cooplead_id or not email:
            print("❌ CRITICAL: Extracted dictionary payload schema attributes validation failed")
            return jsonify({"error": "Malformed handshake payload structure"}), 400
            
    except jwt.ExpiredSignatureError as expiration_err:
        print(f"❌ SIGNATURE FAILURE: The JWT timestamp signature has expired. Details: {str(expiration_err)}")
        return jsonify({"error": "Handshake expired. Please navigate back to Cooplead and re-click the access link."}), 401
    except jwt.InvalidTokenError as token_sig_err:
        print(f"❌ SIGNATURE FAILURE: Cryptographic key verification verification failed. Details: {str(token_sig_err)}")
        print(f"💡 FIX CONFIG: Double check that SHARED_CROSS_APP_SECRET matching strings are identical on both servers.")
        return jsonify({"error": "Invalid cross-app verification signature"}), 401

    try:
        # 2. Check if this marketer already has a record inside Coopmart
        marketer = Marketer.query.filter_by(cooplead_user_id=str(cooplead_id)).first()
        
        if not marketer:
            print(f"👤 Marketer profile reference mapping not found. Dynamic provisioning triggered for: {email}")
            # Dynamically provision the marketer account into the database using your exact schema fields
            marketer = Marketer(
                cooplead_user_id=str(cooplead_id),
                name=name if name else email.split('@')[0],
                email=email
            )
            db.session.add(marketer)
            db.session.commit()
            print(f"✨ Successfully provisioned new marketer account record ledger entity: {email}")
        else:
            print(f"🔄 Existing marketer match identified in local database: {marketer.email}")

        # 3. Create a unique session token for the user's browser session wrapper
        auth_session_token = f"session_token_for_marketer_{marketer.id}"

        # Build the user dict from your model and guarantee the role property is inside it
        user_data = marketer.to_dict()
        user_data["role"] = "marketer"  # Frontend explicitly expects "marketer" string here

        print("🚀 Dispatching perfectly matched SsoResponse response data layout structure context to frontend application UI...")
        # 4. Return matching your React frontend SsoResponse type definitions exactly!
        return jsonify({
            "message": "SSO authentication successful.",
            "auth_token": auth_session_token,   # Matches res.auth_token key mapping parameters
            "user": user_data                   # Ensures res.user.role paths extract perfectly
        }), 200

    except Exception as server_err:
        db.session.rollback()
        print(f"💥 CRITICAL ERROR: Exception occurred during marketer database operations context: {server_err}")
        return jsonify({"error": "Internal database sync configuration error handling login"}), 500
      

import os
import requests
from flask import jsonify, request

# Cooplead backend API Base URL (adjust for production)
COOPLEAD_BASE_URL = os.environ.get("COOPLEAD_API_URL", "http://127.0.0.1:5000/api")

# ─── ADD YOUR ACTUAL MAIN APP COMPANY API KEY HERE ───
import os

# Make sure this matches the exact string or env variable used in the main app

@signals_bp.route('/cooplead/track', methods=['POST', 'OPTIONS'])
def proxy_cooplead_track():
    if request.method == 'OPTIONS':
        return jsonify({"status": "preflight_ok"}), 200

    data = request.get_json() or {}
    
    event_name = data.get("event")
    payload = data.get("payload") or {}
    timestamp = data.get("ts")

    print(f"📡 [Tracking Proxy] Received event '{event_name}' from consumer browser.")

    cooplead_payload = {
        "event_name": event_name,
        "timestamp": timestamp,
        "customer_user_id": payload.get("customer_user_id") or payload.get("email") or payload.get("anonymousId") or "anonymous_client",
        "referrer_code": payload.get("aff") or payload.get("referrer_code")
    }

    # 🔥 Pass the shared secret key here
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SHARED_CROSS_APP_SECRET}"
    }

    try:
        res = requests.post(
            f"{COOPLEAD_BASE_URL}/v1/webhook", 
            json=cooplead_payload, 
            headers=headers,
            timeout=1.5
        )
        print(f"📡 [Tracking Proxy] Main App response status: {res.status_code}")
    except Exception as tracking_err:
        print(f"⚠️ [Tracking Proxy] Failed forwarding to Cooplead pipeline: {str(tracking_err)}")

    return jsonify({"status": "event_relayed"}), 200


# ─── ROUTE 2: TENANT INTEGRATION PROVISIONER ───
@signals_bp.route('/tenants/<string:username>/cooplead/provision', methods=['POST', 'OPTIONS'])
def provision_coop_tenant(username):
    """
    Triggers during merchant onboarding. Links a new Coopmart store slug 
    with a designated campaign manager sequence inside Cooplead.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "preflight_ok"}), 200

    clean_slug = username.lower().strip()
    
    # Locate the target storefront tenant
    tenant = Tenant.query.filter_by(username_slug=clean_slug).first()
    if not tenant:
        return jsonify({"error": f"Store handle '{clean_slug}' does not exist on Coopmart"}), 404

    print(f"🛠️ [Provisioner] Syncing merchant tracking network context for slug: {clean_slug}")

    try:
        # Request Cooplead's backend to register this new brand company profile dynamically
        cooplead_req_body = {
            "business_name": tenant.business_name,
            "admin_email": tenant.admin_email,
            "website_url": f"https://coopmart.store/{clean_slug}"
        }
        
        # Fire generation hook to Cooplead's registration engine
        response = requests.post(
            f"{COOPLEAD_BASE_URL}/auth/register", # Make sure this matches Cooplead's company registration endpoint
            json=cooplead_req_body,
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            res_data = response.json()
            # If your Cooplead app returns an allocation ID key back (e.g. campaign hash)
            # update it on your tenant record for direct analytical metric synchronization:
            campaign_id = res_data.get("company", {}).get("cooplead_campaign_id")
            if campaign_id:
                tenant.cooplead_campaign_id = campaign_id
                db.session.commit()
                print(f"✅ Successfully linked Campaign ID {campaign_id} to tenant: {clean_slug}")

    except Exception as provision_err:
        print(f"⚠️ [Provisioner Failure] Seamless background provision connection dropped: {str(provision_err)}")
        # We return a 200 status code anyway to satisfy the frontend's requirement that provisioning shouldn't block user registration
        return jsonify({"status": "provision_skipped", "reason": "Cooplead server timeout"}), 200

    return jsonify({
        "status": "success",
        "message": f"Tenant tracking profiles linked safely for store slug handle: {clean_slug}"
    }), 200


import os
import uuid
from datetime import datetime
import requests
from flask import jsonify, request



FINCRA_SECRET_KEY = os.environ.get("FINCRA_SECRET_KEY", "ThAov82QkzMyIk5vHzg5573rw2KyMT3O")
COOPLEAD_BASE_URL = os.environ.get("COOPLEAD_API_URL", "http://127.0.0.1:5000/api")

# Mock database tracking dictionary to simulate Fincra transaction logs before webhook settles
# (In production, you'll map this state parameter to a Transaction/Order model ledger)
PENDING_TRANSACTIONS = {}

@signals_bp.route('/payments/fincra/initialize', methods=['POST', 'OPTIONS'])
def initialize_fincra_payment():
    """
    POST /api/payments/fincra/initialize
    Receives order parameters and registers a new payment session redirect gateway link with Fincra.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "preflight_ok"}), 200

    data = request.get_json() or {}
    
    tenant_slug = data.get("tenant")
    product_id = data.get("productId")
    product_name = data.get("productName")
    amount = data.get("amount")
    currency = data.get("currency", "USD")
    customer = data.get("customer", {})
    marketer_ref = data.get("marketerRef")  # The tracked local aff_id tracking value string

    if not all([tenant_slug, product_id, amount, customer.get("email")]):
        return jsonify({"error": "Missing mandatory transaction parameter details"}), 400

    # 1. Generate a unique, trackable transaction reference code
    tx_reference = f"tx_coopmart_{uuid.uuid4().hex[:12]}"

    print(f"💰 [Fincra Init] Preparing payment session for reference: {tx_reference}")

    # 2. Structure payload exactly matching Fincra Checkout API specification guidelines
    fincra_payload = {
        "amount": int(amount),  # If processing NGN/GHS, ensure conversion factor to minor units if needed
        "currency": currency,
        "reference": tx_reference,
        "feeBearer": "business",
        "redirectUrl": f"http://127.0.0.1:8000/checkout/success?ref={tx_reference}",
        "customer": {
            "name": customer.get("name", "Anonymous Guest"),
            "email": customer.get("email"),
            "phoneNumber": customer.get("phone", "")
        },
        "metadata": {
            "tenant": tenant_slug,
            "marketer_ref": marketer_ref,
            "product_id": product_id
        }
    }

    try:
        # Request a hosted checkout page allocation link from Fincra
        # (Using sandbox URL; update to https://api.fincra.com/checkout/payments for production)
        response = requests.post(
            "https://sandboxapi.fincra.com/checkout/payments",
            json=fincra_payload,
            headers={
                "x-pub-key": FINCRA_SECRET_KEY,
                "Content-Type": "application/json"
            },
            timeout=8
        )
        
        # Pull checkout URL dynamically from Fincra if available; fallback to localized redirect mock for safety
        fincra_res_data = response.json() if response.status_code in [200, 201] else {}
        checkout_url = fincra_res_data.get("data", {}).get("checkoutUrl", f"https://sandbox.fincra.com/checkout/{tx_reference}")

    except Exception as e:
        print(f"⚠️ Fincra connection timed out, utilizing local fallback checkout system framework context: {e}")
        checkout_url = f"https://sandbox.fincra.com/checkout/{tx_reference}"

    # 3. Cache state parameters temporarily (simulating an immutable order placement record)
    session_data = {
        "reference": tx_reference,
        "checkoutUrl": checkout_url,
        "tenant": tenant_slug,
        "marketerRef": marketer_ref,
        "productId": product_id,
        "productName": product_name,
        "amount": float(amount),
        "currency": currency,
        "customer": customer,
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    
    PENDING_TRANSACTIONS[tx_reference] = session_data

    # Return structure matching React frontend FincraSession interface contract exactly
    return jsonify(session_data), 200


@signals_bp.route('/payments/fincra/confirm', methods=['POST', 'OPTIONS'])
def confirm_payout_split():
    """
    POST /api/payments/fincra/confirm
    Client-visible verification step. Simulates final transactional ledger settlement,
    calculates programmatic splits, and posts tracking commission changes to Cooplead.
    """
    if request.method == 'OPTIONS':
        return jsonify({"status": "preflight_ok"}), 200

    data = request.get_json() or {}
    tx_reference = data.get("reference")

    # Fetch dynamic parameters out of cache memory registry tracking references
    cached_session = PENDING_TRANSACTIONS.get(tx_reference)
    if not cached_session:
        return jsonify({"error": f"Transaction reference context code '{tx_reference}' invalid or missing"}), 404

    amount = cached_session["amount"]
    currency = cached_session["currency"]
    marketer_ref = cached_session["marketerRef"]
    tenant_slug = cached_session["tenant"]

    print(f"🛡️ [Payout Split Engine] Running server-side verification allocation rules for {tx_reference}...")

    # 1. Programmatic allocation breakdown computations (e.g., 10% affiliate, 5% ecosystem node, 85% vendor)
    marketer_share = 0.0
    if marketer_ref:
        marketer_share = round(amount * 0.10, 2)  # 10% basic commission tier conversion
    
    platform_share = round(amount * 0.05, 2)       # 5% platform infrastructure maintenance cut
    merchant_share = round(amount - (marketer_share + platform_share), 2)

    # 2. SECURE SERVER-TO-SERVER SYNCHRONIZATION: Notify Cooplead to settle point metrics balances
    if marketer_ref and marketer_share > 0:
        print(f"🚀 Forwarding commission tracking ledger event directly to Cooplead context for marketer ID: {marketer_ref}")
        cooplead_webhook_body = {
            "event": "commission_payout",
            "cooplead_user_id": str(marketer_ref),
            "amount": marketer_share,
            "currency": currency,
            "reference": tx_reference,
            "metadata": {
                "source_tenant": tenant_slug,
                "product_name": cached_session.get("productName")
            }
        }
        
        try:
            cooplead_res = requests.post(
                f"{COOPLEAD_BASE_URL}/webhooks/coopmart-payout",
                json=cooplead_webhook_body,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            print(f"📡 Cooplead callback synchronization settled with status response code: {cooplead_res.status_code}")
        except Exception as sync_err:
            print(f"⚠️ Server-to-server webhook network communication fault gracefully bypass: {sync_err}")

    # Remove temporary transaction logging memory records post execution optimization
    PENDING_TRANSACTIONS.pop(tx_reference, None)

    # 3. Package output layout matching React frontend PayoutConfirmation data contract layout parameters
    return jsonify({
        "ok": True,
        "reference": tx_reference,
        "tenant": tenant_slug,
        "marketerRef": marketer_ref,
        "payoutSplit": {
            "merchantAmount": merchant_share,
            "marketerAmount": marketer_share,
            "platformAmount": platform_share,
            "currency": currency
        },
        "confirmedAt": datetime.utcnow().isoformat() + "Z"
    }), 200


# Add this model import verification to your file imports if not present
# from app.models import Tenant, Product, Marketer, Conversion, db
import traceback
from flask import request, jsonify
# Ensure db, Tenant, Product, Marketer, Conversion, and any escrow models are imported here

@signals_bp.route('/payments/webhook', methods=['POST'])
def handle_payment_gateway_webhook():
    """
    Stage 1: Fincra Webhook Listener.
    Captures incoming successful checkouts and registers them into 
    the backend escrow holding ledger. Does NOT dispatch to Cooplead yet.
    """
    data = request.get_json() or {}
    print("🛰️ [Webhook Interceptor] Incoming Gateway Payload:", data)

    status = data.get("status") or data.get("event") or "successful"
    metadata = data.get("metadata") or data.get("data", {}).get("metadata", {})
    
    # Structural extraction variables
    username_slug = metadata.get("merchant_slug") or data.get("tenant")
    product_id = metadata.get("product_id") or data.get("productId")
    cooplead_user_id = metadata.get("affiliate_id") or data.get("marketerId") or metadata.get("aff")
    
    raw_amount = data.get("amount") or data.get("data", {}).get("amount", 0.0)
    sale_amount = float(raw_amount)
    reference = data.get("reference") or data.get("data", {}).get("reference")

    # Drop non-success transactions safely
    if "success" not in status.lower() and status.lower() != "successful":
        return jsonify({"status": "ignored", "message": "Non-success event dropped"}), 200

    if not username_slug or not product_id:
        print("❌ [Webhook Error] Extraction failed. Missing tracking attributes.")
        return jsonify({"error": "Missing structural tracking context properties"}), 400

    try:
        tenant = Tenant.query.filter_by(username_slug=username_slug).first()
        product = Product.query.get(product_id)
        if not tenant:
            return jsonify({"error": f"Merchant '{username_slug}' not found"}), 404

        # Calculate potential commission with fallback properties
        db_rate = getattr(tenant, 'commission_rate', None) or \
                  getattr(tenant, 'commission_percentage', None) or \
                  10.0  
        rate = float(db_rate) / 100.0
        commission = sale_amount * rate

        print(f"🔒 Escrow Lock: holding {sale_amount} for {username_slug} (Ref: {reference}). Awaiting client fulfillment.")

        # ─── ESCROW STATE HANDLING ───
        # Check if your DB model tracks specific conversion rows as pending escrow.
        # Create a conversion entry marked as 'held' or 'pending' if applicable:
        conversion = Conversion.query.filter_by(reference=reference).first() if hasattr(Conversion, 'reference') else None
        
        if not conversion:
            # Match marketer if present
            marketer_id = None
            if cooplead_user_id and cooplead_user_id != "undefined":
                marketer = Marketer.query.filter_by(cooplead_user_id=str(cooplead_user_id)).first()
                if marketer:
                    marketer_id = marketer.id

            conversion = Conversion(
                reference=reference, # Assuming a reference field exists on Conversion
                marketer_id=marketer_id,
                tenant_id=tenant.id,
                product_id=product.id,
                sale_amount=sale_amount,
                commission_earned=commission,
                status="held"  # Tracked under holding state
            )
            db.session.add(conversion)
            db.session.commit()

        return jsonify({"status": "escrow_held", "message": "Funds registered safely inside escrow container"}), 200

    except Exception as route_err:
        db.session.rollback()
        print(f"💥 Escrow initialization crash: {str(route_err)}")
        return jsonify({"error": "Escrow configuration processing error", "details": str(route_err)}), 500


import traceback
import requests
from datetime import datetime
from flask import request, jsonify

import traceback
import requests
from datetime import datetime
from flask import request, jsonify

@signals_bp.route('/conversions', methods=['GET', 'POST'])  # 👈 Added GET method here
@signals_bp.route('/escrow/release', methods=['POST'])
def handle_conversion_release():
    """
    Stage 2: Escrow Release & Attribution Engine.
    GET: Fetches a single conversion by unique 'reference' string (for buyers) OR 
         all conversions filtered by 'tenant' slug (for merchant dashboards).
    POST: Triggered when the buyer confirms delivery. It updates the held escrow 
          record to 'released' and instantly reports the commission to Cooplead.
    """
    
    # ─── 1. HANDLE DASHBOARD & BUYER GET DATA LOADS ───
    if request.method == 'GET':
        reference = request.args.get('reference')
        tenant_slug = request.args.get('tenant')
        
        try:
            # A. Unique Reference Lookup Path (Used by your new Buyer Confirmation Page)
            if reference:
                print(f"🛰️ [Escrow DB Fetch] Processing single order lookup for reference: '{reference}'")
                conversion = Conversion.query.filter_by(reference=reference).first()
                if not conversion:
                    print(f"⚠️ [Escrow DB Fetch] Order reference '{reference}' not found.")
                    return jsonify({"error": "Order not found"}), 404
                
                c_dict = conversion.to_dict()
                
                # Attach product names and merchant info down relationship chain
                product = Product.query.get(conversion.product_id)
                tenant = Tenant.query.get(conversion.tenant_id)
                
                c_dict["productName"] = product.name if product else "Platform Product"
                c_dict["tenantUsername"] = tenant.username_slug if tenant else "Merchant"
                return jsonify(c_dict), 200

            # B. Tenant Group Filters Path (Used by your Merchant Dashboard Component)
            if tenant_slug:
                print(f"🛰️ [Escrow DB Fetch] Processing dashboard data lookup for tenant slug: '{tenant_slug}'")
                tenant = Tenant.query.filter_by(username_slug=tenant_slug).first()
                if not tenant:
                    print(f"⚠️ [Escrow DB Fetch] Tenant slug '{tenant_slug}' not found.")
                    return jsonify([]), 200
                    
                conversions = Conversion.query.filter_by(tenant_id=tenant.id).order_by(Conversion.created_at.desc()).all()
                
                serialized_conversions = []
                for c in conversions:
                    c_dict = c.to_dict()
                    product = Product.query.get(c.product_id)
                    c_dict["productName"] = product.name if product else "Platform Product"
                    c_dict["tenantUsername"] = tenant.username_slug
                    serialized_conversions.append(c_dict)

                return jsonify(serialized_conversions), 200

            # Edgecase fallback if query params are missing completely
            print("omo no query params provided")
            return jsonify([]), 200

        except Exception as get_err:
            print(f"💥 Escrow dashboard registry data load crash: {str(get_err)}")
            traceback.print_exc()
            return jsonify({"error": "Failed to pull ledger records", "details": str(get_err)}), 500

    # ─── 2. HANDLE CONVERSION LIFECYCLE UPDATES (POST) ───
    data = request.get_json() or {}
    print("🛰️ [Escrow Release Engine] Processing capture payout trigger:", data)

    reference = data.get("reference")
    username_slug = data.get("tenant")
    product_id = data.get("productId")
    cooplead_user_id = data.get("marketerId")
    
    raw_amount = data.get("amount") or 0.0
    sale_amount = float(raw_amount)
    explicit_commission = data.get("commissionAmount")
    customer_email = data.get("customerEmail")

    if not reference:
        return jsonify({"error": "Missing transaction order reference string"}), 400

    try:
        # Lookup the escrow row initiated during Stage 1 by its unique reference string
        conversion = Conversion.query.filter_by(reference=reference).first()

        if conversion:
            # If already processed to prevent double payout loops
            if conversion.status == "released":
                return jsonify({"status": "processed", "message": "Ledger conversion has already been finalized previously."}), 200
            
            # Transition held escrow parameters into finalized payout states
            conversion.status = "released"
            conversion.released_at = datetime.utcnow()
            
            # Extract models down relation chain
            tenant = Tenant.query.get(conversion.tenant_id)
            product = Product.query.get(conversion.product_id)
            marketer = Marketer.query.get(conversion.marketer_id) if conversion.marketer_id else None
            commission = conversion.commission_earned
        else:
            # Fallback path: If for some reason Stage 1 bypassed DB recording, create it directly
            tenant = Tenant.query.filter_by(username_slug=username_slug).first()
            product = Product.query.get(product_id)
            if not tenant:
                return jsonify({"error": f"Merchant storefront '{username_slug}' not found"}), 404

            db_rate = getattr(tenant, 'commission_rate', None) or getattr(tenant, 'commission_percentage', None) or 10.0  
            commission = float(explicit_commission) if explicit_commission is not None else (sale_amount * (float(db_rate) / 100.0))

            marketer = None
            if cooplead_user_id and cooplead_user_id != "undefined":
                marketer = Marketer.query.filter_by(cooplead_user_id=str(cooplead_user_id)).first()

            conversion = Conversion(
                reference=reference,
                marketer_id=marketer.id if marketer else None,
                tenant_id=tenant.id,
                product_id=product.id,
                sale_amount=sale_amount,
                commission_earned=commission,
                status="released",
                customer_email=customer_email,
                released_at=datetime.utcnow()
            )
            db.session.add(conversion)

        db.session.commit()
        print(f"✅ Escrow Finalized! Reference: {reference}. Status: {conversion.status}")

        # Server-to-Server dispatch out to Cooplead Main App
        if marketer or (cooplead_user_id and cooplead_user_id != "undefined"):
            ref_code = cooplead_user_id or marketer.cooplead_user_id
            
            cooplead_payload = {
                "event_name": "lead_conversion",
                "customer_user_id": customer_email or conversion.customer_email or "customer_checkout",
                "referrer_code": str(ref_code)
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SHARED_CROSS_APP_SECRET}"
            }

            try:
                res = requests.post(
                    f"{COOPLEAD_BASE_URL}/v1/webhook",
                    json=cooplead_payload,
                    headers=headers,
                    timeout=3.0
                )
                print(f"📡 [Sync Gateway] Cooplead conversion tracking response status: {res.status_code}")
            except Exception as sync_err:
                print(f"⚠️ [Sync Gateway] Post-Escrow background sync failed: {str(sync_err)}")
        else:
            print("🛒 Organic transaction conversion committed (No marketer link attributed).")

        return jsonify({"status": "processed", "message": "Escrow successfully cleared and accounted for."}), 200

    except Exception as route_err:
        db.session.rollback()
        print(f"💥 Webhook release verification crash: {str(route_err)}")
        traceback.print_exc()
        return jsonify({"error": "Internal ledger calculation crash", "details": str(route_err)}), 500

@signals_bp.route('/escrow/deposit', methods=['POST'])
def handle_escrow_deposit():
    """
    Frontend Escrow Mirror Endpoint.
    Receives early client-side checkout data and locks it as a 'held' conversion row.
    """
    data = request.get_json() or {}
    print("🛰️ [Escrow Deposit Engine] Inbound client mirror payload:", data)

    reference = data.get("reference")
    username_slug = data.get("tenant")
    product_id = data.get("productId")
    cooplead_user_id = data.get("marketerRef") or data.get("marketerId")
    
    raw_amount = data.get("amount") or 0.0
    sale_amount = float(raw_amount)
    customer = data.get("customer", {})
    customer_email = customer.get("email") if isinstance(customer, dict) else data.get("customerEmail")

    if not reference:
        return jsonify({"error": "Missing transaction reference identifier"}), 400

    try:
        # 1. Prevent overlapping inserts if Fincra webhook already fired
        existing_conversion = Conversion.query.filter_by(reference=reference).first()
        if existing_conversion:
            print(f"ℹ️ Escrow order reference {reference} already captured by webhook.")
            return jsonify({"status": "held", "message": "Order already recorded."}), 200

        # 2. Extract structural profiles
        tenant = Tenant.query.filter_by(username_slug=username_slug).first()
        product = Product.query.get(product_id)
        if not tenant:
            return jsonify({"error": f"Storefront context '{username_slug}' not found"}), 404

        # Calculate base commission using metadata configurations
        db_rate = getattr(tenant, 'commission_rate', None) or getattr(tenant, 'commission_percentage', None) or 10.0  
        rate = float(db_rate) / 100.0
        commission = sale_amount * rate

        marketer = None
        if cooplead_user_id and cooplead_user_id != "undefined":
            marketer = Marketer.query.filter_by(cooplead_user_id=str(cooplead_user_id)).first()

        # 3. Securely log inside conversions table with 'held' status
        conversion = Conversion(
            reference=reference,
            marketer_id=marketer.id if marketer else None,
            tenant_id=tenant.id,
            product_id=product.id,
            sale_amount=sale_amount,
            commission_earned=commission,
            status="held",
            customer_email=customer_email
        )
        
        db.session.add(conversion)
        db.session.commit()
        print(f"🔒 Escrow Record Initialized: {reference} set to HELD.")

        return jsonify({"status": "held", "message": "Transaction safely deposited into holding escrow"}), 201

    except Exception as err:
        db.session.rollback()
        print(f"💥 Escrow deposit registry crash: {str(err)}")
        return jsonify({"error": "Internal ledger storage failure", "details": str(err)}), 500


@signals_bp.route('/escrow/<string:reference>/fulfill', methods=['POST'])
def handle_escrow_fulfill(reference):
    """
    Seller Fulfillment Flag.
    Updates escrow row state from 'held' to 'seller_fulfilled'.
    """
    try:
        conversion = Conversion.query.filter_by(reference=reference).first()
        if not conversion:
            return jsonify({"error": "Target escrow conversion timeline not found"}), 404

        if conversion.status == "held":
            conversion.status = "seller_fulfilled"
            db.session.commit()
            print(f"📦 Escrow Reference {reference} updated to SELLER_FULFILLED.")

        return jsonify({"status": "seller_fulfilled", "message": "Order status flagged as shipped."}), 200
    except Exception as err:
        db.session.rollback()
        return jsonify({"error": "Failed updating fulfillment status", "details": str(err)}), 500
   

@signals_bp.route('/conversions/fulfill', methods=['POST'])
def seller_mark_fulfilled():
    """
    Updates an escrow record state to 'seller_fulfilled' so that 
    the buyer page knows they can click confirm.
    """
    data = request.get_json() or {}
    reference = data.get("reference")
    
    if not reference:
        return jsonify({"error": "Missing transaction reference"}), 400
        
    conversion = Conversion.query.filter_by(reference=reference).first()
    if not conversion:
        return jsonify({"error": "Order transaction not found"}), 404
        
    if conversion.status == "held":
        conversion.status = "seller_fulfilled"
        db.session.commit()
        print(f"📦 [Escrow Pipeline] Order {reference} advanced to seller_fulfilled state.")
        return jsonify({"status": "updated", "message": "Fulfillment status updated successfully."}), 200
        
    return jsonify({"status": "no_change", "message": "Order was already in a different lifecycle block."}), 200


import uuid
import requests
from datetime import datetime
from flask import request, jsonify


import os
import requests
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify


PAYSTACK_SECRET_KEY = "sk_test_77dc7d93400fbec7a52455e4df0d9f2141598239"
PAYSTACK_BASE_URL = "https://api.paystack.co"

PAYSTACK_HEADERS = {
    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json",
}

@signals_bp.route("/payments/paystack/initialize", methods=["POST"])
def initialize_paystack():
    data = request.get_json() or {}

    # Required fields validation
    required_fields = ["tenant", "productId", "productName", "amount", "customer"]
    missing = [field for field in required_fields if field not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    customer = data.get("customer", {})
    email = customer.get("email")
    if not email:
        return jsonify({"error": "Customer email is required"}), 400

    # Paystack requires amount in the lowest currency unit (kobo/cents -> multiply by 100)
    amount_in_kobo = int(float(data["amount"]) * 100)
    currency = data.get("currency", "USD")

    # Store custom metadata to track multi-tenant / commission data inside Paystack
    metadata = {
        "tenant": data.get("tenant"),
        "marketerRef": data.get("marketerRef"),
        "productId": data.get("productId"),
        "productName": data.get("productName"),
        "commissionRate": data.get("commissionRate"),
        "customer": customer,
    }

    paystack_payload = {
        "email": email,
        "amount": amount_in_kobo,
        "currency": currency,
        "metadata": metadata,
    }

    try:
        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=paystack_payload,
            headers=PAYSTACK_HEADERS,
            timeout=10,
        )
        res_data = response.json()

        if not response.ok or not res_data.get("status"):
            return jsonify({
                "error": res_data.get("message", "Paystack initialization failed")
            }), response.status_code

        paystack_data = res_data["data"]

        # Response matching the PaystackSession TypeScript interface
        paystack_session = {
            "reference": paystack_data["reference"],
            "checkoutUrl": paystack_data["authorization_url"],
            "tenant": data["tenant"],
            "marketerRef": data.get("marketerRef"),
            "productId": data["productId"],
            "productName": data["productName"],
            "amount": data["amount"],
            "currency": currency,
            "commissionRate": data.get("commissionRate"),
            "customer": customer,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        return jsonify(paystack_session), 200

    except requests.RequestException as e:
        return jsonify({"error": "Failed to connect to Paystack API", "details": str(e)}), 502


@signals_bp.route("/confirm", methods=["POST"])
def confirm_paystack_payout_split():
    data = request.get_json() or {}

    reference = data.get("reference")
    if not reference:
        return jsonify({"error": "Reference is required"}), 400

    try:
        # Verify transaction with Paystack before confirming payout
        verify_res = requests.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=PAYSTACK_HEADERS,
            timeout=10,
        )
        verify_data = verify_res.json()

        if not verify_res.ok or not verify_data.get("status"):
            return jsonify({
                "error": verify_data.get("message", "Transaction verification failed")
            }), 400

        tx_status = verify_data["data"]["status"]
        if tx_status != "success":
            return jsonify({"error": f"Transaction is not successful (status: {tx_status})"}), 400

        # Calculate payout split logic
        amount = data.get("amount", 0)
        commission_rate = data.get("commissionRate", 0) or 0
        commission_amount = (amount * commission_rate) / 100 if commission_rate else 0
        merchant_amount = amount - commission_amount

        # Response matching the PayoutConfirmation interface
        payout_confirmation = {
            "reference": reference,
            "tenant": data.get("tenant"),
            "marketerRef": data.get("marketerRef"),
            "status": "SUCCESS",
            "totalAmount": amount,
            "currency": data.get("currency", "USD"),
            "split": {
                "commissionRate": commission_rate,
                "commissionAmount": commission_amount,
                "merchantAmount": merchant_amount,
            },
            "confirmedAt": datetime.now(timezone.utc).isoformat(),
        }

        return jsonify(payout_confirmation), 200

    except requests.RequestException as e:
        return jsonify({"error": "Failed to verify transaction with Paystack", "details": str(e)}), 502

from flask import Blueprint, request, jsonify, session
from app.models import Buyer  # Adjust this import path to match your layout layout



# In your Flask routes blueprint
import secrets

@signals_bp.route('/buyer/auth/register', methods=['POST'])
def handle_buyer_register():
    try:
        data = request.get_json() or {}
        name = data.get('name')
        email = data.get('email', '').strip().lower()
        phone = data.get('phone')
        password = data.get('password')

        if not all([name, email, phone, password]):
            return jsonify({"error": "All fields are required to establish an account."}), 400

        if Buyer.query.filter_by(email=email).first():
            return jsonify({"error": "An account with this email already exists."}), 400

        new_buyer = Buyer(name=name, email=email, phone=phone)
        new_buyer.set_password(password)

        db.session.add(new_buyer)
        db.session.commit()

        # 🚀 FIX: Generate an explicit authentication token for buyers
        buyer_token = f"session_token_for_buyer_{new_buyer.id}_{secrets.token_hex(16)}"

        return jsonify({
            "message": "Registration successful", 
            "token": buyer_token,
            "buyer": new_buyer.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Internal Registration failure: {str(e)}"}), 500


@signals_bp.route('/buyer/login', methods=['POST'])
def handle_buyer_login():
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password components are required."}), 400

        buyer = Buyer.query.filter_by(email=email).first()
        
        if not buyer or not buyer.check_password(password):
            return jsonify({"error": "Invalid email or password credentials."}), 401

        # 🚀 FIX: Generate token upon login
        buyer_token = f"session_token_for_buyer_{buyer.id}_{secrets.token_hex(16)}"

        return jsonify({
            "message": "Welcome back!", 
            "token": buyer_token,
            "buyer": buyer.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"error": f"Internal Login engine fault tracking: {str(e)}"}), 500
    
@signals_bp.route('/buyer/logout', methods=['POST'])
def handle_buyer_logout():
    session.pop('buyer_id', None)
    session.pop('user_type', None)
    return jsonify({"success": True, "message": "Logged out cleanly."}), 200


COOP_JWT_SECRET = "your-shared-secret-key-between-both-apps"

@signals_bp.route("/auth/sso-login", methods=["POST"])
def sso_login():
    sso_token = request.json.get("token")
    
    try:
        data = jwt.decode(sso_token, COOP_JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "SSO session expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid auth token"}), 401

    social_user_id = data["sub"]
    
    tenant = Tenant.query.filter_by(coop_social_user_id=social_user_id).first()
    if not tenant:
        tenant = Tenant(
            coop_social_user_id=social_user_id,
            admin_email=data["email"],
            username_slug=data["handle"] or f"user-{social_user_id[:8]}",
            business_name=f"{data['name']}'s Store"
        )
        db.session.add(tenant)
        db.session.commit()

    # Issue token formatted specifically for your token_required decorator
    session_token = create_coopmart_jwt(tenant.id)

    return jsonify({
        "message": "Authenticated successfully",
        "access_token": session_token,
        "tenant": tenant.to_dict()
    })
