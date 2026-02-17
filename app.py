import os
import threading
from flask import Flask, render_template, jsonify, request
from scraper import process_jobs, get_jobs_json, update_job_status, update_job_link, JSON_PATH

app = Flask(__name__, template_folder=".")

# Global state for scraper progress
scraper_state = {
    "is_running": False,
    "progress": "Idle"
}

def scraper_progress_callback(message):
    scraper_state["progress"] = message

def run_scraper_thread():
    global scraper_state
    scraper_state["is_running"] = True
    scraper_state["progress"] = "Starting..."
    try:
        process_jobs(progress_callback=scraper_progress_callback)
    except Exception as e:
        scraper_state["progress"] = f"Error: {str(e)}"
    finally:
        scraper_state["is_running"] = False
        scraper_state["progress"] = "Idle"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/jobs")
def get_jobs():
    jobs = get_jobs_json()
    return jsonify(jobs)

@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    if scraper_state["is_running"]:
        return jsonify({"status": "error", "message": "Scraper already running"}), 400
    
    thread = threading.Thread(target=run_scraper_thread)
    thread.start()
    return jsonify({"status": "success", "message": "Scraper started"})

@app.route("/api/progress")
def get_progress():
    return jsonify(scraper_state)

@app.route("/api/update_status", methods=["POST"])
def update_status():
    data = request.json
    job_id = data.get("id")
    new_status = data.get("status")
    
    if update_job_status(job_id, new_status):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Failed to update status"}), 500

@app.route("/api/update_link", methods=["POST"])
def update_link():
    data = request.json
    job_id = data.get("id")
    new_link = data.get("link")
    
    if update_job_link(job_id, new_link):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Failed to update link"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
