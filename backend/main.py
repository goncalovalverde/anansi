import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import database
from . import api
from .api import config, data, charts, insights, flow, trends, health

app = FastAPI(title="Anansi", description="Jira/CSV backlog analytics dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db(database.DB_PATH)

app.include_router(config.router)
app.include_router(data.router)
app.include_router(charts.router)
app.include_router(insights.router)
app.include_router(flow.router)
app.include_router(trends.router)
app.include_router(health.router)

_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend-vue", "dist")
if os.path.isdir(_frontend_dir):
    app.mount(
        "/",
        StaticFiles(directory=_frontend_dir, html=True),
        name="static",
    )
