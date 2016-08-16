class UserError(Exception):
	"""Is the root of all user-caused exceptions that may be thrown while parsing
	an expression."""
	pass

class NullExpressionError(UserError):

	"""Raised when asked to compile a filter that isn't really a filter at
	all (ie, null string or all whitespace)."""

	def __str__(self):
		return 'Null expression'

class SemicolonExpressionError(UserError):

	"""Raised when a semicolon appears in an expression. Semicolons are only
	used in sieves and the sieve code should filter them out."""

	def __str__(self):
		return 'Semicolon appears in expression'

class UncompileableRegexError(UserError):
	
	"""The tokenizer will attempt to test-compile regular expressions as it
	encounters them so that invalid ones become compile-time errors. 
	Eval-time errors are harder to report and less preferable for other
	obvious reasons."""

	def __init__(self, regex, lineno, re_error):
		self._regex=regex
		self._lineno=lineno
		self._re_error=re_error
	
	def __str__(self):
		return 'Error compiling regex %s at line %d: %s' % (
			repr(self._regex),
			self._lineno,
			self._re_error )

class TokenUserError(UserError):
	"""A UserError that pertains to a specific token in the input."""
	def __init__(self, offending_token):
		self._offending_token = offending_token
	
	def error(self):
		raise NotImplementedError()
	
	def __str__(self):
		return self.error() + ' at line %d char %d' % (
			self._offending_token.lineno,
			self._offending_token.linepos )


class TokenizationError(UserError):
	"""A UserError that occurrs at tokenization time (so that we don't
	really have a specific offending token so TokenUserError can't be
	raised."""
	
	def __init__(self, data, lineno):
		"""data: the input we are attempting to get a token off the
		beginning of.
		lineno: the line number in the input that this occurs."""
		self._data = data
		self._lineno = lineno
	
	def __str__(self):
		return '%s error while tokenizing input %s... at line %d' % (
			self.error(),
			repr(self._data[0:20]),
			self._lineno )

#########################################################################

class UnclosedQuoteError(TokenizationError):
	def error(self):
		return 'Unclosed quote'

class UnclosedREError(TokenizationError):
	def error(self):
		return 'Unclosed regular expression'

class UnknownTokenError(TokenizationError):
	def error(self):
		return 'Unknown token'

class InvalidListMember(TokenUserError):
	def error(self):
		return 'Token of type %s is not a valid list member' % self._token.ttype

class InconsistentListMemberType(TokenUserError):
	def error(self):
		return 'List member is not of a type consistent with other list members'

class ExcessCloseParen(TokenUserError):
	def error(self):
		return 'Close parenthesis has no corresponding opener'

class MissingOperand(TokenUserError):
	def __init__(self, offending_token, position):
		#super(MissingOperand, self).__init__(offending_token)
		self._offending_token = offending_token
		assert position in ('left','right')
		self._position = position
	
	def error(self):
		return 'Operator is missing %s operand' % self._position

class OperatorInsteadOfOperand(TokenUserError):
	def __init__(self, offending_token, position):
		self._offending_token = offending_token
		assert position in ('left','right')
		self._position = position
	
	def error(self):
		return 'Expected an expression operand on %s side, found operator instead' % self._position

class ExcessiveOperands(TokenUserError):
	def error(self):
		return 'Too many operands for expression'		

class UnclosedParen(UserError):
	def error(self):
		return 'Statement ended with open parenthesis'

class UnexpectedEOF(UserError):
	def __str__(self):
		return 'Unexpected end of input'

#########################################################################

class SymbolTypeConflict(UserError):
	"""Raised when determining required types for symbols in the
	expression (via stypemap method). If a given symbol is expected
	to be two different types at the same time in different parts of
	the parse tree, this gets raised."""

	def __init__(self, establishing_expr, conflicting_expr):
		self._establisher = establishing_expr
		self._conflicter = conflicting_expr	
	
	def __str__(self):
		return "Symbol '%s' has conflicting expected type. Established type is %s at line %d char %d. Conflicting type is %s at line %d char %d." % (
			self._establisher.token().data,
			self._establisher.type(),
			self._establisher.token().lineno,
			self._establisher.token().linepos,
			self._conflicter.type(),
			self._conflicter.token().lineno,
			self._conflicter.token().linepos )
		

class IncompatibleOperandError(UserError):
	def __init__(self, operator, operand, position):
		#assert issubclass(operator.__class__, Operator)
		#assert issubclass(operand.__class__, Expression)
		#assert position in ('left', 'right')
		self._operator = operator
		self._operand = operand
		self._position = position
	
	def __str__(self):
		return 'Invalid %s operand of type %s for operator %s at line %d char %d' % (
			self._position, 
			self._operand.type(), 
			self._operator.token().data, 
			self._operator.token().lineno,
			self._operator.token().linepos )
		#return 'invalid operand %s for operator' % repr(operand)
