import re

import tokenize
import debug
import errors


##################################################################################
##################################################################################
# These functions massage lists of Tokens in various ways to prepare for further
# processing
##################################################################################
##################################################################################

def listify(tokens):
	"""Finds lists (a series of values in brackets) within the token stream and
	transforms them into TokenList objects. The returned list will contain 
	Token and TokenList objects."""

	new_list = []
	#for i in range(0,len(tokens)):
	while len(tokens)>0:
		token = tokens.pop(0)
		if token.ttype=='openbracket':
			token_list = tokenize.TokenList()
			token = tokens.pop(0)
			while token.ttype!='closebracket':
				if token.ttype == 'comma':
					pass
				else:
					token_list.add_token(token)
				token = tokens.pop(0)
			new_list.append(token_list)
		else:
			new_list.append(token)
	return new_list		



def parenthesize(tokens,root=True):
	""" takes an array of Tokens, returns an array with further arrays
	of tokens. The groupings are by parenthesis tokens in the array."""
	
	list = []

	while len(tokens)!=0:
		token = tokens.pop(0)
		if issubclass(token.__class__, tokenize.Token):
			if token.ttype=='oparen':
				list.append( parenthesize(tokens,False) )
			elif token.ttype=='cparen':
				if root:
					raise errors.ExcessCloseParen(token)
				else:
					return list
			else:
				list.append(token)
		elif issubclass(token.__class__, tokenize.TokenList):
			list.append(token)
		else:
			raise TypeError('tokens list contains something of an unknown type')
	
	if root:
		return list
	else:
		raise errors.UnclosedParen(token)

def apply_precedence_2(tokens):
	"""takes an array of Tokens, returns the array with certain higher
	precedence operations grouped into subarrays. This applies precedence
	for second level precedence operators (not)."""
	assert type(tokens) == type([])
	
	i = 0
	#for token in tokens:
	while i != len(tokens):
		token = tokens[i]

		if issubclass(token.__class__, tokenize.TokenList):
			i+=1
			continue

		if type(token) == type([]):
			tokens[ tokens.index(token) ] = apply_precedence_2(token)

		elif token.ttype == 'not':
			if tokens.index(token) == len(tokens)-1:
				raise errors.MissingOperand(token, 'right')
			
			operator = token
			right_operand = tokens[tokens.index(operator)+1]
		
			object_to_insert_before = None
			if tokens.index(operator)+2 < len(tokens):
				object_to_insert_before = tokens[tokens.index(operator)+2]
			
			tokens.remove(operator)
			tokens.remove(right_operand)
			
			if type(right_operand)==type([]):
				right_operand = apply_precedence_2(right_operand)
			
			operation = [operator, right_operand]
			
			if object_to_insert_before is not None:
				tokens.insert( tokens.index(object_to_insert_before), operation )
			else:
				tokens.append(operation)
			
		i+=1
	return tokens

def apply_precedence_1(tokens):
	"""takes an array of Tokens, returns the array with certain higher
	precedence operations grouped into subarrays. This applies precedence
	for highest precedence operators (ordinary binary operators)."""

	assert type(tokens) == type([])
	
	i = 0
	#for token in tokens:
	while i != len(tokens):
		token = tokens[i]

		if issubclass(token.__class__, tokenize.TokenList):
			i+=1
			continue

		if type(token) == type([]):
			tokens[ tokens.index(token) ] = apply_precedence_1(token)

		elif token.ttype in ('equal', 'match', 'notequal', 'stringequal', 'stringnotequal','in','notin'):
			if tokens.index(token)==0:
				raise errors.MissingOperand(token,'left')
			if tokens.index(token)==len(tokens)-1:
				raise errors.MissingOperand(token,'right')
				
			operator = token
			left_operand = tokens[tokens.index(operator)-1]
			right_operand = tokens[tokens.index(operator)+1]
			
			object_to_insert_before = None
			if tokens.index(operator)+2 < len(tokens):
				object_to_insert_before = tokens[tokens.index(operator)+2]
			
			tokens.remove(left_operand)
			tokens.remove(operator)
			tokens.remove(right_operand)
			
			operation = [left_operand, operator, right_operand]
			
			if object_to_insert_before is not None:
				tokens.insert( tokens.index(object_to_insert_before), operation )
			else:
				tokens.append(operation)
			
			i-=1
			
		i+=1
	return tokens

	
