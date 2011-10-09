#!/usr/bin/python
import sqlite3, pymongo, sys, datetime, re

m_coll=pymongo.Connection().kara2.posts
c=sqlite3.connect(sys.argv[1])
c.text_factory=str
cur=c.cursor()
mkdict = lambda p: dict( zip( ['id', 'thread', 'message', None, 'time', None, 'name'], p ) )
pl = cur.execute('select * from posts')
regexp=re.compile(r'(^>>(/\w+/)?(\d+))', flags=(re.MULTILINE|re.UNICODE))
cnt=0
while True:
    cnt+=1
    r = pl.fetchone()
    if r is None:   break
    p = mkdict(r)
    p['id']=int(p['id'])
    p['thread']=int(p['thread'])
    p['message']=p['message'].decode('utf-8', 'replace') if p['message'] else None
    p['time']=datetime.datetime.fromtimestamp(int(p['time']))
    p['name']=p['name'].decode('utf-8', 'replace') if p['name'] else None
    p['board']='b'.decode('utf-8', 'replace')
    p['from_ca']=True
    try:
        if p['message']: 
            for i in regexp.findall(p['message']):
                if i[1]:
                    p['message'].replace(i[0], u'>>/%s/%d/%d' % ( i[1], p['thread'], int(i[2]) ))
                else:
                    p['message'].replace(i[0], u'>>/%d/%d' % (p['thread'], int(i[2]) ))
    except TypeError:
        print p
    pr={}
    for k in p.keys():
        if k is not None:
            pr[k]=p[k]
    if pr['thread'] == pr['id']:
        #m_coll.update( {'id':p['id'], 'thread':p['thread'], 'board':'b'}, { '$set': {'thread':0} } )
        #p['thread']=p['id']
        pr['thread']=0
    m_coll.insert(pr)
    if cnt%2000==0:
        print '\r%f%%' % (cnt/475785.0)*100*100,
print 'done,', cnt, 'ok'

