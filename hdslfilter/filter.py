
import sys
import re
import string
import copy

import tokenize
import debug
import errors
import parse

class RegexCache(object):
	"""This is used in Expressions whenever the regex match operator is used
	(=~). Expressions on this operator are compiled to the python code
	"RC.match(<string>,<expr>)". So, when evaluating the compiled code there
	must be one of these objects present in the namespace and named 'RC'."""

	def __init__(self):
		self._cache = {}
	
	def match(self, string, regex):
		if string is None or string==None:
			return False
		
		# TODO: maybe make ints or other stuff here an Eval error?
		string = str(string)
		
		if not self._cache.has_key(regex):
			self._cache[regex] = re.compile(regex)
		
		if self._cache[regex].search(string) is None:
			return False
		else:
			return True

class EvalError(Exception):

	"""This is the root of all Exceptions that may be thrown while
	attempting to evaluate a filter expression that arise for user-caused
	reasons."""

class SymbolExpansionError(EvalError): 
	"""Raise when a symbol is used in an expression but is not defined in
	the namespace that something wants to evaluate it against."""
	
	def __init__(self, symbol, exception):
		self._symbol = symbol
		self._exception = exception

	def __str__(self):
	 	return 'Error expanding symbol "%s": %s' % (self._symbol, str(self._exception))

class SymbolExpansionTypeError(EvalError):
	"""Raised when a value for a symbol is successfully found, but it is not
	of a type usable in a filter expression."""
	
	def __init__(self, fe, obj, symbol, value):
		self.fe = fe
		self.obj = obj
		self.symbol = symbol
		self.value = value
	
	def __str__(self):
		return '%(fe)s got a value (%(value)s) of an invalid type (%(type)s) while attempting to expand symbol %(symbol)s against object %(obj)s' % {
			'fe': str(self.fe), 
			'value': repr(self.value),
			'type': repr(type(self.value)),
			'symbol': self.symbol,
			'obj': repr(self.obj) }

# what can happen while attempting to evaluate a filter against a syslog message:
# - exception thrown while doing the actual python eval: this is a bug, bubble
#   it all the way up
# - KeyError while doing eval to find value for a symbol: filter is using a
#   symbol that doesn't exist in the current message. probably harmless.
#   substitute None in and ignore. debug log it.
# - non-KeyError while doing eval to find value for a symbol: probably from
#   something non-dict-like in the log message object. The user could be
#   mistakenly using something in the FE that wasn't meant to be used in the
#   FE. Log it and fail to evaluate. What to do on eval failure depends on
#   the application. IE, If we're filtering something OUT, allow the message
#   in. Fail safe. raise SymbolExpansionError.
# - invalid symbol type after obtaining value for a symbol: probably the user
#   trying to use something in a FE that can't be. Same error handling procedure
#   as above.