###################################################################################
###################################################################################
## Operator objects represent represent unbound operators as the parse tree is
## assembled
###################################################################################
###################################################################################


class Operator(object):
	def __init__(self, token):
		if not issubclass(tokenize.Token, token.__class__):
			raise TypeError('Token sublcass required')
		if token.ttype not in self.token_types():
			raise ValueError('%s token required, got %s' % (repr(self.token_types()), token.ttype))
		self._operator_token = token

	def token(self):
		return self._operator_token
		
	def want_left_operand(self):
		raise NotImplementedError()
	
	def want_right_operand(self):
		raise NotImplementedError()
	
	def __repr__(self):
		return '%s.%s(%s)' % (self.__module__, self.__class__.__name__, repr(self._operator_token))
	
class BinaryOperator(Operator):
	def want_left_operand(self):
		return True
	
	def want_right_operand(self):
		return True

class InOperator(BinaryOperator):
	def token_types(self):
		return ('in','notin')

class UnaryOperator(Operator):
	def want_left_operand(self):
		return False
	
	def want_right_operand(self):
		return True

class NotOperator(UnaryOperator):
	def token_types(self):
		return ('not')

class EqualOperator(BinaryOperator):
	def token_types(self):
		return ('equal','notequal')

class LogicalOperator(BinaryOperator):
	def token_types(self):
		return ('and','or')

class MatchOperator(BinaryOperator):
	def token_types(self):
		return ('match')

####################################################################################		
####################################################################################		
## Expression objects represent expressions (a parse tree). Operators and other
## Expressions can be combined to form new Expressions.
####################################################################################		
####################################################################################		

class Expression(object):
	dump_space = '    '
	def token(self):
		raise NotImplementedError("class '%s' does not define token method" % self.__class__.__name__)
	def dump(self, ilevel):
		"""Returns a string representing this expression as a parse tree."""
		raise NotImplementedError()

	def find_symbols(self):

		"""Returns an array containing strings which are all of the symbols
		used in this parse tree."""

		raise NotImplementedError()
	
class BinaryExpression(Expression):
	def dump(self, ilevel=0):
		rv = '%s%s\n' % (Expression.dump_space*ilevel, self.dump_repr())
		rv+=self._left_expression.dump(ilevel+1)
		rv+=self._right_expression.dump(ilevel+1)
		return rv

	def find_symbols(self):
		return self._left_expression.find_symbols() + self._right_expression.find_symbols()		

	def token(self):
		return self._operator.token()
	
	def __repr__(self):
		return '%s.%s(%s,%s,%s)' % (
			self.__module__,
			self.__class__.__name__,
			repr(self._operator),
			repr(self._left_expression),
			repr(self._right_expression) )

	def dump_repr(self):
		return '%s(%s, ..., ...)' % (
			self.__class__.__name__, 
			repr(self._operator) )

	def compile(self):
		return '(%s %s %s)' % (
			self._left_expression.compile(), 
			self.token().data,
			self._right_expression.compile() )

class MatchExpression(BinaryExpression):
	def __init__(self, operator, left_expression, right_expression):
		if not issubclass(operator.__class__, MatchOperator):
			raise TypeError('MatchOperator sublcass required')
		if not issubclass(left_expression.__class__, Expression):
			raise TypeError('Expression subclass required for left_expression parameter')
		if not issubclass(right_expression.__class__, Expression):
			raise TypeError('Expression subclass required for right_expression parameter')

		self._operator = operator
		self._left_expression = left_expression
		self._right_expression = right_expression
	
	def compile(self):
		return 'RC.match(%s,%s)' % (self._left_expression.compile(), self._right_expression.compile())

