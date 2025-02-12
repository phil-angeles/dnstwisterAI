import os
from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import Response, RedirectResponse
from fastapi.templating import Jinja2Templates


app = FastAPI(
    title=os.environ.get("APP_NAME"),
    debug=os.environ.get("APP_DEBUG"),
    description=os.environ.get("APP_DESCRIPTION")
)

@app.get("/")
def test():
    return {
        "status": "OK",
        "message": "Running success"
    }
