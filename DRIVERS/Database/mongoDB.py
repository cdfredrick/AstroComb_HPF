# -*- coding: utf-8 -*-
"""
Created on Sun Nov 12 12:00:07 2017

@author: Connor
"""

import pymongo

class MongoClient:
    def __init__(self):
        # Connect to the MongoDB client
        self.client = pymongo.MongoClient()

class Database:
    def __init__(self, mongo_client, database, capped_collection_size=int(1e6)):
        # Get the MongoDB client
        self.client = mongo_client
        # Get the requested database
        self.database = self.client[database]
        # Get the collection
        self.collection = self.database['collection']
        # Get the capped collection
        self.capped_collection = self.database['capped_collection']
        # Check that the collection is as specified in the initialization options
        capped_collection_options = self.capped_collection.options()
        if not bool(capped_collection_options):
            # Create the collection if it does not already exist
            self.database.create_collection('capped_collection', capped=True, size=capped_collection_size)
        if (not capped_collection_options['capped']) or (capped_collection_options['size'] != capped_collection_size):
            # Convert the collection if it is not capped or if it is the wrong size
            self.database.command({'convertToCapped':'capped_collection', 'size':capped_collection_size})
