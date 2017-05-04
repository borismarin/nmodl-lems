from tx_nmodl.expr_compiler import ExprCompiler
from textx.model import parent_of_type, children_of_type

from sublems import L


class Lems(ExprCompiler):

    def __init__(self):
        super().__init__()
        self.L = L()

    def block(self, b):
        if (parent_of_type('FuncDef', b) or children_of_type('FuncCall', b)):
            return
        self.process_block(b)

    def assign(self, asgn):
        var = asgn.variable
        exp = asgn.expression
        if not var:
            asgn.lems = exp.lems
        asgn.visited = False

    def ifstmt(self, ifs):
        pass

    def primed(self, p):
        var = p.variable
        expression = p.expression
        self.L.dxdt(var, expression.lems)

    def mangle_name(self, root, pars, suff=None):
        par_ph = ['{' + p.name + '}' for p in pars]
        s = '__{}'.format(suff) if suff else ''
        return '{}_{}'.format(root, '_'.join(par_ph)) + s

    def varref(self, var):
        ivar = var.var
        if(self.is_txtype(ivar, 'FuncPar')):
            lems = '{{{}}}'.format(ivar.name)
        elif(self.is_txtype(ivar, 'FuncDef')):
            lems = self.mangle_name(ivar.name, ivar.pars)
        elif(self.is_txtype(ivar, 'Local')):
            parent = parent_of_type('FuncDef', ivar)
            lems = self.mangle_name(parent.name, parent.pars, ivar.name)
        else:
            lems = ivar.name
        var.lems = lems

    def process_block(self, root, context={}):
        def inner_asgns(x):
            return (a for a in children_of_type('Assignment', x)
                    if a.variable)
        for ifst in children_of_type('IfStatement', root):
            # handling true/false assignments for the same var
            for t, f in zip(inner_asgns(ifst.true_blk),
                            inner_asgns(ifst.false_blk)):
                if t.variable.var == f.variable.var:
                    self.L.cdv(t.variable.lems.format(**context),
                               ifst.cond.lems.format(**context),
                               t.expression.lems.format(**context),
                               f.expression.lems.format(**context))
                    t.visited = True
                    f.visited = True
        for asgn in inner_asgns(root):
            if not asgn.visited:
                self.L.dv(asgn.variable.lems.format(**context),
                          asgn.expression.lems.format(**context))
                asgn.visited = True

    #  function def related methods

    def funcdef(self, f):
        pass

    def locals(self, loc):
        pass

    def local(self, loc):
        parent = parent_of_type('FuncDef', loc)
        locname = self.mangle_name(parent.name, parent.pars, loc.name)
        loc.lems = locname

    def funcpar(self, fp):
        fp.lems = fp.name

    def funccall(self, fc):
        args = [a.lems for a in fc.args]
        if fc.func.builtin:
            fun = fc.func.builtin
            lems = '{}({})'.format(fun, ', '.join(args))
        else:
            fun = fc.func.user
            arg_val = dict(zip([p.name for p in fun.pars], args))
            if fun.is_function:
                lems = '{}_{}'.format(fun.name, '_'.join(args))
            elif fun.is_procedure:
                lems = ''  # only interested in side effects handled below
            self.process_block(fun, arg_val)
        fc.lems = lems

    # methods below pertain to nodes handled by direct string generation

    def negation(self, neg):
        s = neg.sign.lems if neg.sign else ''
        v = neg.primary.lems
        neg.lems = s + v

    def paren(self, par):
        par.lems = '(' + par.ex.lems + ')'

    def binop(self, node):
        ops = [n.lems for n in node.op[1:]]
        l = node.op[0].lems
        node.lems = l + ''.join(ops)

    def addition(self, add):
        self.binop(add)

    def multiplication(self, mul):
        self.binop(mul)

    def exponentiation(self, exp):
        self.binop(exp)

    def num(self, num):
        num.lems = num.num

    def op(self, op):
        op.lems = ' ' + self.L.ops.get(op.o, op.o) + ' '

    def pm(self, pm):
        self.op(pm)

    def md(self, md):
        self.op(md)

    def exp(self, exp):
        self.op(exp)

    def relational(self, l):
        self.binop(l)

    def logicalcon(self, l):
        self.binop(l)

    def logcon(self, l):
        self.op(l)

    def relop(self, r):
        self.op(r)

    def compile(self, mod):
        self.mm.model_from_str(mod)
        return self.L.render()
