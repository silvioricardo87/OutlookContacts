#!/usr/bin/env python
import sys, urllib, json
from bson.son import SON
from bson.json_util import dumps, RELAXED_JSON_OPTIONS
import pprint
from pymongo import MongoClient
from bson.objectid import ObjectId
import ast
import re

def main(uri):
  numfilters = 2
  client  = MongoClient(uri)
  #connect to database
  db = client.get_default_database()
  for i in range(numfilters):
    if i == 0:
      #by Email:
      pipeline = [
        {"$match":{"E-mail Address":{"$nin":["null","?"]},}},
        {"$group":{"_id":{"E-mail Address":"$E-mail Address"},"uniqueIds":{"$addToSet":"$_id"},"count": {"$sum": 1}}},
        {"$match":{"count": {"$gt": 1}}},
        {"$sort": SON([("count", -1), ("_id", -1)])}
      ]
    else:
      #by First AND Last Name
      pipeline = [
        {"$match":{"First Name":{"$nin":["null","?"]},"Last Name":{"$nin":["null","?"]}}},
        {"$group":{"_id":{"First Name":"$First Name", "Last Name":"$Last Name"},"uniqueIds":{"$addToSet":"$_id"},"count": {"$sum": 1}}},
        {"$match":{"count": {"$gt": 1}}},
        {"$sort": SON([("count", -1), ("_id", -1)])}
      ]
    #send data to list
    print(pipeline)
    data = list(db.cleancontacts.aggregate(pipeline))
    #db.command('aggregate', 'contacts', pipeline=pipeline, explain=True)
    #pprint.pprint(data)
    #put it in a json object
    json_string = dumps(data, json_options=RELAXED_JSON_OPTIONS)
    json_data = json.loads(json_string)
    #print(json_data)
    new_ids = []
    num_iter = 0
    error_count = 0
    num_duplicates = 0
    #iterate over json objects
    for contact in json_data:
      num_iter += 1
      ids = contact["uniqueIds"]
      #print(ids)
      ids_duplicates = []
      #iterate over id values in json object contact
      for id in ids:
        id_value = id["$oid"]
        #print(id_value)
        #send ids to an array
        ids_duplicates.append(id_value)
      #get the first object from the id array, send to json
      new_contact_string = dumps(db.cleancontacts.find_one({"_id":ObjectId(ids_duplicates[0])}), json_options=RELAXED_JSON_OPTIONS)
      new_contact = json.loads(new_contact_string)
      #pprint.pprint(new_contact)
      for id in ids_duplicates[1:]:
        num_duplicates += 1
        #get data from contacts collection, iterating by id over the array
        contact_data = db.cleancontacts.find_one({"_id":ObjectId(id)})
        #pprint.pprint(contact_data)
        contact_data.pop('_id', None)
        #get rid of id fields in json object
        if i == 0:
          #email
          post_id=db.emailduplicates.insert_one(contact_data).inserted_id
        else:
          #name
          post_id=db.nameduplicates.insert_one(contact_data).inserted_id
      new_contact.pop('_id', None)
      #pprint.pprint(new_contact)
      #delete filtered contacts
      for id in ids_duplicates:
        db.cleancontacts.delete_one({"_id":ObjectId(id)})
      #send new json object to database
      post_id=db.cleancontacts.insert_one(new_contact).inserted_id
      #print(post_id)
      new_ids.append(str(post_id))
      #db.cleancontacts.delete_one({"_id":ObjectId(post_id)})
      #print out information about post
      if num_iter % 10 == 0:
        print("Iteration " + str(num_iter) + ".")
    print("Found " + str(num_duplicates) + " total duplicate contacts, errors: " + str(error_count))

if __name__ == '__main__':
  with open('config.json') as f:
    config = json.load(f)
    #uri goes to mlab for getting the data
    uri = config["uri"]
    main(uri)
