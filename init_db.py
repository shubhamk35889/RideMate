from database import create_db_engine
from schema import init_schema


engine = create_db_engine()
init_schema(engine)
print("Database initialized successfully.")
