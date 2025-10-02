"""
Django settings module initialization.
Automatically imports the appropriate settings based on environment.
"""

import os
from decouple import config

# Determine which settings to use
ENVIRONMENT = config('ENVIRONMENT', default='dev')

if ENVIRONMENT == 'production':
    from .prod import *
elif ENVIRONMENT == 'dev':
    from .dev import *
else:
    from .base import *
