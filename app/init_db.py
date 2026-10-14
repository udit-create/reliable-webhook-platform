
from app.core.database import Base, engine
from app.models.webhook import Webhook
from app.models.event import Event
from app.models.delivery import Delivery

Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")
