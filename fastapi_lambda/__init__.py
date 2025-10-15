"""
FastAPI-Lambda framework - Lambda-native FastAPI.
"""

from fastapi_lambda.app import FastAPI as FastAPI
from fastapi_lambda.response import HTMLResponse as HTMLResponse
from fastapi_lambda.response import JSONResponse as JSONResponse
from fastapi_lambda.response import PlainTextResponse as PlainTextResponse
from fastapi_lambda.response import RedirectResponse as RedirectResponse

from .app import LambdaEvent as LambdaEvent
from .app import create_lambda_handler as create_lambda_handler
from .exceptions import HTTPException as HTTPException
from .param_functions import Body as Body
from .param_functions import Depends as Depends
from .param_functions import Header as Header
from .param_functions import Path as Path
from .param_functions import Query as Query
from .param_functions import Security as Security

__version__ = "0.2.0"