class LogicalExpression(BinaryExpression):
	def __init__(self, operator, left_expression, right_expression):
		if not issubclass(operator.__class__, LogicalOperator):
			raise TypeError('LogicalOperator sublcass required')
		if not issubclass(left_expression.__class__, Expression):
			raise TypeError('Expression subclass required for left_expression parameter')
		if not issubclass(right_expression.__class__, Expression):
			raise TypeError('Expression subclass required for right_expression parameter')

		self._operator = operator
		self._left_expression = left_expression
		self._right_expression = right_expression

class InExpression(BinaryExpression):
	def __init__(self, operator, left_expression, right_expression):
		if not issubclass(operator.__class__, InOperator):
			raise TypeError('InOperator subclass required')
		if not issubclass(right_expression.__class__, ValueListExpression):
			raise TypeError('ValueListExpression required for right operand')
		
		if not issubclass(SymbolExpression, left_expression.__class__) and not issubclass(ValueExpression, left_expression.__class__):
			raise TypeError('ValueExpression or SymbolExpression required for left operand')

		self._operator = operator
		self._left_expression = left_expression
		self._right_expression = right_expression
	
	def compile(self):
		if self._operator.token().ttype=='in':
			text = 'in'
		else:
			text='not in'
			
		return '(%s %s %s)' % (
			self._left_expression.compile(), 
			text,
			self._right_expression.compile() )
	
class EqualExpression(BinaryExpression):
	def __init__(self, operator, left_expression, right_expression):
		if not issubclass(operator.__class__, EqualOperator):
			raise TypeError('EqualOperator sublcass required')
		if not issubclass(left_expression.__class__, Expression):
			raise TypeError('Expression subclass required for left_expression parameter')
		if not issubclass(right_expression.__class__, Expression):
			raise TypeError('Expression subclass required for right_expression parameter')

		self._operator = operator
		self._left_expression = left_expression
		self._right_expression = right_expression

class NotExpression(Expression):
	def __init__(self, operator, right_expression):
		if not issubclass(operator.__class__, NotOperator):
			raise TypeError('NotOperator subclass required')
		if not issubclass(right_expression.__class__, Expression):
			raise TypeError('Expression subclass required for right_expression parameter')
		
		self._operator = operator
		self._right_expression = right_expression

	def find_symbols(self):
		return self._right_expression.find_symbols()

	def token(self):
		return self._operator.token()

	def dump(self,ilevel=0):
		rv= '%s%s\n' % (Expression.dump_space*ilevel, self.dump_repr())
		rv += self._right_expression.dump(ilevel+1)
		return rv
	
	def dump_repr(self):
		return 'NotExpression(%s)' % repr(self._operator)
	
	def compile(self):
		return '(not %s)' % self._right_expression.compile()
	
class TerminalExpression(Expression):
	def token(self):
		return self._value_token
	
	def __repr__(self):
		return '%s.%s(%s)' % (self.__module__, self.__class__.__name__, repr(self.token()))

	def dump(self,ilevel=0):
		return '%s%s\n' % (Expression.dump_space*ilevel, self.dump_repr())

	def find_symbols(self):
		return []

	def dump_repr(self):
		return '%s(%s)' % (
			self.__class__.__name__, 
			repr(self._value_token) )
	
class SymbolExpression(TerminalExpression):
	def __init__(self, value_token):
		if not issubclass(tokenize.Token, value_token.__class__):
			raise TypeError('tokenize.Token sublcass required')
		if not value_token.ttype in ('symbol'):
			raise ValueError('symbol token type required')
		self._value_token = value_token

	def find_symbols(self):
		return [self._value_token.data]

	def compile(self):
		return ' SYMBOL[%s] ' % repr(self._value_token.data)
	
class ValueListExpression(TerminalExpression):
	def __init__(self,value_token):
		if not issubclass(tokenize.TokenList, value_token.__class__):
			raise TypeError('tokenize.TokenList sublcass required')
		self._value_token = value_token
	
	def compile(self):
		return self._value_token.python_repr()
	
	def __repr__(self):
		return '%s.%s(%s)' % (self.__module__, self.__class__.__name__, repr(self._value_token))

