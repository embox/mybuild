"""
PLY-based parser for Myfile grammar.
"""

__author__ = "Eldar Abusalimov"
__date__ = "2013-07-05"


import functools
import operator
import ply.yacc

from . import lex
from .linkage import BuiltinScope
from .linkage import ObjectScope
from .linkage import Stub
from .location import Fileinfo
from .location import Location

from util import cached_property
from util.compat import *


# Here go scoping-related stuff + some utils.

def to_rlist(reversed_list):
    return reversed_list[::-1]


def this_scope(p): return p.parser.scope_stack[-1]
def this_stub(p):  return p.parser.stub_stack[-1]

def this_scope_stub(p):
    return p.parser.stub_stack[len(p.parser.scope_stack)-1]

def push_scope(p, scope): p.parser.scope_stack.append(scope); return scope
def pop_scope(p):  return p.parser.scope_stack.pop()

def push_stub(p, stub):  p.parser.stub_stack.append(stub); return stub
def pop_stub(p):  return p.parser.stub_stack.pop()


# Location tracking.

def loc(p, i):
    return Location(p.parser.fileinfo, p.lineno(i), p.lexpos(i))

def wloc(p, i):
    return p[i], loc(p, i)

noloc = operator.itemgetter(0)  # obj_wloc -> obj

def nolocs(iterable_wlocs):
    return map(noloc, iterable_wlocs)


def track_loc(func):
    """
    Decorator for rule functions. Copies location from the first RHS symbol.
    """
    @functools.wraps(func)
    def decorated(p):
        # XXX accessing PLY internals
        s = p.slice
        s[0].lineno = s[1].lineno
        s[0].lexpos = s[1].lexpos

        func(p)

    return decorated


# Grammar definitions for PLY.

tokens = lex.tokens
start = 'translation_unit'


def p_translation_unit(p):
    """translation_unit : values"""
    p[0] = to_rlist(p[1])


def p_values_0(p):
    """values :
       values : value"""
    p[0] = [p[1]] if len(p) > 1 else []
def p_values_1(p):
    """values : value COMMA values"""
    l = p[0] = p[3]
    l.append(p[1])

def p_value(p):
    """value : STRING
       value : NUMBER
       value : new_object init_object
       value : array"""
    p[0] = p[1]


def p_new_object(p):
    """new_object :"""
    p[0] = push_stub(p, Stub(p.parser.linker,
                             this_scope(p), this_scope_stub(p)))

def p_init_object(p):
    """init_object : object_header
       init_object : object_header object_body
       init_object : object_body"""
    p.parser.linker.stubs.append(pop_stub(p))


def p_object_header(p):
    """object_header : qualname object_name object_args"""
    this_stub(p).init_header(type_name_wlocs=to_rlist(p[1]),
                             name_wloc=p[2],
                             kwarg_pair_wlocs=p[3])

def p_object_name(p):
    """object_name : empty
       object_name : ID"""
    p[0] = wloc(p, 1)

def p_object_args(p):
    """object_args :
       object_args : LPAREN arglist RPAREN"""
    p[0] = to_rlist(p[2]) if len(p) > 1 else []


def p_arglist_0(p):
    """arglist :
       arglist : arg"""
    p[0] = [p[1]] if len(p) > 1 else []
def p_arglist_1(p):
    """arglist : arg COMMA arglist"""
    l = p[0] = p[3]
    l.append(p[1])

def p_arg_0(p):
    """arg : ID EQUALS value"""
    p[0] = (p[1], p[3]), loc(p, 1)

def p_arg_1(p):
    """arg : value"""
    p[0] = (None, p[1]), loc(p, 1)


def p_object_body(p):
    """object_body : LBRACE new_scope docstring object_members RBRACE"""
    this_stub(p).init_body(attrs=to_rlist(p[4]), docstring=p[3])
    p.parser.linker.scopes.append(pop_scope(p))

def p_new_scope(p):
    """new_scope :"""
    push_scope(p, ObjectScope(this_scope(p)))


