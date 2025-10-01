// MongoDB initialization script
// This script is executed automatically by the official MongoDB Docker image
// on the first initialization of the database (when no data directory exists).
// It uses the environment variable MONGO_INITDB_DATABASE provided by the
// Docker entrypoint to select the target database.
//
// It will:
// - Select the requested database
// - Ensure the `documents` collection exists
// - Create a unique index on `identifier` in the `documents` collection
//   (our API looks up documents by `identifier` and expects it to be unique).

(function () {
  try {
    // Select target DB (defaults to 'mpath' if not provided)
    var targetDbName = (process.env.MONGO_INITDB_DATABASE || 'mpath');
    var targetDb = db.getSiblingDB(targetDbName);

    print("[init] Using database: " + targetDbName);

    // Ensure collection exists
    var collections = targetDb.getCollectionNames();
    if (collections.indexOf('documents') === -1) {
      print('[init] Creating collection: documents');
      targetDb.createCollection('documents');
    } else {
      print('[init] Collection already exists: documents');
    }

    // Create unique index on identifier
    print('[init] Creating index on documents.identifier (unique)');
    targetDb.documents.createIndex({ identifier: 1 }, { unique: true, name: 'identifier_unique' });

    print('[init] Initialization completed.');
  } catch (e) {
    print('[init] Initialization error: ' + e);
  }
})();
