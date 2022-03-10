#!/bin/python

from __future__ import division

from __builtin__ import False

import pymongo
from bson.json_util import dumps, loads
from pymongo import CursorType
from scapy.all import *

stars = lambda n: "*" * n

MAX_CACHE_SIZE = 4982162063
                 
                 

current_cache_size=0
estimated_cache_size = current_cache_size



server_list = []
s_lsps = defaultdict(lambda:defaultdict(lambda:None))

server_list.append(<cache1_ip>)
server_list.append(<cache2_ip>)
server_list.append(<cache3_ip>)
server_list.append(<cache4_ip>)

clientip_list = []
clientip_list.append("10.10.10.7")
clientip_list.append("10.10.10.6")
clientip_list.append("10.10.10.8")
clientip_list.append("10.10.10.9")




def cache_miss(f_path, serv_ip):
    global current_cache_size, estimated_cache_size 
    cache_insert=True
    for ip in server_list:
        try:
            client=pymongo.MongoClient(ip)
            print( "Connected successfully again!!!")
        except pymongo.errors.ConnectionFailure, e:
            print("Could not connect to MongoDB sadly: %s" % e)
        db = client.cachestatus
        table = db.cache1
        if(table.find_one({"urn": f_path})) is not None:
            cache_insert=False
            break
    if cache_insert == True:        
        for ip in clientip_list:
                if ip == serv_ip:
                    client_index = clientip_list.index(ip)
        serv_ip = server_list[client_index]    
        try:
            client=pymongo.MongoClient(serv_ip)
            print( "Connected successfully again!!!")
        except pymongo.errors.ConnectionFailure, e:
            print("Could not connect to MongoDB sadly: %s" % e)
        db = client.cachestatus
        table = db.cache1
        mpdinfo = db.mpdinfo
        print "Cache miss\n"
        evict_ids = []
        cache_size_res = table.find_one()
        print ("Cache key\n")
        print f_path
        get_mpd = mpdinfo.find_one({"urn":str(f_path)})
        if get_mpd is None:
            print "File not found\n"
        new_seg_size = get_mpd['seg_size'] 
        evict = False
        evict_seg_size = 0
        
        res = table.find_one({'$query': {}, '$orderby': {"date": -1}})
        if res is not None:
            print "Get cache_size\n"
            pipe = [{'$group': {'_id': None, 'cache_size': {'$sum': '$seg_size'}}}]
            res2 = table.aggregate(pipe)
            estimated_size = loads(dumps(res2))
            estimated_cache_size=int(estimated_size[0]['cache_size'])+ new_seg_size
            print estimated_cache_size
        else:
            estimated_cache_size+=new_seg_size
        # Perform Cache Eviction
        while evict is False:
            
            for res in table.find().sort([("date", pymongo.ASCENDING)]).limit(1):
                print "Non empty cache\n"
                if res['date'] is not None: 
                    if estimated_cache_size > MAX_CACHE_SIZE:
                        table.remove({"date": res["date"]})
                        estimated_cache_size-=res['seg_size']
                    else:
                        evict = True
            if table.find_one() is None:
                insert_cache = True
                break
        # Update New Entry to MongoDB
        if(table.find_one({"urn": f_path})) is None:
            post = {"urn": f_path, "seg_no": get_mpd['seg_no'], "qual_no": get_mpd['quality'], "seg_size": new_seg_size, "cache_size":estimated_cache_size, "hit_rate":1, "date": datetime.utcnow()}
            print "Inserting URN: %s \n New cache Size %d in cache %s"%(f_path,estimated_cache_size,str(serv_ip))
            post_id = table.insert_one(post).inserted_id
        else:
            print "Content present in Cache. Don't insert\n"
    
if __name__ == "__main__":
        
    '''
     Performing MongoDB initialization here
    
    '''    
    try:
        client=pymongo.MongoClient()
        print( "Connected successfully again!!!")
    except pymongo.errors.ConnectionFailure, e:
        print("Could not connect to MongoDB sadly: %s" % e)
    db = client.opencdn
    coll = db.cachemiss
    cursor = coll.find(cursor_type = CursorType.TAILABLE_AWAIT).max_await_time_ms (0)
    
    while cursor.alive:
        print "Tailing cursor\n"
        try:
            doc = cursor.next()
            print doc
            print('Generating a cache miss\n')
            cache_miss(str(doc["urn"]), str(doc["source_ip"]))
                #threading.Thread(target=cache_miss,args=(str(doc["urn"]), str(serv_ip))).start()
        except StopIteration:
            time.sleep(1)

