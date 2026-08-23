from flask import render_template
from app import db
from app.errors import bp


@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html',error=error), 404


@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html',error=error), 500

from app.errors import bp
@bp.errorhandler(Exception)
def handle_exception(error):
    return render_template("errors/500.html", error=error), 500

from sqlalchemy.exc import SQLAlchemyError

@bp.errorhandler(SQLAlchemyError)
def handle_database_error(error):
    return render_template("errors/500.html",error=error), 500

