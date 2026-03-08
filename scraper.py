import os
import time
import json
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from google import genai

# Load environment variables
load_dotenv()

# Configuration
JSON_PATH = "latest_jobs.json"
BASE_URL = "https://www.freejobalert.com/"

def setup_driver():
    options = Options()
    # Required for headless execution in GitHub Actions/Linux
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Try using webdriver_manager, but fallback to system chromedriver if needed
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"WebDriverManager failed: {e}. Trying default system chromedriver.")
        driver = webdriver.Chrome(options=options)
        
    return driver

def fetch_job_links(driver):
    print(f"Fetching job links from {BASE_URL}...")
    driver.get(BASE_URL)
    time.sleep(5)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("https://www.freejobalert.com/articles"):
            links.append(a["href"])
    
    return list(set(links)) # Deduplicate

def load_jobs():
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_jobs(jobs):
    with open(JSON_PATH, "w") as f:
        json.dump(jobs, f, indent=2)

def update_json(new_links):
    jobs = load_jobs()
    existing_links = {job["href"] for job in jobs}
    
    # Determine next ID safely
    current_max_id = 0
    if jobs:
        try:
            current_max_id = max(int(job["id"]) for job in jobs)
        except ValueError:
            current_max_id = 0
    
    new_entries_count = 0
    for link in new_links:
        if link not in existing_links:
            current_max_id += 1
            new_job = {
                "id": str(current_max_id),
                "href": link,
                "status": "UNPUBLISHED",
                "website_content": {},
                "social_posts": {
                    "x": "", "ln": "", "fb": "", "ig": "", "th": "", "wp": "", "tg": ""
                }
            }
            jobs.append(new_job)
            new_entries_count += 1
            
    if new_entries_count > 0:
        save_jobs(jobs)
        print(f"Added {new_entries_count} new jobs to JSON.")
    else:
        print("No new jobs found.")
        
    return jobs

def extract_content(html):
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove unwanted tags
    for tag in soup(["script", "style", "noscript", "iframe", "footer", "aside"]):
        tag.decompose()

    # Main content container (article body)
    main_content = soup.find("div", class_="entry-content")

    if main_content:
        # Remove advertisement blocks inside article
        for ad in main_content.find_all(class_="ad_div"):
            ad.decompose()

        # Extract clean text
        content = main_content.get_text(separator="\n", strip=True)
        return content
    return ""

def generate_content_and_posts(content, client):
    if not content:
        return None
        
    prompt = """You are a content strategist and social media manager. 
    1. Extract structued data for a job board website from the raw text.
    2. Generate engaging social media posts.

    Raw Job Description:
    {content}
    
    Output a valid JSON object with the following structure. 
    IMPORTANT: 
    - website_content.markdown_content MUST be in Markdown.
    - social_posts content MUST be Pure Plain Text. Do NOT use markdown.
    - If an 'actual_link' is found, you MUST include it in every social_post (e.g., "Apply: [Link]" or "More info: [Link]").
    
    {{
      "website_content": {{
        "title": "Concise Job Title",
        "markdown_content": "Full job description formatted in clean Markdown. Include key details like formatting dates, fees, age limits, etc. Do NOT include the official link here.",
        "actual_link": "The official application or notification URL found in the text. If not found, leave empty string.",
        "action": "One (or two words) call to action button text, e.g., 'Apply Now', 'View Notification', 'Check Result'"
      }},
      "social_posts": {{
        "x": "Twitter post (max 200 chars) with hashtags and the link. Plain text only.",
        "ln": "LinkedIn post (professional, bullet points using hyphens or emojis). Include the link. Plain text only.",
        "fb": "Facebook post (engaging). Include the link. Plain text only.",
        "ig": "Instagram caption (visual, hashtags). Include the link (for 'link in bio' context). Plain text only.",
        "wp": "WhatsApp message (short, direct) with the link. Plain text only.",
        "th": "Threads post (conversational) with the link. Plain text only.",
        "tg": "Telegram message (broadcast style, concise). Include the link. Plain text only."
      }}
    }}
    """
    
    try:
        response = client.models.generate_content(
            model='gemma-3-27b-it', # Using a reliable model
            contents=prompt.format(content=content),
        )
        return response.text
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

def update_job_status(job_id, new_status):
    jobs = load_jobs()
    updated = False
    for job in jobs:
        if job["id"] == str(job_id):
            job["status"] = new_status
            updated = True
            break
    if updated:
        save_jobs(jobs)
        return True
    return False

def update_job_link(job_id, new_link):
    jobs = load_jobs()
    updated = False
    for job in jobs:
        if job["id"] == str(job_id):
            if "website_content" not in job:
                job["website_content"] = {}
            job["website_content"]["actual_link"] = new_link
            updated = True
            break
    if updated:
        save_jobs(jobs)
        return True
    return False

def get_jobs_json():
    return load_jobs()

def process_jobs(progress_callback=None):
    driver = setup_driver()
    RATE_LIMIT_DELAY = 2.5 # Seconds
    MAX_RETRIES = 3
    
    try:
        # 1. Fetch and update links
        if progress_callback: progress_callback("Fetching job links...")
        links = fetch_job_links(driver)
        jobs = update_json(links)
        
        # 2. Identify jobs to process (UNPUBLISHED or GENERATED but incomplete)
        # For simplicity, we process UNPUBLISHED. If you want to re-process incomplete ones, add logic.
        jobs_to_process = [job for job in jobs if job["status"] == "UNPUBLISHED"]
        
        total_jobs = len(jobs_to_process)
        if total_jobs == 0:
            print("No new jobs to process.")
            if progress_callback: progress_callback("No new jobs to process.")
            return

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("GOOGLE_API_KEY not found. Skipping content generation.")
            client = None
        else:
            client = genai.Client(api_key=api_key)

        for i, job in enumerate(jobs_to_process):
            url = job["href"]
            job_id = job["id"]
            msg = f"Processing {i+1}/{total_jobs}: {url}"
            print(msg)
            if progress_callback: progress_callback(msg)
            
            time.sleep(RATE_LIMIT_DELAY)
            
            try:
                driver.get(url)
                time.sleep(3) 
                content = extract_content(driver.page_source)
                
                if content:
                    generated_data = None
                    if client:
                        for attempt in range(MAX_RETRIES):
                            try:
                                json_str = generate_content_and_posts(content, client)
                                if json_str:
                                    import json
                                    clean_json = json_str.replace("```json", "").replace("```", "").strip()
                                    generated_data = json.loads(clean_json)
                                    break
                                else:
                                    print(f"Attempt {attempt+1}: No response.")
                            except json.JSONDecodeError as e:
                                print(f"Attempt {attempt+1}: JSON Parse Error: {e}")
                            except Exception as e:
                                print(f"Attempt {attempt+1}: API Error: {e}")
                            time.sleep(2)
                    
                    if generated_data:
                        print(f"Generated Data for {url}")
                        # Update the job object in memory
                        # We need to find the job in the main 'jobs' list to update it persistently
                        # (since 'job' loop var might be a copy or we want to save full list)
                        for mutable_job in jobs:
                            if mutable_job["id"] == job_id:
                                mutable_job["website_content"] = generated_data.get("website_content", {})
                                mutable_job["social_posts"] = generated_data.get("social_posts", {})
                                mutable_job["status"] = "GENERATED"
                                break
                        
                        save_jobs(jobs)
                    else:
                        print(f"Failed to generate data for {url}")
                else:
                    print("No content extracted.")
            except Exception as e:
                print(f"Error processing {url}: {e}")
        
        if progress_callback: progress_callback("Processing complete.")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    process_jobs()

