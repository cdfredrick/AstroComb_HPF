mongoDB.py contains classes for accessing data and logs in the Mongo database.

Initialize a MongoClient to create a connection to the MongoDB. This connection has built in pooling and so can be used to connect to multiple databases.

There are three classes for accessing databases, DatabaseMaster, DatabaseReadWrite, and DatabaseRead. The "master" class enforces the database settings as given in the initialization kwargs and ensures that the record and log have the correct indexes. The "read and write" class is used to form a read and write connection to a database, without needing to specify the database configuration. The "read only" class is used to form a read only connection to a database. The methods in this class cannot change values in the database. Only one script needs to call the "master" all others can use the "read and write" or "read only".

Also included is a handler for use with the built-in logging python library.

Each database is structured so that it contains a collection to store permanent records, a rolling buffer used for quick read and write access, and a collection to store log entries. In general, the buffer should be used for most things, with entries only transferring to the record on demand. The log is intended to be the repository of messages and statements as generated with the logging library.
