
import re

import errors
import debug

#####################################################################################
#####################################################################################
## These things are for tokenizing raw input strings. Tokenization divides input
## up into the smallest components that have any meaning.
#####################################################################################
#####################################################################################


def find_endsquote(s,quotechar):
	"""Given a string (s) the first character of which is the start of a
	quoted string (quoted by quotechar), find the index of the close
	quote."""

	start=0
	while True:
		idx = s.index(quotechar,start)
		if idx>1 and s[idx-1]!='\\':
			return idx+1
		elif idx<=1:
			return idx+1
		start+=idx+1

class Token(object):
	"""Represents an indivisible element of the language, like a string or
	an operator or a parentesis."""

	def __init__(self, ttype, data, lineno, linepos ):
		self.ttype = ttype
		self.data = data
		self.lineno = lineno
		self.linepos = linepos
		self._first = False
		self._last = False
	
	def __repr__(self):
		return '%s.%s(%s, %s, %s, %s)' % ( self.__module__, self.__class__.__name__, repr(self.ttype), repr(self.data), repr(self.lineno), repr(self.linepos) )
		#return repr(self.data)
	
	def __str__(self):
		return 'TOKEN(%s) line %d char %d: %s' % (self.ttype, self.lineno, self.linepos, str(self.data))


class TokenList(object):
	def __init__(self, list=None):
		"""open and closebracket are Token objects of type openbracket and
		closebracket. They are needed in case they are the first or last
		tokens in the expression (which are in turn used for error
		messages)."""

		self._list = []
		self._type = None

		if list is not None:
			for member in list:
				self.add_token(member)
	
	def add_token(self,token):
		if token.ttype not in ('int','string'):
			raise errors.InvalidListMember('Invalid token type for list member: '+token.ttype)
		if self._type is not None:
			if self._type != token.ttype:
				raise errors.InconsistListMemberType('All tokens in a list must have the same type')
		self._type = token.ttype
		self._list.append(token)
	
	def type(self):
		return self._type
	
	def contents(self):
		return self._list
		
	def python_repr(self):
		return str(map( lambda i: i.data, self._list ))
	
	def __repr__(self):
		return '%s.%s(list=%s)' % (
			self.__module__, self.__class__.__name__, 
			repr(self._list))