class ValueExpression(TerminalExpression):
	def __init__(self, value_token):
		if not issubclass(tokenize.Token, value_token.__class__):
			raise TypeError('tokenize.Token sublcass required')
		if not value_token.ttype in ('string','int','regex'):
			raise ValueError('string|int|regex token type required')
		self._value_token = value_token
	
	def compile(self):
		return repr(self._value_token.data)

###############################################################################

def nodeify(tokens):
	"""transforms a recursive list of tokens into lists of Expression and Operator
	sublcasses"""
	
	if type(tokens) != type([]):
		raise TypeError('List required')
	
	for i in range(0,len(tokens)):
		if type(tokens[i])==type([]):
			tokens[i] = nodeify(tokens[i])
		elif issubclass(tokenize.Token, tokens[i].__class__):
			if tokens[i].ttype in ('equal', 'notequal'):
				tokens[i] = EqualOperator(tokens[i])
			elif tokens[i].ttype in ('in','notin'):
				tokens[i] = InOperator(tokens[i])
			elif tokens[i].ttype in ('int','string','regex'):
				tokens[i] = ValueExpression(tokens[i])
			elif tokens[i].ttype in ('symbol'):
				tokens[i] = SymbolExpression(tokens[i])
			elif tokens[i].ttype in ('and','or'):
				tokens[i] = LogicalOperator(tokens[i])
			elif tokens[i].ttype in ('not'):
				tokens[i] = NotOperator(tokens[i])
			elif tokens[i].ttype == 'match':
				tokens[i] = MatchOperator(tokens[i])
			elif tokens[i].ttype == 'semicolon':
				raise errors.SemicolonExpressionError()
			else:
				raise NotImplementedError("Don't know how to level up a token of type "+tokens[i].ttype)
		elif issubclass(tokens[i].__class__, tokenize.TokenList):
			tokens[i] = ValueListExpression(tokens[i])
		else:
			raise TypeError('List member of unknown type (needed List or tokenize.Token)')

	return tokens

###############################################################################

class InsufficientOperands(Exception):
	def __init__(self, operator, position):
		assert issubclass(operator.__class__, Operator)
		assert position in  ('left','right')
		self._operator = operator
		self._position = position
	
	def __str__(self):
		return '%s operand not present for operator %s' % (
			self._position, self._operator.token().data )

def build_expression(operator, left_operand=None, right_operand=None):
	"""Takes an Operator and one or two Expressions and returns a new 
	Expression that is the combination of these things."""

	if not issubclass(operator.__class__, Operator):
		raise TypeError('Operator subclass required for operator parameter, got '+str(right_operand.__class__))
	if left_operand is not None:
		if not issubclass(left_operand.__class__, Expression):
			raise TypeError('Expression or None required for left_operand, got '+str(right_operand.__class__))
	if right_operand is not None:
		if not issubclass(right_operand.__class__, Expression):
			raise TypeError('Expression or None required for right_operand, got '+str(right_operand.__class__))
			

	if issubclass(operator.__class__, BinaryOperator):
		if left_operand is None or right_operand is None:
			raise ValueError('a binary operator requires two operands to build')


		if issubclass(operator.__class__, EqualOperator):
			return EqualExpression(operator, left_operand, right_operand)
		elif issubclass(operator.__class__, LogicalOperator):
			return LogicalExpression(operator, left_operand, right_operand)
		elif issubclass(operator.__class__, MatchOperator):
			return MatchExpression(operator, left_operand, right_operand)
		elif issubclass(operator.__class__, InOperator):
			return InExpression(operator, left_operand, right_operand)

	if issubclass(operator.__class__, NotOperator):
		if left_operand is not None or right_operand is None:
			raise ValueError('a not operator requires a right operand only')
		return NotExpression(operator, right_operand)

	raise NotImplementedError('Unknown operator class: %s' % operator.__class__)

