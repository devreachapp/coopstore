from app import create_app
import os

from datetime import datetime, timezone
app = create_app()
#from app.models import User


import os

import os
import threading

import os
from app import db



if __name__ == "__main__":

    with app.app_context():
        
        '''
        target_user = User.query.filter_by(email="info.starturn@gmail.com").first()
        if target_user:
            target_user.role = "admin"
            db.session.commit()
            print("🚀 Success: info.starturn@gmail.com has been promoted to Admin!")
        '''
        '''accounts_to_delete = ["5049687126", "435651021"]

        deleted_accounts = TradingAccount.query.filter(
            TradingAccount.mt5_login.in_(accounts_to_delete)
        ).all()

        for account in deleted_accounts:
            print(f"Deleting account: {account.mt5_login}")
            db.session.delete(account)

        db.session.commit() 

        print("✅ Selected trading accounts deleted successfully...")'''

        print("--- REGISTERED FLASK ROUTES ---")
        for rule in app.url_map.iter_rules():
            print(f"Path: {rule.rule} -> Methods: {list(rule.methods)} -> Endpoint: {rule.endpoint}")
        print("--------------------------------")

      # Get port from environment variable
    app.run(debug=True,port=8000)