def p_docstring_0(p):
    """docstring : empty
       docstring : STRING
       docstring : STRING COMMA"""
    p[0] = p[1]

def p_object_members_0(p):
    """object_members :
       object_members : object_member"""
    p[0] = [p[1]] if len(p) > 1 else []
def p_object_members_1(p):
    """object_members : object_member COMMA object_members"""
    l = p[0] = p[3]
    l.append(p[1])

def p_object_member(p):
    """object_member : string_or_qualname COLON value"""
    p[0] = (p[1], p[3])


def p_array(p):
    """array : LBRACKET values RBRACKET"""
    p[0] = to_rlist(p[2])


@track_loc
def p_qualname_0(p):
    """qualname : ID"""
    p[0] = [wloc(p, 1)]

@track_loc
def p_qualname_1(p):
    """qualname : ID PERIOD qualname"""
    l = p[0] = p[3]
    l.append(wloc(p, 1))


@track_loc
def p_string_or_qualname_0(p):
    """string_or_qualname : STRING"""
    p[0] = p[1]

@track_loc
def p_string_or_qualname_1(p):
    """string_or_qualname : qualname"""
    p[0] = '.'.join(nolocs(reversed(p[1])))


def p_empty(p):
    """empty : """
    pass

def p_error(t):
    print("FUUUUUUUUUUUUUUUUUUUUUUUUUUUUU", t)


parser = ply.yacc.yacc(method='LALR', write_tables=False, debug=0)

# The main entry point.

def parse(source, linker, builtins={}, filename=None, **kwargs):
    """
    Parses the given source and returns the result.

    Args:
        source (str) - data to parse
        builtins (dict) - builtin variables
        filename (str) - file name to report in case of errors
        **kwargs are passed directly to the underlying PLY parser

    Returns:
        a tuple (ast_root, global_scope).

    Note:
        This function is NOT reentrant.
    """
    global parser

    p = parser
    parser = None  # paranoia mode on
    try:
        p.fileinfo = Fileinfo(source, filename)

        global_scope = ObjectScope(parent=BuiltinScope(builtins))

        p.scope_stack   = [global_scope]
        p.stub_stack  = [None]

        p.linker = linker

        ast_root = p.parse(source, lexer=lex.lexer, **kwargs)

        p.linker.scopes.append(global_scope)

        return (ast_root, dict(global_scope))

    finally:
        parser = p


source = '''//module Kernel,

//obj obj,
foo bar,
module foo(xxx=bar),

module Kernel(debug = False) {
    "Docstring!"

    x: xxx xname() {},

    source: "init.c",

    depends: [
        embox.arch.cpu(endian="be"){runtime: False},

        embox.driver.diag.diag_api,
    ],
    depends: embox.kernel.stack,

},


'''

if __name__ == "__main__":
    from .linkage import GlobalLinker, LocalLinker
    from .errors import MyfileError, CompoundError
    from util import singleton

    import traceback, sys, code
    from pprint import pprint

    def get_builtins():
        @singleton
        class embox(object):
            def __call__(self, *args, **kwargs):
                print self, args, kwargs
                return self
            def __getattr__(self, attr):
                return self
        class module(object):
            def __init__(self, *args, **kwargs):
                super(module, self).__init__()
                print self, args, kwargs
            def __call__(self, *args, **kwargs):
                print self, args, kwargs
                return self
        xxx = lambda: 42

        return dict(locals(), **{
                        'None':  lambda: None,
                        'True':  lambda: True,
                        'False': lambda: False,
                    })

    gl = GlobalLinker()
    ll = LocalLinker(gl)
    try:
        pprint(parse(source, linker=ll, builtins=get_builtins()))
        ll.link_local()
        gl.link_global()

    except MyfileError as e:
        e.print_error()

    except:
        tb = sys.exc_info()[2]
        traceback.print_exc()
        last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
        frame = last_frame().tb_frame
        ns = dict(frame.f_globals)
        ns.update(frame.f_locals)
        code.interact(local=ns)

