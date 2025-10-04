import json
import os

DATA_FOLDER = "data"
TOPICS_FILE = os.path.join(DATA_FOLDER, "topics.json")
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def measured_mastery(topic):
    return topic.get("mastery", 0.5)


def confidence(topic):
    return topic.get("confidence", 0.5)


def importance(topic):
    return topic.get("importance", 0.5)


def best_mode(topic, preferences):
    mastery = measured_mastery(topic)
    if mastery < 0.4:
        return "Concept Review"
    elif mastery < 0.7:
        return "Practice Quiz"
    else:
        return "Timed Test"


def adjust_duration(attention_span):
    if attention_span < 30:
        return 25
    elif attention_span < 45:
        return 35
    else:
        return 45


def update_plan(username):
    topics = load_json(TOPICS_FILE)
    users = load_json(USERS_FILE)
    user = users.get(username, {"attention_span": 30, "missed_sessions_ratio": 0.1})

    attention_span = user.get("attention_span", 30)
    missed_sessions_ratio = user.get("missed_sessions_ratio", 0.1)

    for topic in topics:
        M = measured_mastery(topic)
        C = confidence(topic)
        G = abs(M - C)
        P = 0.5 * (1 - M) + 0.3 * G + 0.2 * importance(topic)
        topic["priority"] = round(P, 2)

    topics.sort(key=lambda x: x["priority"], reverse=True)

    plan = []
    for topic in topics:
        session_type = best_mode(topic, user)
        duration = adjust_duration(attention_span)
        plan.append({
            "topic": topic["name"],
            "type": session_type,
            "duration": duration,
            "priority": topic["priority"],
            "scheduled": "Today",
            "width": round(measured_mastery(topic) * 100)
        })

    suggestions = []
    if missed_sessions_ratio > 0.3:
        suggestions.append("Consider shorter, more frequent sessions.")
    if any(t["priority"] > 0.7 for t in topics):
        suggestions.append("Focus on high-priority topics first.")

    save_json(TOPICS_FILE, topics)

    return {"plan": plan, "suggestions": suggestions}
