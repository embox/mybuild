class Domain(frozenset):
    def value(self):
	if len(self) == 1:
	    for v in self:
		return v
	return None
    
    def force_value(self):
	for v in sorted(self):
	    return v
	raise CutConflictException(self)

class ListDom():
    def __init__(self, it):
	self.it = tuple(it)

    def __nonzero__(self):
	return True

    def force_value(self):
	return tuple(self.it)

    def __and__(self, other):
	return other

    def __len__(self):
	return 1

    def __add__(self, other):
	self.it = self.it + tuple(other)
	return self

class IntegerDom(Domain):
    def __repr__(self):
	return '<IntegerDom: [%d-%d]' % (min(self), max(self))

    def __str__(self):
	return '<IntegerDom: [%d-%d]' % (min(self), max(self))

class ModDom(Domain):
    def __and__(self, other):
	if isinstance(other, BoolDom):
	    if True in other:
		return ModDom(self)
	    return ModDom([])
	return Domain.__and__(self, other)

class BoolDom(Domain):
    pass

