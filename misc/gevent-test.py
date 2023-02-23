#!/usr/bin/env python
from __future__ import print_function
import gevent
from gevent import subprocess

import sys

if sys.platform.startswith('win'):
    UNAME = ['cmd.exe', '/C', 'ver']
    LS = ['dir.exe']
else:
    UNAME = ['uname']
    LS = ['ls;sleep 3;ls']

# run 2 jobs in parallel
p1 = subprocess.Popen(UNAME, stdout=subprocess.PIPE, shell=True)
p2 = subprocess.Popen(LS, stdout=subprocess.PIPE,shell=True)

gevent.wait([p1, p2], timeout=1)

# print the results (if available)
if p1.poll() is not None:
    print('uname: %r' % p1.stdout.read())
else:
    print('uname: job is still running')
if p2.poll() is not None:
    print('ls: %r' % p2.stdout.read())
else:
    print('ls: job is still running')

p1.stdout.close()
p2.stdout.close()