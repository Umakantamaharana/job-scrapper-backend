import os
import threading
import base64
from flask import Flask, render_template, jsonify, request, send_from_directory
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

@app.route("/job_images/<path:filename>")
def serve_image(filename):
    return send_from_directory("public/job_images", filename)

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

@app.route("/api/upload_image", methods=["POST"])
def upload_image():
    data = request.json
    job_id = data.get("id")
    image_data = data.get("image")  # base64 string
    
    if not job_id or not image_data:
        return jsonify({"status": "error", "message": "Missing job_id or image data"}), 400
        
    try:
        # Create directory if it doesn't exist
        os.makedirs("public/job_images", exist_ok=True)
        
        # Remove data URI header if present
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
            
        img_bytes = base64.b64decode(image_data)
        file_path = f"public/job_images/{job_id}.png"
        
        with open(file_path, "wb") as f:
            f.write(img_bytes)
            
        # Update JSON data
        jobs = get_jobs_json()
        for idx, job in enumerate(jobs):
            if str(job["id"]) == str(job_id):
                jobs[idx]["image_url"] = f"/job_images/{job_id}.png"
                break
        else:
            return jsonify({"status": "error", "message": "Job ID not found"}), 404
            
        # Assuming save_jobs_data exists or we write manually
        import json
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=4)
            
        return jsonify({"status": "success", "image_url": f"/job_images/{job_id}.png"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/delete_image", methods=["POST"])
def delete_image():
    data = request.json
    job_id = data.get("id")
    
    if not job_id:
        return jsonify({"status": "error", "message": "Missing job_id"}), 400
        
    try:
        file_path = f"public/job_images/{job_id}.png"
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Update JSON data
        jobs = get_jobs_json()
        for idx, job in enumerate(jobs):
            if str(job["id"]) == str(job_id):
                if "image_url" in jobs[idx]:
                    del jobs[idx]["image_url"]
                break
                
        import json
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=4)
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
