# To run this application locally:
# 1) Create and activate a virtual environment (recommended):
#    python -m pip install --upgrade pip virtualenv
#    virtualenv .venv
#    On Linux/macOS: source .venv/bin/activate
#    On Windows (PowerShell): .\.venv\Scripts\Activate.ps1
#
# 2) Install dependencies:
#    pip install fastapi strawberry-graphql uvicorn pymongo python-dotenv
#
# 3) Ensure MongoDB is running locally (default: mongodb://localhost:27017).
#    Start a local instance with: mongod
#
# 4) (Optional) Configure environment in a .env file or shell:
#    MONGO_USERNAME=...
#    MONGO_PASSWORD=...
#    MONGO_HOST=localhost:27017
#    MONGO_DB_NAME=simple_graphql_db
#
# 5) Start the API:
#    uvicorn app:app --reload
#
# 6) Open the GraphQL Playground at:
#    http://127.0.0.1:8000/graphql
#
# Notes:
# - If you don't set any env vars, the app uses mongodb://localhost:27017 and DB 'simple_graphql_db'.
# - python-dotenv is supported; place the variables above into a .env file in the project root.

from typing import List, Optional
# Compatibility patch for Python 3.10+ where ABCs moved to collections.abc
import collections
import collections.abc

# Provide shims for libraries that still import these from 'collections'
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping  # type: ignore[attr-defined]
if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping  # type: ignore[attr-defined]
if not hasattr(collections, "MutableSet"):
    collections.MutableSet = collections.abc.MutableSet  # type: ignore[attr-defined]
if not hasattr(collections, "Sequence"):
    collections.Sequence = collections.abc.Sequence  # type: ignore[attr-defined]

import strawberry
from fastapi import FastAPI, Request, HTTPException, status
from strawberry.fastapi import GraphQLRouter
from pymongo import MongoClient, ReturnDocument
from dotenv import load_dotenv
import os

# Load environment variables from .env if present (override any existing env)
# Also support hot-reloading when the .env file changes.
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
_ENV_MTIME: Optional[float] = None

def reload_env_if_changed() -> None:
    global _ENV_MTIME
    try:
        if os.path.exists(ENV_FILE):
            mtime = os.path.getmtime(ENV_FILE)
            if _ENV_MTIME is None or mtime != _ENV_MTIME:
                load_dotenv(dotenv_path=ENV_FILE, override=True)
                _ENV_MTIME = mtime
        else:
            # If file was removed after being present, clear mtime so future additions reload
            if _ENV_MTIME is not None:
                load_dotenv(dotenv_path=ENV_FILE, override=True)
                _ENV_MTIME = None
    except Exception:
        # Do not crash the app on env reload errors; ignore silently
        pass

# Initial load
reload_env_if_changed()

# --- Security: API Secret ---
# Note: Do not cache API_SECRET; always read from environment after potential reload.

# --- Database Setup ---
# Connect to MongoDB. It is highly recommended to use an environment variable
# for the connection string in a production environment.
mongo_username = os.getenv("MONGO_USERNAME")
mongo_password = os.getenv("MONGO_PASSWORD")
mongo_host = os.getenv("MONGO_HOST", "localhost:27017")
mongo_db_name = os.getenv("MONGO_DB", "m-path")
print(f"Connecting to MongoDB at {mongo_host}...")

# Construct the connection URL
if mongo_username and mongo_password:
    mongo_uri = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}/"
else:
    mongo_uri = f"mongodb://{mongo_host}/"
client = MongoClient(mongo_uri)

# Select the database and collection
db = client[mongo_db_name]
documents_collection = db.documents


def collection_for_type(doc_type: Optional[str]):
    """Resolve the MongoDB collection to operate on based on `type`.
    - If a non-empty type is provided, use a sanitized version as the collection name.
    - Fallback to the default `documents` collection.
    """
    if not doc_type:
        return documents_collection
    # Basic sanitization: allow alphanumeric and underscore; lower-case name
    safe = ''.join(ch for ch in doc_type if ch.isalnum() or ch == '_').lower()
    if not safe:
        return documents_collection
    return db[safe]


# --- GraphQL Schema Definition ---
# This is where we define the types and fields for our GraphQL API.
# It's what clients use to understand what data can be requested or modified.

