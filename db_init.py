# db_init.py
from app import app, db
from models import init_db

if __name__ == '__main__':
    with app.app_context():
        init_db(app)
    print("Database tables created successfully!")