"""
FastAPI web server for JEP event visualization.
"""

import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from jep_agent.core.event import parse_json

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
    try:
        lines = content.decode("utf-8", errors="strict").split("\n")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Archive must be UTF-8") from exc
    events = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = parse_json(line)
            if not isinstance(event, dict):
                raise ValueError("Expected an event object")
        except (ValueError, RecursionError) as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid event JSON on line {number}"
            ) from exc
        events.append(event)
    if not events:
        raise HTTPException(status_code=400, detail="No events to display")
    return JSONResponse({"count": len(events), "events": events})


def start_server(host="127.0.0.1", port=8080, reload=False):
    import uvicorn

    uvicorn.run("jep_agent.web.server:app", host=host, port=port, reload=reload)
