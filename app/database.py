from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import configparser
import os

# Read database configuration from db_config.ini
config = configparser.ConfigParser()
# Construct the absolute path to db_config.ini relative to the project root
# Assuming the script is run from the project root, or adjust path as needed
# For now, let's assume db_config.ini is in the root directory
db_config_path = os.path.join(os.path.dirname(__file__), '..', 'db_config.ini')

if not os.path.exists(db_config_path):
    # Fallback or error handling if db_config.ini is not found
    # For demonstration, we'll use placeholders, but in real app, this should error or use defaults
    print("WARNING: db_config.ini not found. Using placeholder database configuration.")
    db_params = {
        "server": "localhost",
        "database": "PAL_DB",
        "user": "", # Empty for Windows Auth
        "password": ""
    }
else:
    config.read(db_config_path)
    db_params = {
        "server": config.get("Database", "server"),
        "database": config.get("Database", "database"),
        "user": config.get("Database", "user", fallback=""),
        "password": config.get("Database", "password", fallback="")
    }

# Construct the database URL
DATABASE_URL = ""
if db_params["user"]:
    # SQL Server Authentication
    # NOTE: Ensure you have the correct ODBC driver installed.
    # Example for SQL Server Native Client 11.0 or ODBC Driver 17 for SQL Server
    # You might need to adjust the DRIVER name based on your system.
    # Using a common driver name format.
    driver = "{ODBC Driver 17 for SQL Server}" # Or "{SQL Server Native Client 11.0}" or "{SQL Server}"
    DATABASE_URL = f"mssql+pyodbc://{db_params['user']}:{db_params['password']}@{db_params['server']}/{db_params['database']}?driver={driver}"
else:
    # Windows Authentication
    driver = "{ODBC Driver 17 for SQL Server}" # Or "{SQL Server Native Client 11.0}" or "{SQL Server}"
    DATABASE_URL = f"mssql+pyodbc://{db_params['server']}/{db_params['database']}?driver={driver}&trusted_connection=yes"

# SQLAlchemy engine and session setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Placeholder for database schema creation (if needed, though the original app seems to handle it)
# The original app has a create_table method in infrastructure/database.py.
# For FastAPI, this might be handled via Alembic migrations or a separate setup script.
# For now, we'll assume the database and tables are pre-existing or managed externally.

print(f"Database URL configured: {DATABASE_URL.split('@')[-1]}") # Print anonymized URL

