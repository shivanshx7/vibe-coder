# ai_logic.py
import os, json
from datetime import datetime

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")
TOPICS_FILE = os.path.join(DATA_DIR, "topics.json")

def load_topics():
    if not os.path.exists(TOPICS_FILE):
        sample = [
            {"name":"Math","mastery":0.4,"confidence":0.9,"importance":0.9,"priority":0},
            {"name":"Physics","mastery":0.6,"confidence":0.6,"importance":0.8,"priority":0},
            {"name":"Chemistry","mastery":0.5,"confidence":0.4,"importance":0.7,"priority":0}
        ]
        with open(TOPICS_FILE, "w") as f:
            json.dump(sample, f, indent=2)
    with open(TOPICS_FILE, "r") as f:
        return json.load(f)

def save_topics(topics):
    with open(TOPICS_FILE, "w") as f:
        json.dump(topics, f, indent=2)

def importance(topic):
    return max(0.0, min(1.0, topic.get("importance", 0.5)))

def best_mode(topic, preferences):
    if topic.get("mastery",0) < 0.5:
        return "Practice"
    if topic.get("confidence",0) < 0.4:
        return "Concept"
    return "Revision"

def adjust_duration(attention_span, topic):
    base = attention_span or 45
    factor = 0.9 + (1 - topic.get("mastery",0)) * 0.6
    duration = int(max(15, min(90, base * factor)))
    return duration

def recompute_plan_for_user(username, users, topics, dry_run=False):
    user = users.get(username)
    if not user:
        raise ValueError("unknown user")
    for t in topics:
        M = float(t.get("mastery",0.0))
        C = float(t.get("confidence",0.5))
        G = abs(M - C)
        imp = importance(t)
        P = 0.5 * (1 - M) + 0.3 * G + 0.2 * imp
        t["priority"] = round(P, 4)
    topics.sort(key=lambda x: x["priority"], reverse=True)
    N = user.get("preferences", {}).get("daily_topics", None) or user.get("preferences", {}).get("daily_sessions", 3) or 3
    plan = []
    att = user.get("attention_span", 45)
    missed = user.get("missed_sessions", 0)
    completed = user.get("completed_sessions", 0)
    missed_ratio = 0
    if completed + missed > 0:
        missed_ratio = missed / (completed + missed)
    for t in topics[:N]:
        stype = best_mode(t, user.get("preferences", {}))
        dur = adjust_duration(att, t)
    if missed_ratio > 0.4:
        dur = max(15, int(dur * 0.6))
    session = {
        "topic": t["name"],
        "type": stype,
        "duration": dur,
        "priority": t["priority"],
        "scheduled": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    }

    # <-- Add this line to precompute width for progress bar
    session["width"] = int(t.get("mastery", 0) * 100)

    plan.append(session)
    suggestions = []
    if missed_ratio > 0.4:
        suggestions.append("Split long sessions into shorter daily ones")
    if any(t["priority"] > 0.6 for t in topics):
        suggestions.append("High priority topics need focused practice.")
    if not dry_run:
        save_topics(topics)
    return {"plan": plan, "suggestions": suggestions, "missed_ratio": round(missed_ratio, 2)}
