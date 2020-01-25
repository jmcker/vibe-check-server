import sys, os

print(__file__)

os.chdir(os.path.dirname(__file__))
sys.path.append(os.path.dirname(__file__))

import bottle
from server import *