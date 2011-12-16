#!/usr/bin/python

import urllib, pymongo, json, binascii, time
from datetime import datetime
import parse_p
db_conn = pymongo.Connection()
posts_coll = db_conn.kara2.posts
def getpjson(time, dbg=0):
    url="http://www.karachan.org/read2.php?lastupdate=%d&token=jp2gmaleniemowlaki" % time
    if dbg: print "open:", url
    rr = urllib.urlopen(url).read()
    if len(rr)<10:
        return []
    else:
        return json.loads(rr)

def getbdict(dbg=0):
    url="http://www.karachan.org/read2.php?boardy=1&token=jp2gmaleniemowlaki"
    if dbg: print "open:", url
    rr=urllib.urlopen(url).read()
    return dict([(int(i['id']),i['name']) for i in json.loads(rr)] ) #+ [(54, 'xD')])
def convert_dict(src, bdict):
    #uid = 
    ret = { 'message' : src['message'].replace('<br />', '\n').replace('\r', ''),
            'id' : int(src['id']),
            'subject' : src['subject'],
            'email' : src['email'],
            'board' : bdict[int(src['boardid'])],
            'time' : datetime.fromtimestamp(int(src['timestamp'])),
            'trip' : src['tripcode'],
            'file' : pymongo.binary.Binary(binascii.a2b_hex(src['file_md5'])) if len(src['file_md5'])>10 else None,
            'thread' : int(src['parentid']),
            'name' : src['name'] }
    return ret

def dbinsert(data):
    assert type(data) == list
    for i in data:
        i['message'] =  parse_p.modpost(i)
    return posts_coll.insert(data)

def batch_insert(lastupd):
    bt = getbdict()
    print "bd:", ', '.join(["%s:%s" % (i, bt[i]) for i in bt.keys()])
    while True:
        l = [convert_dict(i, bt) for i in getpjson(lastupd, dbg=1)]
        r = dbinsert(l)
        print "inserted %d of %d" % (len(r), len(l))
        if len(l)<100:
            break
        else:
            lastupd = int( time.mktime( max( [i['time'] for i in l] ).timetuple() ) )

if __name__ == '__main__':
    import sys
    if len(sys.argv)>1:
        batch_insert(int(sys.argv[1]))
    else:
        t=int( time.mktime(posts_coll.find({'from_ca' : {'$ne' : 1}}, {'time':1}).sort('time',-1).limit(1)[0]['time'].timetuple() ))
        batch_insert(t)
