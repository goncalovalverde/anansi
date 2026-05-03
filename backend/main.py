import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

import database
import api.config
import api.data
import api.charts
import api.insights
import api.flow
import api.trends

app = FastAPI(title="Anansi", description="Jira/CSV backlog analytics dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db(database.DB_PATH)

app.include_router(api.config.router)
app.include_router(api.data.router)
app.include_router(api.charts.router)
app.include_router(api.insights.router)
app.include_router(api.flow.router)
app.include_router(api.trends.router)

_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend-vue", "dist")
if os.path.isdir(_frontend_dir):
    app.mount(
        "/",
        StaticFiles(directory=_frontend_dir, html=True),
        name="static",
    )
