#!/usr/bin/env python3

# This WSGI script can be used with apache2 wsgi interface.
# Make sure:
# - there is venv/bin/activate_this.py (use virtualenv, not venv module)
# - that the paths are valid
# - if having problems, turning the logging level to DEBUG may help
# - adding logging.info(...) here and there is primitive, but effective technique

import os
import runpy
import sys
import logging

HOME_DIR = '/home/svarog'

logging.basicConfig(filename=os.path.join(HOME_DIR, 'logs/wsgi.log'),
                    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)d: %(message)s',
                    level=logging.INFO)

activate_this = os.path.join(HOME_DIR, 'devel/svarog/server/venv/bin/activate_this.py')

runpy.run_path(activate_this)

sys.path.insert(0, os.path.join(HOME_DIR, 'devel/svarog/server'))

path = os.path.join(os.path.dirname(__file__), os.pardir)
if path not in sys.path:
    sys.path.append(path)

from app import app as application
application.secret_key = 'your secret key here'

# Uncomment this to get more information about template loading
# application.config['EXPLAIN_TEMPLATE_LOADING'] = True
