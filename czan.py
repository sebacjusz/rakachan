#!/usr/bin/python
# -*- coding: utf-8 -*-
import time, urlparse, re, sys
from flup.server.fcgi import WSGIServer
from flask import Flask, request, render_template, Markup
import pymongo

app=Flask(__name__)
app.config.from_object('config')

class DatabaseConnection(object):
    """Wraps around the low-level pymongo queries"""
    def __init__(self, db, host=None, port=None):
        self.connection = pymongo.Connection(host=host, port=port)
        self.db = self.connection[db]
        self.posts_coll=self.db.posts
        self.board_info_c=self.db.boards
    def __process_data(self, post):
        if not post:
            return post

<<<<<<< HEAD
        if not app.config.get('USE_TIME_FIELD') or not post.has_key('time'):
=======
        if not app.config['USE_TIME_FIELD'] or not post.has_key('time'):
>>>>>>> 068b25f39db00422b3c7785beef9ab37cfa63327
            post['time'] = post['_id'].generation_time
        #We need to replace None with an empty string so jinja's urlize function doesn't repr() it
        post['message']=post['message'] if post['message'] else ''
        if not post.get('raw_html'):
            return post
        else:
            post['message']=Markup(post['message'])
            return post
    def single(self, board, p_id):
        p = self.posts_coll.find_one( {'id' : p_id, 'board': board } )
        return self.__process_data(p)
    def thread(self, board, t_id):
        """returns a tuple with the first post(OP) and a list of replies"""
        OP = self.posts_coll.find_one( {'board' : board, 'thread':0, 'id': t_id } )
        if not OP:
            return None
        replies = self.posts_coll.find( {'board':board, 'thread':t_id} ).sort('id',1)
        OP=self.__process_data(OP)
        replies=map(self.__process_data, replies)
        return (OP, replies)
    def board(self, board, per_page=15, replies=3):
        """returns a generator yielding `per_page` thread tuples (see thread()) with `replies` last replies"""
        thr = self.posts_coll.find( {'board':board, 'thread':0} ).sort('id', -1).limit(per_page)
        def repgen(tl):
            for i in tl:
                r_tmp = self.posts_coll.find( {'board':board, 'thread': i['id']} ).sort('id', -1)
                repcnt = r_tmp.count()
                i['ommited']=repcnt
                yield {'OP':self.__process_data(i), 'replies':map(self.__process_data,r_tmp.limit(replies))}
        return repgen(thr)
    def search_regex(self, query, limit=100):
        """returns a tuple of first `limit` search results and a number of total posts found"""
        res = self.posts_coll.find( { 'message' : { '$regex' : query } } ).limit(limit)
        sc = res.count()
        return ( map(self.__process_data, res), sc)

dbc = DatabaseConnection(app.config['MONGO_DB'])

@app.template_filter('mkxlink')
def xlink_filter(msg, def_board):
    html = "<a onmouseover=\"ppv(this, '%s',%d)\" onmouseout=\"$('#preview').remove()\" href=\"%s\"> %s </a>" #board, id, content, link
    r_other=re.compile(r'(^>>>?(/\w+)?/(\d+)/(\d+).*)$', flags=(re.MULTILINE|re.UNICODE))
    for i in r_other.findall(msg):
        orig, board, thread, post = i
        board = board[1:] if board else def_board
        rr = html % (board, int(post), '%s/thread/%s/%d#%d' % ( app.config['WWW_PATH'], board, int(thread), int(post) ), orig )
        msg = msg.replace(orig, Markup(rr))
    return Markup(msg)

@app.template_filter()
def mk_unkfunc(msg):
    r_hl=re.compile(r'^(>\w.*)$', flags=re.MULTILINE|re.UNICODE)
    for i in r_hl.findall(msg):
        msg=msg.replace(i, Markup(u"<span class=unkfunc>%s</span>") % i)
    return msg

app.jinja_env.filters['nl2br'] = lambda x: x.replace('\n', Markup('<br />'))

@app.route('/search')
def search1():
    q=request.args.get('q')
    if q:
        r,c = dbc.search_regex(q)
        search={'count':c, 'q':q}
    else:
        r=[]
        search=None
    return render_template('post.html', posts=r, mode={'search':1}, search=search)

@app.route('/post/<p_board>/<int:p_id>')
def read_single(p_board, p_id):
    post = dbc.single(p_board, p_id)
    if not post:
        return "<h1>404</h1><br> A post with this id doesn't exist. (id %d, brd %s)" % (p_id, p_board), 404
    return render_template('post.html', posts=[post], mode={'single':1})

@app.route('/thread/<t_board>/<int:t_id>')
def read_thread(t_board, t_id):
    thr = dbc.thread(t_board, t_id)
    if not thr:
        return "<h1>404</h1><br> A thread with this id doesn't exist.", 404
    return render_template('post.html', threads=[{'OP':thr[0], 'replies':thr[1]}], mode={'thread':1})

@app.route('/board/<board>')
def board(board):
    thr_l = dbc.board(board)
    return render_template('post.html', b_threads=thr_l, mode={'board':1})

if __name__ == '__main__':
    if len(sys.argv) > 2:
        addr = (sys.argv[1], int(sys.argv[2]))
    elif len(sys.argv)>1 and sys.argv[1]=='-nb':
        addr=None
    else:
        addr = ('127.0.0.1', 9001)
    WSGIServer(app, bindAddress=addr).run()