# Define the Document type. This mirrors the structure of the data we'll store.
@strawberry.type
class DocumentType:
    id: strawberry.ID
    identifier: str
    type: str
    data: str


# Define the Query class. This contains fields for fetching data.
@strawberry.type
class Query:
    @strawberry.field
    def get_document(self, identifier: str, type: str) -> Optional[DocumentType]:
        """Fetches a single document by its unique identifier and type."""
        coll = collection_for_type(type)
        doc = coll.find_one({"identifier": identifier})
        if doc:
            if 'type' not in doc:
                doc['type'] = type
            # MongoDB's unique ID is an ObjectId; convert it to string and remove the raw field.
            doc['id'] = str(doc['_id'])
            doc.pop('_id', None)
            return DocumentType(**doc)
        return None

    @strawberry.field
    def list_documents(self) -> List[DocumentType]:
        """Fetches all documents from the database."""
        docs = []
        for d in documents_collection.find():
            d['id'] = str(d['_id'])
            d.pop('_id', None)
            docs.append(DocumentType(**d))
        return docs


# Define the Mutation class. This contains fields for creating, updating, or deleting data.
@strawberry.type
class Mutation:
    @strawberry.field
    def create_document(self, identifier: str, type: str, data: str) -> DocumentType:
        """Creates a new document in the database."""
        coll = collection_for_type(type)
        new_doc = {'identifier': identifier, 'type': type, 'data': data}
        result = coll.insert_one(new_doc)
        new_doc['id'] = str(result.inserted_id)
        # Ensure no raw Mongo _id leaks into the GraphQL type
        new_doc.pop('_id', None)
        return DocumentType(**new_doc)

    @strawberry.field
    def update_document(self, identifier: str, type: str, new_data: Optional[str] = None) -> Optional[DocumentType]:
        """Updates an existing document by its identifier and type."""
        coll = collection_for_type(type)
        filter_query = {"identifier": identifier}

        # Prepare the update dictionary with non-None values.
        updates = {}
        if new_data is not None:
            updates['data'] = new_data

        if updates:
            # Find and update the document, returning the modified document.
            updated_doc = coll.find_one_and_update(
                filter_query,
                {"$set": updates},
                return_document=ReturnDocument.AFTER
            )
            if updated_doc:
                if 'type' not in updated_doc:
                    updated_doc['type'] = type
                updated_doc['id'] = str(updated_doc['_id'])
                updated_doc.pop('_id', None)
                return DocumentType(**updated_doc)

        return None

    @strawberry.field
    def delete_document(self, identifier: str, type: str) -> bool:
        """Deletes a document from the database by its identifier and type."""
        coll = collection_for_type(type)
        result = coll.delete_one({"identifier": identifier})
        return result.deleted_count > 0


# --- API and GraphQL Integration ---

# Create a GraphQL schema from our Query and Mutation classes.
schema = strawberry.Schema(query=Query, mutation=Mutation)

# Create the FastAPI application.
app = FastAPI(
    title="NoSQL GraphQL API with MongoDB",
    description="A simple API for unstructured documents using MongoDB.",
    version="1.0.0"
)

# Middleware to enforce API secret on every request if configured.
@app.middleware("http")
async def verify_api_secret(request: Request, call_next):
    # Hot-reload .env if it changed
    reload_env_if_changed()
    api_secret = os.getenv("API_SECRET")
    if api_secret:  # only enforce if configured
        provided = request.headers.get("x-api-secret") or request.headers.get("X-Api-Secret")
        if provided != api_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API secret")
    response = await call_next(request)
    return response

# Create the GraphQL router, which handles all GraphQL requests.
graphql_app = GraphQLRouter(schema)

# Add the GraphQL endpoint to our FastAPI application.
app.include_router(graphql_app, prefix="/graphql")


# You can also add other standard REST endpoints if you wish.
@app.get("/")
async def root():
    return {"message": "Welcome to the NoSQL GraphQL API! Navigate to /graphql for the playground."}


if __name__ == "__main__":
    # Allow running via: python app.py
    import uvicorn
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("app:app", host=host, port=port, reload=os.getenv("UVICORN_RELOAD", "false").lower() == "true")
