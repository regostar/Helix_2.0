from datetime import datetime, UTC
from .database import db

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    socket_id = db.Column(db.String(100), nullable=False)
    messages = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    @staticmethod
    def get_or_create(socket_id, session=None):
        if session is None:
            session = db.session
        chat_history = session.query(ChatHistory).filter_by(socket_id=socket_id).first()
        if not chat_history:
            chat_history = ChatHistory(socket_id=socket_id, messages=[])
            session.add(chat_history)
            session.commit()
        return chat_history 