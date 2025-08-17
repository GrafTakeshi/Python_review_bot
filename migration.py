from database.manager import DatabaseManager


db = DatabaseManager()
db._check_migrations()