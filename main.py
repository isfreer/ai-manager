from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.get("/")
def root():
    return {"message": "AI Manager API running"}


# 1. get_state
@app.get("/get_state")
def get_state():
    res = supabase.table("state").select("*").execute()
    return res.data


# 2. update_state
@app.post("/update_state")
def update_state(data: dict):
    # 1. 更新 state
    res = supabase.table("state").upsert(data).execute()

    # 2. 自動寫 summary（簡單版）
    summary_text = f"""
Goal: {data.get("current_goal")}
Direction: {data.get("current_direction")}
Decisions: {data.get("key_decisions")}
Focus: {data.get("next_focus")}
"""

    supabase.table("summaries").insert({
        "content": summary_text
    }).execute()

    return res.data


# 3. save_summary
@app.post("/save_summary")
def save_summary(data: dict):
    res = supabase.table("summaries").insert(data).execute()
    return res.data


# 4. auto_update
@app.post("/auto_update")
def auto_update():
    # 1. 讀取 current state
    state_res = supabase.table("state").select("*").eq("id", 1).execute()

    if not state_res.data:
        return {"error": "No state found for id = 1"}

    state = state_res.data[0]

    goal = (state.get("current_goal") or "").lower()
    direction = (state.get("current_direction") or "").lower()
    decisions = (state.get("key_decisions") or "").lower()
    constraints = state.get("constraints") or ""

    # 2. Rule-based automation（免費版，唔用 OpenAI）
    if "frontend" in goal or "dashboard" in goal:
        next_focus = "完成 dashboard 操作流程"
        summary = "系統判斷目前重點是完成前端 dashboard，並確保可以清楚顯示與操作 state。"
    elif "api" in direction or "backend" in decisions:
        next_focus = "測試 backend API 流程"
        summary = "系統判斷目前重點是確認 backend API 可以穩定讀寫 Supabase。"
    elif constraints:
        next_focus = "拆細下一步行動"
        summary = f"系統偵測到限制：{constraints}，因此下一步應先拆細任務，避免一次做太多。"
    else:
        next_focus = "整理目前狀態"
        summary = "系統已讀取目前 state，下一步應先整理目標、方向與待辦。"

    # 3. 更新 state
    supabase.table("state").update({
        "next_focus": next_focus
    }).eq("id", 1).execute()

    # 4. 儲存 summary
    supabase.table("summaries").insert({
        "content": summary
    }).execute()

    return {
        "next_focus": next_focus,
        "summary": summary
    }