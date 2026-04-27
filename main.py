from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from openai import OpenAI
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)


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

    prompt = f"""
你係 FreerOS AI Manager。請根據以下 state，決定下一步最實際行動，並寫一段簡短 summary。

current_goal: {state.get("current_goal")}
current_direction: {state.get("current_direction")}
key_decisions: {state.get("key_decisions")}
constraints: {state.get("constraints")}
next_focus: {state.get("next_focus")}

請只用以下格式回答：
next_focus: <下一步行動，20字內>
summary: <一句簡短摘要>
"""

    # 2. 用 AI 產生 next_focus + summary
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content or ""

    next_focus = "Review current state"
    summary = content.strip()

    for line in content.splitlines():
        if line.lower().startswith("next_focus:"):
            next_focus = line.split(":", 1)[1].strip()
        elif line.lower().startswith("summary:"):
            summary = line.split(":", 1)[1].strip()

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