def build_expressions(node_list): 
	"""Assembles a parse tree: combines a recursive list of Expression and
	Operator objects into (eventually) a single Expression object which is
	the root of the parse tree."""

	left_node_list = []
	
	# first go through and process all sublists so we contain only
	# a flat list of Expression and Operator subclasses
	for i in range(0,len(node_list)):
		if type(node_list[i]) == type([]):
			node_list[i] = build_expressions(node_list[i])

	while len(node_list)>0:
		node = node_list.pop(0)

		if issubclass(node.__class__, Operator):
			if node.want_left_operand():

				if len(left_node_list)==0:
					#raise InsufficientOperands(node,'left')
					raise errors.MissingOperand(node.token(),'left')
				if not issubclass(left_node_list[-1].__class__, Expression):
					if issubclass(left_node_list[-1].__class__, Operator):
						#raise ValueError('wanted an expr, got operator')
						raise errors.OperatorInsteadOfOperand(node.token(), 'left')
					else:
						raise TypeError('Unknown object in node list: %s' % str(left_node_list[-1]))
					
				left_operand = left_node_list.pop(-1)
			else:
				left_operand = None

			if node.want_right_operand():

				if len(node_list)==0:
					#raise InsufficientOperands(node,'right')
					raise errors.MissingOperand(node.token(), 'right')
				if not issubclass(node_list[0].__class__, Expression):
					if issubclass(node_list[0].__class__, Operator):
						#raise ValueError('wanted an expr, got operator')
						raise errors.OperatorInsteadOfOperand(node.token(), 'right')
					else:
						raise TypeError('Unknown object in node list: %s' % str(node_list[0]))
						
				right_operand = node_list.pop(0)
			else:
				right_operand = None
			
			left_node_list.append(build_expression(node, left_operand, right_operand))

		elif issubclass(node.__class__, Expression):
			left_node_list.append(node)
		
		else:
			raise TypeError('given a node_list containing an element of an unknown type: '+str(node.__class__))
	
	if len(left_node_list) > 1:
		raise errors.ExcessiveOperands(left_node_list[0].token())

	assert len(left_node_list)==1
	
	return left_node_list[0]

##################################################################################
##################################################################################
## These things are for compiling and executing the parsed statement.
##################################################################################
##################################################################################
		
class RegexCache(object):
	def __init__(self):
		self._cache = {}
	
	def match(self, regex, string):
		if not self._cache.has_key(regex):
			self._cache[regex] = re.compile(regex)
		
		if self._cache[regex].match(string) is None:
			return False
		else:
			return True

class SymbolExpansionError(Exception):
	def __init__(self, symbol, exception):
		self._symbol = symbol
		self._exception = exception

	def __str__(self):
	 	return 'Error expanding symb "%s": %s' % (self._symbol, str(self._exception))

def expand_symbols(symbols, namespace):
	values = {}
	for symbol in symbols:
		try:
			values[symbol] = eval(symbol, namespace) 
		except Exception, e:
			raise SymbolExpansionError(symbol, e)
	
	return values

def parse(tokens, logger=debug.NullDebugLogger()): 
	"""Takes a list of Tokens and assembles it into a parse tree. Returns
	the Expression object at the root of the parse tree."""

	logger.debug('---- begin parse.parse ----')
	logger.debug('---- listify -------------')

	tokens = listify(tokens)
	logger.debug(str(tokens))

	logger.debug('---- parenthesize ----')
	
	tokens = parenthesize(tokens)
	logger.debug(str(tokens))

	logger.debug('---apply_precedence--------------------')
	
	tokens = apply_precedence_1(tokens)
	tokens = apply_precedence_2(tokens)
	logger.debug('precedence applied: '+str(tokens))

	logger.debug('---nodeify--------------------')
	
	nodes = nodeify(tokens)
	logger.debug(str(nodes))

	logger.debug('----build_expressions-----------------------')

	if len(nodes)==0:
		return None
	
	root = build_expressions(nodes)
	dump = root.dump()
	for line in dump.split('\n'):
		logger.debug(line)

	logger.debug('---- end parse.parse ----')
	return root

