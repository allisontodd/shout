#!/usr/bin/env python3

#
# Parser for RF link matchmaking queries
#

import parsy

# Data classes used in parsing

class Identifier:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "Identifier(name=%s)" % self.name

class Function:
    def __init__(self, name, args):
        self.name = name
        self.args = args
    def __repr__(self):
        return "Function(name=%s, args=%s)" % (self.name, self.args)

class BinOp:
    def __init__(self, left, right, op):
        self.left = left
        self.right = right
        self.op = op
    def __repr__(self):
        return "BinOp(left=%s, right=%s, op=%s)" % (self.left, self.right, self.op)

class MapBinOp:
    def __init__(self, left, right, op):
        self.left = left
        self.right = right
        self.op = op
    def __repr__(self):
        return "MapBinOp(left=%s, right=%s, op=%s)" % (self.left, self.right, self.op)
        
class IsaExpr:
    def __init__(self, ident, expr):
        self.ident = ident
        self.expr = expr
    def __repr__(self):
        return "IsaExpr(ident=%s, expr=%s)" % (self.ident, self.expr)

class OfExpr:
    def __init__(self, count, ident):
        self.count = count
        self.ident = ident
    def __repr__(self):
        return "OfExpr(count=%d, ident=%s)" % (self.count, self.ident)

class Select:
    def __init__(self, columns, where):
        self.columns = columns
        self.where = where
    def __repr__(self):
        return "Select(columns=%s, where=%s)" % (self.columns, self.where)
        
# Parsy definitions follow

SELECT = parsy.string('SELECT') | parsy.string('select')
OF = parsy.string('OF') | parsy.string('of')
ISA = parsy.regex(r'[iI][sS]\s+[aA][nN]?')
WHERE = parsy.string('WHERE') | parsy.string('where')

space = parsy.regex(r'\s+')
oparen = parsy.regex(r'\(\s*')
cparen = parsy.regex(r'\s*\)')
comma = parsy.regex(r'\s*,\s*')
semicolon = parsy.regex(r'\s*;\s*')

intLit = parsy.regex(r'(0|[1-9][0-9]*)').map(int).desc("integer")

floatLit = parsy.regex(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?').map(float).desc("floating point number")

singleQuoteString = parsy.regex(r"'[^']*'").map(lambda s: s[1:-1])
doubleQuoteString = parsy.regex(r'"[^"]*"').map(lambda s: s[1:-1])
strLit = (singleQuoteString | doubleQuoteString).desc("string")

identifier = parsy.regex(r'[a-zA-Z][a-zA-Z0-9_]*').map(Identifier).desc("identifier (variable)")

operator = parsy.string_from('=', '<', '>', '<=', '>=')

mapoper = parsy.string_from('<->')

@parsy.generate
def function():
    fname = yield identifier
    yield oparen
    args = yield (mapping_binop | basic_expr.sep_by(comma))
    yield cparen
    return Function(fname, args)

function.desc("function call")

basic_expr = strLit | floatLit | function | identifier

isa_expr = parsy.seq(
    ident = identifier,
    _isastr = space + ISA + space,
    expr = strLit | function | identifier
).combine_dict(IsaExpr).desc("'IS A' binding")

binop_expr = parsy.seq(
    left = basic_expr,
    op = space.optional() >> operator << space.optional(),
    right = basic_expr
).combine_dict(BinOp).desc("operator expression")

of_expr = parsy.seq(
    count = intLit,
    _ofstr = space + OF + space,
    ident = identifier
).combine_dict(OfExpr).desc("'OF' quantifier")

map_expr = of_expr | function | identifier

mapping_binop = parsy.seq(
    left = map_expr,
    op = space.optional() >> mapoper << space.optional(),
    right = map_expr
).combine_dict(MapBinOp).desc("mapping expression")

where_expr = (isa_expr | binop_expr | basic_expr).sep_by(comma, min=1)

select = parsy.seq(
    _selectstr = space.optional() >> SELECT << space,
    columns = of_expr.sep_by(comma, min=1),
    _wherestr = space + WHERE + space,
    where = where_expr,
    _end = semicolon
).combine_dict(Select)
