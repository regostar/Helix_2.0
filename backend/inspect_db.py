from app import db
from models.sequence import Sequence
from models.chat_history import ChatHistory

def inspect_tables():
    """Print the structure of all tables in the database."""
    print("\nSequence Table Structure:")
    for column in Sequence.__table__.columns:
        print(f"- {column.name}: {column.type} (Primary Key: {column.primary_key}, Nullable: {column.nullable})")
    
    print("\nChatHistory Table Structure:")
    for column in ChatHistory.__table__.columns:
        print(f"- {column.name}: {column.type} (Primary Key: {column.primary_key}, Nullable: {column.nullable})")
    
    print("\nForeign Keys:")
    for fk in ChatHistory.__table__.foreign_keys:
        print(f"- {fk.parent.table.name}.{fk.parent.name} -> {fk.column.table.name}.{fk.column.name}")

if __name__ == '__main__':
    with db.app.app_context():
        inspect_tables() 