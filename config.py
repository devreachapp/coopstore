import os
from datetime import  timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))



#UPLOAD_FOLDER = 'C:/Users/DELL/Documents/My Dev Files/Co/demo'  # Must match the disk mount path

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USER_FOLDER = 'user_folder'


UPLOAD_THUMBNAIL_FOLDER = 'User_thumbnail'
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    'pool_recycle': 1800,  # Reconnect after 30 min
    'pool_timeout': 11
}

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "naso")
                                
    SQLALCHEMY_DATABASE_URI = "postgresql://coopmart_lmow_user:Cgt3INbDMqGKimqzJ3aCUNOz6L4CoLfm@dpg-da5f188u01pc73f10k50-a.oregon-postgres.render.com/coopmart_lmow"
    #SQLALCHEMY_DATABASE_URI = "postgresql://postgres:YardCore94!@localhost:5433/coop-mart"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Pagination
    POSTS_PER_PAGE = 90
    FOLLOWED_PER_PAGE = 8
    FOLLOWERS_PER_PAGE = 35

    # Mail Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')

    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))

    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'

    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'true').lower() == 'true'
    
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    FLASKY_MODERATOR = os.environ.get('FLASKY_MODERATOR')

    # Notification Emails
    FLASKER = 'theofuremomoh@outlook.com,momohofure@gmail.com,info.starturn@gmail.com,phurell1@mailto.plus'

    # Pusher Config
    PUSHER_APP_ID = os.environ.get('PUSHER_APP_ID')
    PUSHER_KEY = os.environ.get('PUSHER_KEY')
    PUSHER_SECRET = os.environ.get('PUSHER_SECRET')
    PUSHER_CLUSTER = os.environ.get('PUSHER_CLUSTER')


    # File media_files
    UPLOAD_FOLDER = UPLOAD_FOLDER
    UPLOAD_USER_FOLDER = USER_FOLDER
    UPLOAD_THUMBNAIL_FOLDER = UPLOAD_THUMBNAIL_FOLDER


    # Session Config
    SESSION_TYPE = 'filesystem'
    #SESSION_SQLALCHEMY = None  # To be assigned in create_app after db.init_app

    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    
    SESSION_KEY_PREFIX = 'session:'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'NONE'
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_REFRESH_EACH_REQUEST = True
    SQLALCHEMY_ENGINE_OPTIONS = SQLALCHEMY_ENGINE_OPTIONS
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    SESSION_REFRESH_EACH_REQUEST = True

    #rediss://red-d3itt23e5dus739dbk5g:NQp0PYWLfIN7gKgNxI5RHebLDrFAafgu@oregon-keyvalue.render.com:6379/0?ssl_cert_reqs=CERT_NONE
    #redis://red-d3itt23e5dus739dbk5g:6379/0

    CELERY_BROKER_URL = 'redis://red-d3itt23e5dus739dbk5g:6379/0'
    CELERY_RESULT_BACKEND = 'redis://red-d3itt23e5dus739dbk5g:6379/0'
    FINCRA_SECRET_KEY ='kOPENxvKLAHVlT6FR8LPe6QE6SI4tu2h'
    FINCRA_BASE_URL = 'https://sandboxapi.fincra.com' 