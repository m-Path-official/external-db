// MongoDB initialization script (no-op)
// This script intentionally does NOT create any collections, indexes, or documents.
// Collections and indexes should be created on demand by the GraphQL API.
// It still selects the target database to verify environment wiring and logs it.

(function () {
  try {
    var targetDbName = (process.env.MONGO_INITDB_DATABASE || 'mpath');
    // Touch the DB to ensure the variable is valid; do not create anything.
    db.getSiblingDB(targetDbName);
    print('[init] Using database (no-op init): ' + targetDbName);
    print('[init] Skipping collection and index creation by design.');
  } catch (e) {
    print('[init] Initialization error: ' + e);
  }
})();