class FilterExpression(object):
	def __init__(self, parse_tree, debug_logger = debug.NullDebugLogger()):
		"""Constructs a new FilterExrpression given its parse tree (which is
		a hdsyslogd.filter.parse.Expression object representing the tree
		root). You probably want to use the from_string or from_token_list
		contructors to build a FilterExpression, not this directly."""
		
		if not issubclass(parse_tree.__class__, parse.Expression):
			raise TypeError('parse.Expression object required for parse_tree argument, got %s', parse_tree.__class__)
		self._parse_tree = parse_tree
		self._logger = debug_logger

		# origin is a string that can be set by the using code that
		# describes where this filter was defined in user-friendly terms
		# (ie, "/etc/hdsyslogd.conf:12"). It can be used in errors messages.
		self.origin = None

		# _src_code contains a string representation of the python source
		# code for this expression. _obj_code is that compiled.
		self._src_code = parse_tree.compile()
		self._logger.debug('_src_code=%s' % repr(self._src_code))
		self._src_code = self._src_code.strip()
		self._obj_code = compile(self._src_code, '<string>', 'eval')
		
		# This thing performs regex matching, caching regexes as they are used.
		self._rc = RegexCache()
		
		# This is what is returned by __repr__. It is altered by the alternate
		# constructors from_string and from_token_list
		self.repr = '%s.%s(%s)' % (
			self.__class__.__module__, 
			self.__class__.__name__, 
			repr(parse_tree))
		
		# _symbol_list is an array containing strings that are all the symbols
		# used in the filter expression.
		self._symbol_list = self._parse_tree.find_symbols()
		self._logger.debug('_symbol_list=%s' % repr(self._symbol_list))
		
		# the _symbol2pydt maps symbols as they appear in the filter
		# expression (ie, "aa.bb.cc") to python dictionary traversal code
		# (ie, "['aa']['bb']['cc']"). Keys are the symbols in the filter
		# expression, values are python code (strings).
		self._symbol2pydt = {}
		for symbol in  self._symbol_list:
			self._symbol2pydt[symbol] = '['+ string.join([repr(s) for s in symbol.split('.')],'][') +']'
		self._logger.debug('_symbol2pydt=%s' % repr(self._symbol2pydt))
	
		# this filter expression's original source code, if available
		self.filterSource = None
	
	def py_src_code(self):
		"""Return the python source code for this filter expression."""
		return self._src_code

	def token_list(self):
		"""Return the list of source tokens comprising this filter expression."""
		return self._token_list
	
	def parse_tree(self):
		"""return the root of the parse tree for this expression."""
		return self._parse_tree
	
	@classmethod
	def from_token_list(cls, tokens, debug_logger = debug.NullDebugLogger()):
		
		"""Return a FilterExpression built from the given array of
		hdsyslogd.filter.tokenize.Token objects. This is used when we are
		building filters from a sieve file (which is a bunch of filter
		expressions separated by semicolons. Parsing of that is done
		elsewhere. This may throw a hdsyslogd.filter.errors.UserError
		exception if there are any problems parsing the filter."""
		
		if len(tokens)==0:
			raise errors.NullExpressionError()

		debug_logger.debug("begin from_token_list() constructor for %s" % repr(tokens))
		debug_logger.debug("token list: %s" % [token.data for token in tokens])
		tokens_orig = copy.copy(tokens)
		parse_tree = parse.parse(tokens, debug_logger)
		fe_repr = '%s.%s.from_token_list(%s)' % (cls.__module__, cls.__name__, repr(tokens))
		fe = cls(parse_tree,debug_logger = debug_logger)
		fe.repr = fe_repr
		fe._token_list = tokens_orig
		return fe

	@classmethod
	def from_string(cls, string, debug_logger = debug.NullDebugLogger()):
		"""Return a FilterExpression given a string representation of its
		filter expression source code (ie, "snort.src_addr='1.2.3.4'"). This
		may throw a hdsyslogd.filter.errors.UserError exception if there are
		any problems parsing the filter."""
		debug_logger.debug("begin from_string() constructor for %s" % repr(string))
		tzr = tokenize.Tokenizer()
		filterSource = string
		tokens = []
		fe_repr = '%s.%s.from_string(%s)' % (cls.__module__, cls.__name__, repr(string))
		while string:
			(rest, token) = tzr.get_token(string)
			debug_logger.debug("got token: %s" % repr(token))
			string = rest
			if token is not None:
				tokens.append(token)
		fe = cls.from_token_list(tokens, debug_logger)
		fe.repr = fe_repr
		fe.filterSource = filterSource
		return fe

	# TODO: make this raise one exception for KeyErrors and something more
	# severe for other errors.
	def _expand_symbol(self, symbol, obj): 
	
		"""given a filter expression symbol (ie, "snort.src_addr") and a
		python object that is or acts like a dict, try to expand the symbol
		and get a value against the given python object. IE, given
		"snort.src_addr" as the symbol and {'snort': {'src_addr'}} as obj,
		this will attempt to evaluate obj['snort']['src_addr'] and return
		it."""
		
		if symbol not in self._symbol_list:
			raise ValueError("given symbol is not used in this expression")
		assert self._symbol2pydt.has_key(symbol)
		
		try:
			value = eval('obj%s' % self._symbol2pydt[symbol])
		except KeyError, ke:
			self._logger.debug('%s: KeyError %s while searching for %s in %s. Assuming None.' % (self.origin, ke, symbol, repr(obj)))
			return None
		
		if type(value) not in (type(0), type(0.0), type(''), type(None), type(True), type(0L) ):
			raise SymbolExpansionTypeError(self, obj, symbol, value)
		
		return value
	
	def _get_symdict(self, dict):
		"""Given a python dictionary (or something that acts like one),
		attempt to find values for all symbols in this filter expression in
		the given dict or dict-like object. For example, if this
		FilterExpression represents and expression that uses symbols
		"snort.src_addr" and "customer", this will attempt to evaluate
		dict['snort']['src_addr'] and dict['customer'] to find values for
		thos symbols (it calls expand_symbol to do this). It will return
		all values as a dictionary with filter expression symbols as keys
		(ie 'snort.src_addr') and the values as the dict values."""

		values = {}
		for symbol in self._symbol_list:
			values[symbol] = self._expand_symbol(symbol, dict)
		
		return values
	
	def match(self, logMessage): 
	
		"""Evaluate this expression against this log message in the standard
		manner. Returns True or False. May throw EvalError if there's a
		(possibly) user-caused problem. May throw any other exception if
		there's something worse wrong."""

		if not issubclass(logMessage.__class__, dict):
			raise TypeError('dict or dict subclass required for value to match against')

		namespace = {
			'SYMBOL': self._get_symdict(logMessage),
			'RC': self._rc }
		
		res = eval(self._obj_code, namespace)
		return res

	def matchLog(self, log):

		"""Evaluate this expression against an hdsyslog.log.Log object in
		the standard manner. Returns True or False. May throw EvalError if
		there's a (possibly) user-caused problem. May throw any other
		exception if there's something worse wrong."""
		
		return self.match(log.toDict())
	
	def __str__(self):
		if self.origin is not None:
			return 'filter expression from %s' % self.origin
		else:
			return 'filter expression from unknown origin'
	
	def __repr__(self):
		return self.repr
	
