import re

tokens_re = re.compile('(\(|\)|[\w]*[\w\!\?\*\.\']|\,|\-)(\s*)', re.UNICODE)

def tokens(s):
    """return list of pairs (word, tail)"""
    if s:
        return tokens_re.findall(s)
    else:
        return []
    

class Token:
    def __init__(self, word, ctype=None, tail=None):
        self._word = str(word)
        self._ctype = ctype
        self._tail = tail
        self._next = self._prev = self._index = None
        
    def __repr__(self):
        return str((self.word(), self.ctype()))
        return '<Token %s - %s>' % (self.word(), self.ctype())
    def __next__(self):
        return self._next 
    def prev(self):
        return self._prev
    def index(self):
        return self._index
    def word(self):
        return self._word
    def tail(self):
        return self._tail or ''
    def ctype(self):
        return self._ctype
    def __eq__(self, other):
        if isinstance(other, Token):
            return self._word == other._word and self._ctype == other._ctype
        elif type(other) == type((1,)):
            return self._word == other[0] and self._ctype == other[1]
        
class TokenDict(list):
    def keys(self):
        return [x.word() for x in self]
    def types(self):
        return set(x.ctype() for x in self)
    def append(self, token):
        
        if not isinstance(token, Token):
            raise
        if len(self) > 0:
            token._prev = self[-1]
            token._prev._next = token
        token._index = len(self)
        list.append(self, token)
    
    def __setitem__(self, idx, token):
        token._index = idx
        if idx > 0:
            token._prev = self[idx-1]
            token._prev._next = token 
        if idx < len(self) -1:
            token._next = self[idx + 1]
            token._next._prev = token
            
        list.__setitem__(self, idx, token)
    
    def serialize(self):
        result = ''
        for token in self:
            result += token.word() + token.tail()
        return result