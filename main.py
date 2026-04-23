from fastapi import FastAPI
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

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