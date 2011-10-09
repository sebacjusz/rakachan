#!/usr/bin/python
# -*- coding: utf-8 -*-
import time, urlparse, re, sys
from flup.server.fcgi import WSGIServer
from jinja2 import Environment, FileSystemLoader
from flask import Flask, request
import pymongo
j_env = Environment(loader=FileSystemLoader('./'), trim_blocks=True)
db_conn = pymongo.Connection()
posts_coll = db_conn.kara2.posts
#txt_fields=['name', 'tripcode', 'email', 'subject', 'file', 'file_original', 'message']
conf={'www_path':'/czan', 'anonymous': '[Anon]'}

app=Flask(__name__)
app.debug=True

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

@app.route('/search')
def search1():
    tpl=j_env.get_template('post.html')
    q=request.args.get('q', '')
    if q:
        postst = posts_coll.find( { 'message' : { '$regex' : q } } ).limit(100)
        sc = postst.count()
        search={'count':sc, 'q':q}
    else:
        postst=[]
        search=None
    ret=tpl.render(posts=postst, mode={'search':1, 'wrap':1}, config=conf, search=search)
    return ret

@app.route('/post/<p_board>/<int:p_id>')
def read_single(p_board, p_id):
    tpl=j_env.get_template('post.html')
    post = posts_coll.find_one( {'id' : p_id, 'board': p_board } ) 
    if post is None:
        return "<h1>404</h1><br> A post with this id doesn't exist. (id %d, brd %s)" % (p_id, p_board), 404
    return tpl.render(posts=[post], config=conf, mode={'single':1})

@app.route('/thread/<t_board>/<int:t_id>')
def read_thread(t_board, t_id):
    tpl=j_env.get_template('post.html')
    OP = posts_coll.find_one( {'board' : t_board, 'thread':0, 'id': t_id } )
    if OP is None:
        return "<h1>404</h1><br> A thread with this id doesn't exist.", 404
    replies = posts_coll.find( {'board':t_board, 'thread':t_id} ).sort('id',1)
    ret=tpl.render(threads=[{'OP':OP, 'replies':replies}], mode={'thread':1, 'wrap':1}, board={'name':t_board}, config=conf)
    return ret

@app.route('/board/<board>')
def board(board):
    tpl=j_env.get_template('post.html')
    thr = list( posts_coll.find( {'board':board, 'thread':0} ).sort('id', -1).limit(15) )
    def repgen(tl):
        for i in tl:
            rep = posts_coll.find( {'board':board, 'thread': i['id']} ).sort('id', -1).limit(3)
            yield {'OP':i, 'replies':rep}
    ret = tpl.render(b_threads=repgen(thr), mode={'board':1}, board={'name':board, 'anonymous':'Anone'}, config=conf)
    return ret

def myapp(environ, start_response):
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
    WSGIServer(app, bindAddress=addr).run()
