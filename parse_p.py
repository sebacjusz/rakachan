#!/usr/bin/python
import re
from BeautifulSoup import BeautifulSoup

def get_xlinks(p):
    s = BeautifulSoup(p)
    return s.findAll('a', attrs={'class': re.compile(r'^ref.*$')})

def xl_to_text(p, b=None):
    tmp, board, thread, post = p['class'].split('|')   # [ 'ref', <board>, <thread>, <post> ]
    if b is None or b != board:
        return '>>>/' + '/'.join( (board, thread, post) )
    else:
        return '>>/' + '/'.join( (thread,post) )

def modpost(p, fix_escapes=1):
    if not p['message']:
        return None
    if fix_escapes:
        pt= p['message'].replace('\\"', '"').replace("\\'", "'")
    else:
        pt=p['message']
    xl=get_xlinks(pt)
    xlt = [ xl_to_text(i, p['board']) for i in xl ]
    for i,j in zip(xl, xlt):
        pt=pt.replace(unicode(i), j)
    return pt
