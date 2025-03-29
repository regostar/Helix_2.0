from datetime import datetime, UTC
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    socket_id = db.Column(db.String(100), nullable=False)
    messages = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    @staticmethod
    def get_or_create(socket_id):
        chat_history = ChatHistory.query.filter_by(socket_id=socket_id).first()
        if not chat_history:
            chat_history = ChatHistory(socket_id=socket_id, messages=[])
            db.session.add(chat_history)
            db.session.commit()
        return chat_history 