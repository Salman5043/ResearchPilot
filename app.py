# from dotenv import load_dotenv

# load_dotenv()


# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from api.routes import router


# # ============================================================
# # APPLICATION
# # ============================================================

# app = FastAPI(

#     title="AI Research Assistant",

#     description=
#         "LangGraph powered AI Research Assistant",

#     version="1.0.0"
# )


# # ============================================================
# # CORS
# # ============================================================

# app.add_middleware(

#     CORSMiddleware,

#     allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",") if origin.strip()],

#     allow_credentials=True,

#     allow_methods=["*"],

#     allow_headers=["*"]
# )


# # ============================================================
# # ROUTES
# # ============================================================

# app.include_router(

#     router,

#     prefix="/api"
# )


# # ============================================================
# # ROOT
# # ============================================================

# @app.get("/")
# def root():

#     return {

#         "message":
#             "AI Research Assistant API",

#         "version":
#             "1.0.0",

#         "docs":
#             "/docs",

#         "health":
#             "/api/health"
#     }

from dotenv import load_dotenv

load_dotenv()


import os
import webbrowser

from contextlib import asynccontextmanager
from pathlib import Path
from threading import Timer

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Auto-open the browser when uvicorn starts.
    # The RUN_MAIN check makes sure this only fires in the
    # actual server process, not in the --reload watcher.

    if os.getenv("AUTO_OPEN_BROWSER", "false").lower() == "true" and os.environ.get("RUN_MAIN") == "true":

        Timer(
            1.0,
            lambda: webbrowser.open(
                "http://127.0.0.1:8000/"
            )
        ).start()

    yield


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(

    title=
        "AI Research Assistant",

    description=
        "LangGraph powered AI Research Assistant",

    version=
        "1.2.0",

    lifespan=
        lifespan
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",") if origin.strip()],

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"]
)


# ============================================================
# API ROUTES
# ============================================================

app.include_router(

    router,

    prefix="/api"
)


# ============================================================
# STATIC DIRECTORY
# ============================================================

STATIC_DIR.mkdir(
    exist_ok=True
)


app.mount(

    "/static",

    StaticFiles(directory=STATIC_DIR),

    name="static"
)


# ============================================================
# FRONTEND
# ============================================================

@app.get(
    "/",
    include_in_schema=False
)
def serve_frontend():

    index_file = STATIC_DIR / "index.html"


    if not index_file.is_file():

        return Response(

            content=(

                "<h1>Frontend not found</h1>"

                "<p>Place your frontend file at: "

                f"<code>{index_file}</code></p>"

                "<p>Then refresh this page.</p>"
            ),

            media_type="text/html",

            status_code=500
        )


    return FileResponse(index_file)


@app.get(
    "/favicon.ico",
    include_in_schema=False
)
def favicon():

    return Response(
        status_code=204
    )


# ============================================================
# ROOT API INFO
# ============================================================

@app.get(
    "/api",
    include_in_schema=False
)
def api_info():

    return {

        "message":
            "AI Research Assistant API",

        "version":
            "1.2.0",

        "docs":
            "/docs",

        "health":
            "/api/health",

        "frontend":
            "/"
    }