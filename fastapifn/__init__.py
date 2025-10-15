"""
FastAPIFn framework - Lambda-native FastAPI.
"""

__version__ = "0.1.0"

from fastapifn.response import HTMLResponse as HTMLResponse
from fastapifn.response import JSONResponse as JSONResponse
from fastapifn.response import PlainTextResponse as PlainTextResponse
from fastapifn.response import RedirectResponse as RedirectResponse

# Lambda-native core
from .app import FastAPI as FastAPI
from .app import LambdaEvent as LambdaEvent
from .app import create_lambda_handler as create_lambda_handler

# Exceptions
from .exceptions import HTTPException as HTTPException

# Parameter functions
from .param_functions import Body as Body
from .param_functions import Depends as Depends
from .param_functions import Header as Header
from .param_functions import Path as Path
from .param_functions import Query as Query
from .param_functions import Security as Security
