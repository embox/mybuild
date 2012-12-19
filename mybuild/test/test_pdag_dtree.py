import unittest
from unittest import TestCase

from itertools import izip_longest

from mybuild.dtree import *
from mybuild.pdag import *


class NamedAtom(Atom):
    def __init__(self, name):
        super(NamedAtom, self).__init__()
        self.name = name
    def __str__(self):
        return self.name

class NamedAtomWithCost(NamedAtom):
    def __init__(self, name, cost=0):
        super(NamedAtomWithCost, self).__init__(name)
        self.cost = cost
    def __str__(self):
        return '%s(%s)' % (super(NamedAtomWithCost, self).__str__(), self.cost)

class PdagDtreeTestCase(TestCase):

    @classmethod
    def atoms(cls, names, costs=()):
        return [NamedAtomWithCost(name or '', cost) if cost is not None else
                NamedAtom(name) for name, cost in izip_longest(names, costs)]

    def test_1(self):
        A,B,C,D = atoms = self.atoms('ABCD')

        # (A|B) & (C|D) & (B|~C) & ~B
        pnode = And(Or(A,B), Or(C,D), Or(B, Not(C)), Not(B))
        solution = Dtree(Pdag(*atoms)).solve({pnode:True})

        self.assertIs(True,  solution[pnode])
        self.assertIs(True,  solution[A])
        self.assertIs(False, solution[B])
        self.assertIs(False, solution[C])
        self.assertIs(True,  solution[D])

    def test_2(self):
        A,B = atoms = self.atoms('AB')

        # (A|B) & (~A|B) & (A|~B)
        pnode = And(Or(A,B), Or(Not(A), B), Or(A, Not(B)))
        solution = Dtree(Pdag(*atoms)).solve({pnode:True})

        self.assertIs(True, solution[pnode])
        self.assertIs(True, solution[A])
        self.assertIs(True, solution[B])

    def test_3(self):
        A, = atoms = self.atoms('A')

        # A & ~A
        pnode = And(A, Not(A))

        with self.assertRaises(PdagContextError):
            Dtree(Pdag(*atoms)).solve({pnode:True})

    def test_4(self):
        A,B = atoms = self.atoms('AB')

        # (A|B) & (~A | A&~A)
        pnode = And(Or(A, B), Or(Not(A), And(A, Not(A))))
        solution = Dtree(Pdag(*atoms)).solve({pnode:True})

        self.assertIs(False, solution[A])
        self.assertIs(True,  solution[B])

    def test_5(self):
        A,B = atoms = self.atoms('AB')

        # (~A + A&B + B) & (~B + ~B&A)
        pnode = And(Or(Not(A), And(A,B), B), Or(Not(B), And(A, Not(B))))
        solution = Dtree(Pdag(*atoms)).solve({pnode:True})

        self.assertIs(False, solution[A])
        self.assertIs(False, solution[B])

    def test_6(self):
        A,B,C = atoms = self.atoms('ABC')
        nA,nB,nC = map(Not, (A,B,C))

        # (A+B+C)&(~A+B+C)&(A+~B+C)&(A+B+~C)&(~A+~B+C)&(A+~B+~C)&(~A+B+~C)
        pnode = And(
            Or( A, B, C),
            Or(nA, B, C),
            Or( A,nB, C),
            Or( A, B,nC),
            Or( A,nB,nC),
            Or(nA, B,nC),
            Or(nA,nB, C),
        )
        solution = Dtree(Pdag(*atoms)).solve({pnode:True})

        self.assertIs(True, solution[A])
        self.assertIs(True, solution[B])
        self.assertIs(True, solution[C])

    @unittest.skip("Outputs too much when logging is on")
    def test_7(self):
        A,B,C,D,E = atoms = self.atoms('ABCDE')
        nA,nB,nC,nD,nE = map(Not, (A,B,C,D,E))

        # the same as test_6 but for 5 variables
        pnode = And(
            Or( A, B, C, D, E),

            Or(nA, B, C, D, E),
            Or( A,nB, C, D, E),
            Or( A, B,nC, D, E),
            Or( A, B, C,nD, E),
            Or( A, B, C, D,nE),

            Or(nA,nB, C, D, E),
            Or( A,nB,nC, D, E),
            Or( A, B,nC,nD, E),
            Or( A, B, C,nD,nE),
            Or(nA, B, C, D,nE),

            Or(nA, B,nC, D, E),
            Or( A,nB, C,nD, E),
            Or( A, B,nC, D,nE),
            Or(nA, B, C,nD, E),
            Or( A,nB, C, D,nE),

            Or( A, B,nC,nD,nE),
            Or(nA, B, C,nD,nE),
            Or(nA,nB, C, D,nE),
            Or(nA,nB,nC, D, E),
            Or( A,nB,nC,nD, E),

            Or( A,nB, C,nD,nE),
            Or(nA, B,nC, D,nE),
            Or(nA,nB, C,nD, E),
            Or( A,nB,nC, D,nE),
            Or(nA, B,nC,nD, E),

            Or( A,nB,nC,nD,nE),
            Or(nA, B,nC,nD,nE),
            Or(nA,nB, C,nD,nE),
            Or(nA,nB,nC, D,nE),
            Or(nA,nB,nC,nD, E),
        )
        solution = Dtree(Pdag(*atoms)).solve({pnode:True})

        self.assertIs(True, solution[A])
        self.assertIs(True, solution[B])
        self.assertIs(True, solution[C])
        self.assertIs(True, solution[D])
        self.assertIs(True, solution[E])

    def test_8(self):
        A,B = atoms = self.atoms('AB')

        # (A=>B) & A
        pnode = And(Implies(A,B), A)
        solution = Dtree(Pdag(*atoms)).solve({pnode:True})

        self.assertIs(True,  solution[pnode])
        self.assertIs(True,  solution[A])
        self.assertIs(True,  solution[B])

    def test_9(self):
        A,B = atoms = self.atoms('AB')

        # (A=>B) & ~B
        pnode = And(Implies(A,B), Not(B))
        solution = Dtree(Pdag(*atoms)).solve({pnode:True})

        self.assertIs(True,  solution[pnode])
        self.assertIs(False, solution[A])
        self.assertIs(False, solution[B])

    def test_10(self):
        A,B,C = atoms = atoms = self.atoms('ABC')

        pnode = AtMostOneConstraint(A,B,C)
        solution = Dtree(Pdag(*atoms)).solve({pnode:True, A:True})

        self.assertIs(False, solution[B])
        self.assertIs(False, solution[C])

    def test_11(self):
        A,B,C = atoms = atoms = self.atoms('ABC')

        pnode = AtMostOneConstraint(A,B,C)
        solution = Dtree(Pdag(*atoms)).solve({pnode:True, A:False, B:False})

        self.assertIs(True, solution[C])

    def test_12(self):
        A,B,C = atoms = atoms = self.atoms('ABC')

        pnode = AtMostOneConstraint(A,B,C)
        solution = Dtree(Pdag(*atoms)).solve({pnode:False})

        self.assertIs(False, solution[A])
        self.assertIs(False, solution[B])
        self.assertIs(False, solution[C])

    def test_13(self):
        A,B,C = atoms = atoms = self.atoms('ABC')

        pnode = AtMostOneConstraint(A,B,C)
        with self.assertRaises(PdagContextError):
            Dtree(Pdag(*atoms)).solve({A:True, B:True})


if __name__ == '__main__':

    import mybuild.logs as log

    log.zones = set([
                    'pdag',
                    'dtree',
                    ])
    log.verbose = True
    log.init_log()


    unittest.main()

