# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os, json
from datetime import datetime
from ai_logic import recompute_plan_for_user, load_topics, save_topics

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # change for production

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
TOPICS_FILE = os.path.join(DATA_DIR, "topics.json")

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f, indent=2)
    if not os.path.exists(TOPICS_FILE):
        sample = [
            {"name":"Math","mastery":0.4,"confidence":0.9,"importance":0.9,"priority":0},
            {"name":"Physics","mastery":0.6,"confidence":0.6,"importance":0.8,"priority":0},
            {"name":"Chemistry","mastery":0.5,"confidence":0.4,"importance":0.7,"priority":0}
        ]
        with open(TOPICS_FILE, "w") as f:
            json.dump(sample, f, indent=2)

def load_users():
    ensure_data_dir()
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

@app.route("/", methods=["GET","POST"])
def index():
    users = load_users()
    if request.method == "POST":
        username = request.form.get("username","").strip()
        if not username:
            flash("Please enter a username.")
            return redirect(url_for("index"))
        if username not in users:
            users[username] = {
                "preferences": {"modes": ["Practice","Revision","Concept"], "daily_sessions": 3, "daily_topics": 3},
                "missed_sessions": 0,
                "completed_sessions": 0,
                "attention_span": 45,
                "last_plan_update": None
            }
            save_users(users)
        session["user"] = username
        return redirect(url_for("dashboard"))
    return render_template("index.html", users=list(users.keys()))

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("index"))
    username = session["user"]
    users = load_users()
    topics = load_topics()
    user = users.get(username)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    if not user.get("last_plan_update") or user.get("last_plan_update") != today_str:
        plan = recompute_plan_for_user(username, users, topics)
        save_topics(topics)
        users[username]["last_plan_update"] = today_str
        save_users(users)
    else:
        plan = recompute_plan_for_user(username, users, topics, dry_run=True)
    return render_template("dashboard.html", username=username, plan=plan, topics=topics, user=user)

@app.route("/quiz", methods=["GET"])
def quiz():
    if "user" not in session:
        return redirect(url_for("index"))
    topic_name = request.args.get("topic")
    topics = load_topics()
    topic = None
    if topic_name:
        topic = next((t for t in topics if t["name"]==topic_name), None)
    return render_template("quiz.html", topic=topic, topics=topics)

@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    if "user" not in session:
        return redirect(url_for("index"))
    username = session["user"]
    topic = request.form.get("topic")
    try:
        score = float(request.form.get("score",0))
        max_score = float(request.form.get("max_score",10))
    except:
        score = 0.0
        max_score = 10.0
    if max_score <= 0: max_score = 10.0
    measured = max(0.0, min(1.0, score / max_score))
    topics = load_topics()
    updated_mastery = None
    for t in topics:
        if t["name"] == topic:
            alpha = 0.6
            t["mastery"] = round(alpha * measured + (1 - alpha) * t.get("mastery",0), 3)
            updated_mastery = t["mastery"]
            break
    save_topics(topics)
    users = load_users()
    users[username]["completed_sessions"] = users[username].get("completed_sessions",0) + 1
    save_users(users)
    flash(f"Quiz submitted for {topic}. Mastery → {updated_mastery}")
    return redirect(url_for("dashboard"))

@app.route("/confidence")
def confidence():
    if "user" not in session:
        return redirect(url_for("index"))
    topics = load_topics()
    return render_template("confidence.html", topics=topics)

@app.route("/update_confidence", methods=["POST"])
def update_confidence():
    if "user" not in session:
        return redirect(url_for("index"))
    topics = load_topics()
    for t in topics:
        key = f"confidence_{t['name']}"
        if key in request.form:
            try:
                v = float(request.form.get(key,5))
            except:
                v = 5
            t["confidence"] = round(max(0.0, min(1.0, v/10.0)),3)
    save_topics(topics)
    flash("Confidence updated.")
    return redirect(url_for("dashboard"))

@app.route("/update_plan")
def update_plan():
    if "user" not in session:
        return redirect(url_for("index"))
    username = session["user"]
    users = load_users()
    topics = load_topics()
    plan = recompute_plan_for_user(username, users, topics)
    save_topics(topics)
    users[username]["last_plan_update"] = datetime.utcnow().strftime("%Y-%m-%d")
    save_users(users)
    flash("Adaptive plan updated.")
    return redirect(url_for("dashboard"))

@app.route("/results")
def results():
    if "user" not in session:
        return redirect(url_for("index"))
    topics = load_topics()
    users = load_users()
    username = session["user"]
    user = users.get(username)
    avg_mastery = round(sum(t.get("mastery",0) for t in topics)/max(1,len(topics)),3)
    avg_conf = round(sum(t.get("confidence",0) for t in topics)/max(1,len(topics)),3)
    recommendations = []
    missed_ratio = 0
    if user.get("completed_sessions",0) + user.get("missed_sessions",0) > 0:
        missed_ratio = user.get("missed_sessions",0) / (user.get("completed_sessions",0) + user.get("missed_sessions",0))
    if missed_ratio > 0.4:
        recommendations.append("You miss many sessions — consider shorter daily sessions.")
    if avg_mastery < 0.6:
        recommendations.append("Overall mastery is low — focus on high priority topics.")
    return render_template("results.html", topics=topics, avg_mastery=avg_mastery, avg_conf=avg_conf, recommendations=recommendations)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    ensure_data_dir()
    app.run(debug=True)
