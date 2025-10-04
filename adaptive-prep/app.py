from flask import Flask, render_template, request, redirect, url_for
from ai_logic import update_plan, load_json, save_json, TOPICS_FILE, USERS_FILE
import os

app = Flask(__name__)
USERNAME = "student"  # simple single-user demo


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    plan = update_plan(USERNAME)
    return render_template("dashboard.html", plan=plan)


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    topics = load_json(TOPICS_FILE)
    if request.method == "POST":
        for t in topics:
            key = f"{t['name']}_score"
            if key in request.form:
                t["mastery"] = float(request.form[key])
        save_json(TOPICS_FILE, topics)
        return redirect(url_for("dashboard"))
    return render_template("quiz.html", topics=topics)


@app.route("/confidence", methods=["GET", "POST"])
def confidence_page():
    topics = load_json(TOPICS_FILE)
    if request.method == "POST":
        for t in topics:
            key = f"{t['name']}_conf"
            if key in request.form:
                t["confidence"] = float(request.form[key]) / 10
        save_json(TOPICS_FILE, topics)
        return redirect(url_for("dashboard"))
    return render_template("confidence.html", topics=topics)


@app.route("/recompute")
def recompute():
    plan = update_plan(USERNAME)
    return render_template("recompute.html", plan=plan)


@app.route("/results")
def results():
    topics = load_json(TOPICS_FILE)
    mastered = [t for t in topics if t["mastery"] >= 0.7]
    weak = [t for t in topics if t["mastery"] < 0.7]
    return render_template("results.html", mastered=mastered, weak=weak)


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(TOPICS_FILE):
        save_json(TOPICS_FILE, [
            {"name": "Math", "mastery": 0.4, "confidence": 0.7, "importance": 0.9},
            {"name": "Physics", "mastery": 0.6, "confidence": 0.6, "importance": 0.8},
            {"name": "Chemistry", "mastery": 0.3, "confidence": 0.5, "importance": 0.7}
        ])
    if not os.path.exists(USERS_FILE):
        save_json(USERS_FILE, {"student": {"attention_span": 30, "missed_sessions_ratio": 0.1}})
    app.run(debug=True)
