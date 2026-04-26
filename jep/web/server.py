"""
FastAPI web server for JEP event visualization.
"""

import json
import os

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="JEP Web Viewer")


@app.get("/", response_class=HTMLResponse)
async def root():
    static_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_path):
        with open(static_path, "r") as f:
            return f.read()
    return "<h1>JEP Web Viewer</h1><p>Upload events.jsonl to visualize</p>"


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    lines = content.decode("utf-8").strip().split("\n")
    events = [json.loads(line) for line in lines if line.strip()]
    return JSONResponse({"count": len(events), "events": events})


def start_server(host="127.0.0.1", port=8080, reload=False):
    import uvicorn

    uvicorn.run("jep.web.server:app", host=host, port=port, reload=reload)
