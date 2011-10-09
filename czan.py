#!/usr/bin/python
# -*- coding: utf-8 -*-
#import cProfile
#from os import path
import time, urlparse, re, sys
from flup.server.fcgi import WSGIServer
from jinja2 import Environment, FileSystemLoader
import pymongo
j_env = Environment(loader=FileSystemLoader('./'), trim_blocks=True)
db_conn = pymongo.Connection()
posts_coll = db_conn.kara2.posts
#txt_fields=['name', 'tripcode', 'email', 'subject', 'file', 'file_original', 'message']
conf={'www_path':'/czan', 'anonymous': '[Anon]'}

def xlink_filter(msg, def_board):
    if not msg:
        return ''
    html = "<a onmouseover=\"ppv(this, '%s',%d)\" onmouseout=\"$('#preview').remove()\" href=\"%s\"> %s </a>" #board, id, content, link
    m = msg.replace('\r<br />', '\n')
    r_other=re.compile(r'(^>>>?(/\w+)?/(\d+)/(\d+).*$)', flags=(re.MULTILINE|re.UNICODE))
    for i in r_other.findall(m):
        orig, board, thread, post = i
        if not i[1]:
            board=def_board
        else:
            board=board[1:]
        rr = html % (board, int(post), '%s/thread/%s/%d#%d' % ( conf['www_path'], board, int(thread), int(post) ), orig )
        m = m.replace(orig, rr)
    return m

j_env.filters['mkxlink'] = xlink_filter
j_env.filters['nl2br'] = lambda x: x.replace('\n', '<br />')

def search1(environ, path, start_response):
    query=urlparse.parse_qs(environ['QUERY_STRING'])
    tpl=j_env.get_template('post.html')
    q = query.get('q', ['.*wykop.*'])[0].decode('utf-8')
    postst = posts_coll.find( { 'message' : { '$regex' : q } } ).limit(100)
    sc = postst.count()
    ret=tpl.render(posts=postst, mode={'search':1, 'wrap':1}, config=conf, search={'count':sc, 'q':q} )
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [ret.encode('utf-8')]
def read_single(environ, path, start_response):
    tpl=j_env.get_template('post.html')
    try:
        r_id = int( path[2] )
        r_board = path[1] 
    except (IndexError, ValueError, TypeError):
        start_response('400 Bad Request', [('Content-Type', 'text/html')])
        return ["Invalid post ID."]
    post = posts_coll.find_one( {'id' : r_id, 'board': r_board } ) 
    if post is None:
        start_response('404 Not Found', [('Content-Type', 'text/html')])
        return ["<h1>404</h1><br> A post with this id doesn't exist."]
    #del post['file']
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [tpl.render(posts=[post], config=conf, mode={'single':1}).encode('utf-8')]

def read_thread(environ, path, start_response):
    tpl=j_env.get_template('post.html')
    try:
        board = path[1].decode('utf-8')
        t_id = int( path[2] )
    except (IndexError, ValueError, TypeError):
        start_response('400 Bad Request', [('Content-Type', 'text/html')])
        return ["Invalid thread ID."]
    OP = posts_coll.find_one( {'board' : board, 'thread':0, 'id': t_id } )
    if OP is None:
        start_response('404 Not Found', [('Content-Type', 'text/html')])
        return ["<h1>404</h1><br> A post with this id doesn't exist."]
    #del OP['file']
    replies = posts_coll.find( {'board':board, 'thread':t_id} ).sort('id',1)
    ret=tpl.render(threads=[{'OP':OP, 'replies':replies}], mode={'thread':1, 'wrap':1}, board={'name':board}, config=conf)
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [ret.encode('utf-8')]
def board(environ, path, start_response):
    tpl=j_env.get_template('post.html')
    try:
        board = path[1].decode('utf-8')
    except (IndexError, ValueError, TypeError):
        start_response('400 Bad Request', [('Content-Type', 'text/html')])
        return ["Invalid board."]
    thr = list( posts_coll.find( {'board':board, 'thread':0} ).sort('id', -1).limit(15) )
    def repgen(tl):
        for i in tl:
            rep = posts_coll.find( {'board':board, 'thread': i['id']} ).sort('id', -1).limit(3)
            yield {'OP':i, 'replies':rep}
    #dbg='||'.join(map(repr, l2))
    ret = tpl.render(b_threads=repgen(thr), mode={'board':1}, board={'name':board, 'anonymous':'Anone'}, config=conf)
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [ret.encode('utf-8')]

def myapp(environ, start_response):
    #try:
    #	request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    #except (ValueError):
    #	request_body_size = 0
    #request_body = environ['wsgi.input'].read(request_body_size)
    #post = urlparse.parse_qs(request_body)
    path = environ['SCRIPT_NAME'].split('/')[2:]
    if len(path)==0 or path[0]=='search':
        return search1(environ, path, start_response)
    elif path[0] == 'post':
        return read_single(environ, path, start_response)
    elif path[0] == 'thread':
        return read_thread(environ, path, start_response)
    elif path[0] == 'board':
        return board(environ, path, start_response)

if __name__ == '__main__':
    #print >>log, "init"
    #cProfile.run('WSGIServer(myapp).run()', '/anon/prof')
    if len(sys.argv) > 1:
        addr = (sys.argv[1], int(sys.argv[2]))
    else:
        addr = ('127.0.0.1', 9001)
    WSGIServer(myapp, bindAddress=addr).run()
