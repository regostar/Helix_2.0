from app import app, db
from models.sequence import Sequence
from models.chat_history import ChatHistory

def create_tables():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Tables created successfully!")

if __name__ == '__main__':
    create_tables() 