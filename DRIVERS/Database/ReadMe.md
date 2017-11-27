mongoDB.py contains classes for accessing data and logs in the Mongo database.

Initialize a MongoClient to create a connection to the MongoDB. This connection has built in pooling and so can be used to connect to multiple databases.

There are three classes for accessing databases, DatabaseMaster, DatabaseReadWrite, and DatabaseRead. The "master" class enforces the database settings as given in the initialization kwargs and ensures that the record and log have the correct indexes. The "read and write" class is used to form a read and write connection to a database, without needing to specify the database configuration. The "read only" class is used to form a read only connection to a database. The methods in this class cannot change values in the database. Only one script needs to call the "master" all others can use the "read and write" or "read only".

Also included is a handler for use with the built-in "logging" python library. An example is given at the end of the document.

Each database is structured so that it contains both a rolling buffer and a permanent collection to store data records, as well as permanent and rolling buffers to store log entries. With their faster read and write access and limited size scripts should primarily use the buffers to write and read to disk. The buffers automatically overwrite the oldest entries when full. Data or logs from important events should be transfered from the buffer to permanent storage on demand.