class Sieve(object):
	"""A Sieve is comprised of zero or more FilterExpressions. LogMessages
	can be passed through it to see if they pass all filters or not."""
	def __init__(self, filter_expressions = []):
		for fe in filter_expressions:
			if not issubclass(FilterExpression, fe.__class__):
				raise TypeError('filter_expressions must be a list composed only of FilterExpressions')
		self._filter_exprs = filter_expressions
		self._onexc = True

	def from_string(cls, s):
		return cls.from_str(s)
	from_string = classmethod(from_string)

	def from_str(cls, s):
		"""Return s new Sieve based on expression source code in the string s."""
		tokens = tokenize.tokenize(s)
		filter_exprs = []
		for expr_tokens in tokens:
			#print expr_tokens
			fe = FilterExpression.from_token_list(expr_tokens)
			filter_exprs.append(fe)
		return cls(filter_exprs)
	from_str = classmethod(from_str)
	
	def from_file(cls, path):
		"""Return s new Sieve based on expression source code in the string s."""
		src = file(path).read()

		token_sets = tokenize.tokenize(src)
		filter_exprs = []
		for tokens in token_sets:
			start_line = tokens[0].lineno
			end_line = tokens[-1].lineno
			fe = FilterExpression.from_token_list(tokens)
			fe.origin = 'file %s lines %d-%d' % (path, start_line, end_line)
			filter_exprs.append(fe)
		sieve = Sieve(filter_exprs)
		sieve.src_file = path
		return sieve
	from_file = classmethod(from_file)
	
	def match(self, d):
		"""Returns True if dict object matches a FilterExpression or False
		if it matches None. The FilterExpressions are tested in order and
		evaluation is stopped upon the first match."""

		for fe in self._filter_exprs:
			rv = fe.match(d)
			if rv==True:	
				return True
		return False

	def match_trace(self, d):
		"""Returns True if dict object matches a FilterExpression or False
		if it matches None. The FilterExpressions are tested in order and
		evaluation is stopped upon the first match."""

		for fe in self._filter_exprs:
			rv = fe.match(d)
			if rv==True:	
				return (True,fe)
		return (False,None)

	def test_message(self, log_message):
		"""Returns True if log_message matches a FilterExpression or False
		if it matches None. The FilterExpressions are tested in order and
		evaluation is stopped upon the first match."""

		for fe in self._filter_exprs:
			rv = fe.match_log(log_message)
			if rv==True:	
				return True
		return False
