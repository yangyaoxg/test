from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from app.db import init_db
from app.services import create_student, generate_paper, get_student_dashboard, submit_paper

app = FastAPI(title="小学知识查漏补缺系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event() -> None:
    init_db()


class StudentCreateReq(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    grade: str = "四年级下"


class GeneratePaperReq(BaseModel):
    student_id: int
    count: int = Field(default=20, ge=5, le=20)


class SubmitReq(BaseModel):
    student_id: int
    paper_id: str
    answers: dict[str, str]


class ReinforceReq(BaseModel):
    student_id: int
    weak_points: list[str]
    count: int = Field(default=10, ge=5, le=20)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/student/create")
def api_create_student(payload: StudentCreateReq):
    return {"ok": True, "student": create_student(payload.name, payload.grade)}


@app.post("/api/paper/generate")
def api_generate_paper(payload: GeneratePaperReq):
    try:
        paper = generate_paper(student_id=payload.student_id, paper_type="diagnosis", count=payload.count)
        return {"ok": True, "paper": paper}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/paper/submit")
def api_submit_paper(payload: SubmitReq):
    try:
        analysis = submit_paper(student_id=payload.student_id, paper_id=payload.paper_id, answers=payload.answers)
        return {"ok": True, "analysis": analysis}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/paper/reinforce")
def api_reinforce(payload: ReinforceReq):
    try:
        paper = generate_paper(
            student_id=payload.student_id,
            paper_type="reinforce",
            count=payload.count,
            weak_points=payload.weak_points,
        )
        return {"ok": True, "paper": paper}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/student/{student_id}/dashboard")
def api_student_dashboard(student_id: int):
    try:
        data = get_student_dashboard(student_id)
        return {"ok": True, "dashboard": data}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
