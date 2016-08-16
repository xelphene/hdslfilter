#!/usr/bin/env python

from distutils.core import setup
import sys

if sys.argv[1]=='sdist':
	sys.path = ['.'] + sys.path
	import hdslfilter.__init__
	version = hdslfilter.__init__.__version__
else:
	version = '0.0.0'

setup(
	name='hdslfilter',
	version=version,
	description='Filtering language for filtering Python datastructures',
	author='Steve Benson / Hurricane Labs',
	author_email='steve@hurricanelabs.com',
	license='GPLv3',
	url='http://www.hurricanelabs.com',
	packages=['hdslfilter/']
)
