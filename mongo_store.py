"""MongoDB connection, collection setup, and one-time SQLite data import."""

import os
import sqlite3
import tempfile
import threading
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, ReplaceOne, ReturnDocument
from pymongo.errors import DuplicateKeyError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

COLLECTION_KEYS = {
    "users": "user_id",
    "companies": "company_id",
    "job_seekers": "seeker_id",
    "recruiters": "recruiter_id",
    "subscription_plans": "plan_id",
    "recruiter_subscriptions": "subscription_id",
    "payments": "payment_id",
    "invoices": "invoice_id",
    "jobs": "job_id",
    "skills": "skill_id",
    "job_skills": None,
    "seeker_skills": None,
    "resumes": "resume_id",
    "applications": "application_id",
    "application_tracking": "tracking_id",
    "saved_jobs": "saved_id",
    "notifications": "notification_id",
}

_client = None
_database = None
_lock = threading.Lock()


def _configure_indexes(database):
    database.users.create_index([("email", ASCENDING)], unique=True)
    database.companies.create_index([("company_name", ASCENDING)], unique=True)
    database.subscription_plans.create_index([("plan_name", ASCENDING)], unique=True)
    database.skills.create_index([("skill_name", ASCENDING)], unique=True)
    database.applications.create_index(
        [("seeker_id", ASCENDING), ("job_id", ASCENDING)], unique=True
    )
    database.saved_jobs.create_index(
        [("seeker_id", ASCENDING), ("job_id", ASCENDING)], unique=True
    )
    database.job_skills.create_index(
        [("job_id", ASCENDING), ("skill_id", ASCENDING)], unique=True
    )
    database.seeker_skills.create_index(
        [("seeker_id", ASCENDING), ("skill_id", ASCENDING)], unique=True
    )


def _sqlite_source():
    source = BASE_DIR / "job_portal.db"
    if source.is_file():
        return _import_sqlite_file(source)

    with tempfile.TemporaryDirectory(prefix="job-portal-seed-") as temp_dir:
        seed_database = Path(temp_dir) / "job_portal.db"
        import setup_database

        original_path = setup_database.DB_PATH
        setup_database.DB_PATH = str(seed_database)
        try:
            setup_database.init_database()
        finally:
            setup_database.DB_PATH = original_path

        return _import_sqlite_file(seed_database)


def _import_sqlite_file(source_path):
    connection = sqlite3.connect(str(source_path))
    connection.row_factory = sqlite3.Row
    try:
        tables = [
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        ]
        return {
            table: [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]
            for table in tables
            if table in COLLECTION_KEYS
        }
    finally:
        connection.close()


def _migration_filter(collection_name, document):
    key = COLLECTION_KEYS[collection_name]
    if key:
        return {key: document[key]}
    if collection_name == "job_skills":
        return {"job_id": document["job_id"], "skill_id": document["skill_id"]}
    if collection_name == "seeker_skills":
        return {"seeker_id": document["seeker_id"], "skill_id": document["skill_id"]}
    raise ValueError(f"No migration key configured for {collection_name}")


def get_database():
    """Return a configured MongoDB database, importing demo records if it is empty."""
    global _client, _database
    with _lock:
        if _database is not None:
            return _database

        uri = os.environ.get("MONGODB_URI") or "mongodb://127.0.0.1:27017"
        database_name = os.environ.get("MONGODB_DATABASE", "online_job_portal")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        database = client[database_name]
        _configure_indexes(database)

        state = database["_migration_state"].find_one({"_id": "sqlite_import"})
        if state and state.get("status") == "complete":
            _client, _database = client, database
            return database

        has_application_data = any(
            database[name].estimated_document_count()
            for name in COLLECTION_KEYS
        )
        if has_application_data:
            database["_migration_state"].replace_one(
                {"_id": "sqlite_import"},
                {"_id": "sqlite_import", "status": "complete", "source": "existing MongoDB data"},
                upsert=True,
            )
            _client, _database = client, database
            return database

        if not state:
            try:
                database["_migration_state"].insert_one(
                    {"_id": "sqlite_import", "status": "in_progress"}
                )
            except DuplicateKeyError:
                pass

        imported = _sqlite_source()
        for collection_name, records in imported.items():
            if records:
                operations = [
                    ReplaceOne(
                        _migration_filter(collection_name, record),
                        record,
                        upsert=True,
                    )
                    for record in records
                ]
                database[collection_name].bulk_write(operations, ordered=False)
                key = COLLECTION_KEYS[collection_name]
                if key:
                    maximum_id = max(record[key] for record in records)
                    database["_counters"].update_one(
                        {"_id": collection_name},
                        {"$max": {"sequence": maximum_id}},
                        upsert=True,
                    )

        database["_migration_state"].update_one(
            {"_id": "sqlite_import"}, {"$set": {"status": "complete"}}
        )
        _client, _database = client, database
        return database


def next_id(database, collection_name):
    counter = database["_counters"].find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"sequence": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return counter["sequence"]