class Tokenizer(object):
	"""Chops a string (containing the expressions to compile) into tokens -
	the smallest bits that contain any meaning."""

	def __init__(self):
		self._lineno=1
		self._linepos=1

		self._exp_comment=re.compile('^#[^\n]*\n(.*)', re.DOTALL)
		self._exp_white=re.compile('^[ \t]+(.*)', re.DOTALL)
		self._exp_word = re.compile('^([_a-zA-Z]{1}[._a-zA-Z0-9]*)(.*)', re.DOTALL)
		self._exp_int = re.compile('^([0-9]+)(.*)', re.DOTALL)
		self._exp_notinop = re.compile('^(not[ \t]+in)(.*)', re.DOTALL)

		self._exp_midsymchars = re.compile('^[_.a-zA-Z0-9]+', re.DOTALL)
		self._midsymchars = [chr(i) for i in range(65,91)] + [chr(i) for i in range(97,123)] + [str(i) for i in range(0,10)] + ['_','.']
	
	def get_token(self,data):
		"""Given a raw input string, return the first token off of the front
		of it. Returns a (token, rest) tuple, the first item of which is a
		Token object and the second item of which is the rest of the input
		string."""

		if data[0] in ('"', "'", '/'):
			try:
				close_quote_idx = find_endsquote(data[1:],data[0])
			except ValueError, ve:
				if data[0]=='/':
					raise errors.UnclosedREError(data, self._lineno)
				else:
					raise errors.UnclosedQuoteError(data, self._lineno)
			
			s = data[1:close_quote_idx]
			rest=data[close_quote_idx+1:]

			if data[0]=='/':
				ttype='regex'
			else:
				ttype='string'

			if ttype=='regex':
				# test compile the regex, just to see if it works
				# best to determine this at compile time, easier to report,
				# better for the user.
				try:
					re.compile(s)
				except re.error, ree:
					raise errors.UncompileableRegexError(s, self._lineno, ree)

			t = Token(ttype,s, self._lineno, self._linepos)
			self._linepos += len(data) - len(rest)

			return (rest, t)
			
		if data[0]=='[':
			self._linepos += 1
			return (data[1:], Token('openbracket', '[', self._lineno, self._linepos))
		
		if data[0]==']':
			self._linepos += 1
			return (data[1:], Token('closebracket', ']', self._lineno, self._linepos))

		if data[0]==',':
			self._linepos += 1
			return (data[1:], Token('comma', ',', self._lineno, self._linepos))

		if data[0]=='\n':
			self._lineno+=1
			self._linepos=1
			return (data[1:], None)
			
		mg = self._exp_white.match(data)
		if mg:
			self._linepos += len(data) - len(mg.group(1))
			return (mg.group(1),None)

		mg = self._exp_comment.match(data)
		if mg:
			self._lineno+=1
			self._linepos=1
			return (mg.group(1), None)
		#print 'NO comment match on',repr(data)

		if data[0]=='#' and '\n' not in data:
			#print 'comment to END!'
			self._linepos+=len(data)
			return ('', None)

		mg = self._exp_notinop.match(data)
		if mg:
			t = Token('notin', mg.group(1), self._lineno, self._linepos)
			self._linepos += len(mg.group(1))
			return (mg.group(2), t)
		
		if data[0]=='(':
			t = Token('oparen', data[0], self._lineno, self._linepos)
			self._linepos += 1
			return (data[1:], t)

		if data[0]==')':
			t = Token('cparen', data[0], self._lineno, self._linepos)
			self._linepos += 1
			return (data[1:], t)
		
		mg = self._exp_int.match(data)
		if mg:
			t = Token('int', int(mg.group(1)), self._lineno, self._linepos)
			self._linepos += len(data) - len(mg.group(2))
			return (mg.group(2), t)
		
		if data[0]==';':
			t = Token('semicolon', data[0], self._lineno, self._linepos)
			self._linepos += 1
			return (data[1:], t)
		
		if data[0:2]=='==':
			t = Token('equal', data[0:2], self._lineno, self._linepos)
			self._linepos += 2
			return (data[2:], t)

		if data[0:2]=='!=':
			t = Token('notequal', data[0:2], self._lineno, self._linepos)
			self._linepos += 2
			return (data[2:], t)

		if data[0:2]=='&&':
			t = Token('and', data[0:2], self._lineno, self._linepos)
			self._linepos += 2
			return (data[2:], t)

		if data[0:3]=='and':
			if len(data)>3:
				if data[3] not in self._midsymchars:
					t = Token('and', data[0:3], self._lineno, self._linepos)
					self._linepos += 3
					return (data[3:], t)
			else:
				t = Token('and', data[0:3], self._lineno, self._linepos)
				self._linepos += 3
				return (data[3:], t)
				

		if data[0:2]=='or':
			if len(data)>2:
				if data[2] not in self._midsymchars:
					t = Token('or', data[0:2], self._lineno, self._linepos)
					self._linepos += 2
					return (data[2:], t)
			else:
				t = Token('or', data[0:2], self._lineno, self._linepos)
				self._linepos += 2
				return (data[2:], t)

		if data[0:2]=='||':
			t = Token('or', data[0:2], self._lineno, self._linepos)
			self._linepos += 2
			return (data[2:], t)
		
		if data[0:3]=='not' and data[3] not in self._midsymchars:
			t = Token('not', data[0:3], self._lineno, self._linepos)
			self._linepos += 3
			return (data[3:], t)
		
		if data[0]=='!':
			t = Token('not', data[0], self._lineno, self._linepos)
			self._linepos += 1
			return (data[1:], t)
			
		if data[0:2]=='=~':
			t = Token('match', data[0:2], self._lineno, self._linepos)
			self._linepos += 2
			return (data[2:], t)
		
		if data[0:2]=='in' and data[2] not in self._midsymchars:
			t = Token('in', data[0:2], self._lineno, self._linepos)
			self._linepos += 2
			return (data[2:], t)

		
		mg = self._exp_word.match(data)
		if mg:
			t = Token('symbol', mg.group(1), self._lineno, self._linepos)
			self._linepos += len(mg.group(1))
			return (mg.group(2), t )
		
		raise errors.UnknownTokenError(data, self._lineno)

def divide_expressions(token_list):
	"""Takes a list of Tokens. This list will divide the tokens for multiple
	expressions separated by semicolons up and return each list as a member
	of a list that this function returns. Example: [1,'==',1,';',2,'==','2']
	-> [ [1,'==',1] , [2,'==','2'] ]."""
	
	rv = []
	current_list = []
	
	for token in token_list:
		if token.ttype=='semicolon':
			if len(current_list) > 0:
				rv.append(current_list)
				current_list = []
		else:
			current_list.append(token)

	if len(current_list) > 0:
		rv.append(current_list)
	
	return rv

def tokenize(input, debugLogger=debug.NullDebugLogger()):

	"""takes a series of tokens and divides them up into lists of lists of
	expressions (separated based on semicolons). This is only used for
	building sieves, not standalone filters."""

	tzr = Tokenizer()
	tokens = []
	while input:
		(rest, token) = tzr.get_token(input)
		input = rest
		if token:
			debugLogger.write('* '+str(token))
			tokens.append(token)

	debugLogger.write('post-tokenize: '+str(tokens))
	tokens = divide_expressions(tokens)
	debugLogger.write('post-divide: '+str(tokens))
	
	return tokens
	