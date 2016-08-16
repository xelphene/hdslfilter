
class StdoutDebugLogger(object):
	def debug(self, s):
		print 'DEBUG:',s

class NullDebugLogger(object):
	def debug(self, s):
		pass

	def write(self, msg):
		pass
