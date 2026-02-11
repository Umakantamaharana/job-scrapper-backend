import os
import time
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
CSV_PATH = "latest_jobs.csv"
BASE_URL = "https://www.freejobalert.com/"

def setup_driver():
    options = Options()
    # options.add_argument("--start-maximized") # Not needed for headless
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new") # Uncomment if headless desired
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
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

def update_csv(new_links):
    columns = ["id", "href", "status", "x", "ln", "fb", "ig", "th", "wp"]
    
    # Initialize df with explicit types to avoid warnings
    df = pd.DataFrame(columns=columns)
    
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
        except pd.errors.EmptyDataError:
             pass
    
    # Standardize columns
    for col in columns:
        if col not in df.columns:
            df[col] = ""
            
    existing_links = set(df["href"].tolist())
    
    new_entries = []
    # Determine next ID safely
    if not df.empty and "id" in df.columns and pd.notna(df["id"].max()):
        try:
            current_max_id = int(df["id"].max())
        except:
            current_max_id = 0
    else:
        current_max_id = 0
    
    for link in new_links:
        if link not in existing_links:
            current_max_id += 1
            new_entries.append({
                "id": current_max_id,
                "href": link,
                "status": "UNPUBLISHED",
                "x": "", "ln": "", "fb": "", "ig": "", "th": "", "wp": ""
            })
            
    if new_entries:
        new_df = pd.DataFrame(new_entries)
        combined_df = pd.concat([df, new_df], ignore_index=True)
        combined_df.to_csv(CSV_PATH, index=False)
        print(f"Added {len(new_entries)} new jobs to CSV.")
        return combined_df
    else:
        print("No new jobs found.")
        return df

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

def generate_social_post(content, client):
    if not content:
        return None
        
    prompt = """You are a social media manager. Generate engaging posts for the following platforms based on the job description provided.
    
    Platforms:
    1. X (Twitter): Max 200 characters, include hashtags.
    2. LinkedIn: Professional tone, bullet points for key details, include hashtags.
    3. Facebook: Engaging, slightly longer than X, include hashtags.
    4. Instagram: Visually descriptive caption, many hashtags.
    5. WhatsApp: Short, direct, clear call to action.
    6. Threads: Similar to X but can be slightly more conversational.
    
    Job Description:
    {content}
    
    Output valid JSON only. Do not include markdown formatting like ```json ... ```. Just the raw JSON object.
    {{
        "x": "...",
        "ln": "...",
        "fb": "...",
        "ig": "...",
        "wp": "...",
        "th": "..."
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

def generate_index_html(df):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Job Scraper Output</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }
            h1 { color: #2c3e50; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); background: white; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; vertical-align: top; }
            th { background-color: #34495e; color: white; position: sticky; top: 0; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
            .status-published { color: #27ae60; font-weight: bold; }
            .status-unpublished { color: #d35400; font-weight: bold; }
            .status-generated { color: #2980b9; font-weight: bold; }
            .post-content { max-height: 100px; overflow-y: auto; font-size: 0.9em; margin-bottom: 8px; white-space: pre-wrap; }
            .action-buttons { display: flex; gap: 5px; flex-wrap: wrap; }
            .btn { border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; display: inline-flex; align-items: center; gap: 4px; text-decoration: none; color: white; }
            .btn-copy { background-color: #7f8c8d; }
            .btn-copy:hover { background-color: #626567; }
            .btn-post { background-color: #2980b9; }
            .btn-post:hover { background-color: #2471a3; }
            .platform-cell { min-width: 200px; }
        </style>
        <script>
            function copyToClipboard(text) {
                navigator.clipboard.writeText(text).then(() => {
                    alert('Copied to clipboard!');
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                });
            }
        </script>
    </head>
    <body>
        <h1>Job Scraper Dashboard</h1>
        <p>Last updated: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """</p>
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">ID</th>
                    <th style="width: 80px;">Link</th>
                    <th style="width: 100px;">Status</th>
                    <th>X (Twitter)</th>
                    <th>LinkedIn</th>
                    <th>Facebook</th>
                    <th>Instagram</th>
                    <th>WhatsApp</th>
                    <th>Threads</th>
                </tr>
            </thead>
            <tbody>
    """
    
    import urllib.parse
    
    for _, row in df.iterrows():
        if row["status"] == "PUBLISHED":
            status_class = "status-published"
        elif row["status"] == "GENERATED":
            status_class = "status-generated"
        else:
            status_class = "status-unpublished"
            
        html_content += f"""
                <tr>
                    <td>{row['id']}</td>
                    <td><a href="{row['href']}" target="_blank">View Job</a></td>
                    <td class="{status_class}">{row['status']}</td>
        """
        
        platforms = [
            ('x', 'https://twitter.com/intent/tweet?text='),
            ('ln', 'https://www.linkedin.com/feed/?shareActive=true&text='), # LinkedIn text sharing is tricky via URL, often just URL sharing
            ('fb', 'https://www.facebook.com/sharer/sharer.php?u=' + row['href'] + '&quote='),
            ('ig', ''), # No direct web intent for IG post
            ('wp', 'https://wa.me/?text='),
            ('th', 'https://www.threads.net/intent/post?text=')
        ]
        
        for platform_key, intent_base in platforms:
            content = str(row.get(platform_key, ''))
            if content == 'nan': content = ''
            
            encoded_content = urllib.parse.quote(content)
            encoded_url = urllib.parse.quote(row['href'])
            
            post_btn_html = ""
            if intent_base and content:
                 # Special handling for FB which prefers URL param
                if platform_key == 'fb':
                     final_url = intent_base + encoded_content
                elif platform_key == 'ln':
                     # LinkedIn text + url often works better in simple text param for some clients, but sharing URL is standard.
                     # We'll try passing text.
                     final_url = intent_base + encoded_content
                else:
                     final_url = intent_base + encoded_content
                
                post_btn_html = f'<a href="{final_url}" target="_blank" class="btn btn-post"><i class="fas fa-share-square"></i> Post</a>'
            
            copy_btn_html = ""
            if content:
                # Escape single quotes for JS string
                js_safe_content = content.replace("'", "\\'").replace("\n", "\\n")
                copy_btn_html = f'<button onclick="copyToClipboard(\'{js_safe_content}\')" class="btn btn-copy"><i class="fas fa-copy"></i> Copy</button>'

            html_content += f"""
                    <td class="platform-cell">
                        <div class="post-content">{content[:200] + '...' if len(content) > 200 else content}</div>
                        <div class="action-buttons">
                            {copy_btn_html}
                            {post_btn_html}
                        </div>
                    </td>
            """
            
        html_content += "</tr>"
        
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    with open("index.html", "w") as f:
        f.write(html_content)
    print("Updated index.html")

def update_job_status(job_id, new_status):
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
            # Ensure ID is treated as int/string consistently
            df["id"] = df["id"].astype(str) 
            job_id = str(job_id)
            
            if job_id in df["id"].values:
                idx = df[df["id"] == job_id].index[0]
                df.at[idx, "status"] = new_status
                df.to_csv(CSV_PATH, index=False)
                return True
        except Exception as e:
            print(f"Error updating status: {e}")
    return False

def get_jobs_json():
    columns = ["id", "href", "status", "x", "ln", "fb", "ig", "th", "wp"]
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
            # Check for missing columns and add them if necessary
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            return df.fillna("").to_dict(orient="records")
        except Exception:
            return []
    return []

def process_jobs(progress_callback=None):
    driver = setup_driver()
    RATE_LIMIT_DELAY = 2.5 # Seconds, ensures < 30 RPM
    MAX_RETRIES = 3
    
    try:
        # 1. Fetch and update links
        if progress_callback: progress_callback("Fetching job links...")
        links = fetch_job_links(driver)
        df = update_csv(links)
        
        # 2. Process unpublished jobs OR generated jobs with missing content
        # We process UNPUBLISHED, or GENERATED ones that might have failed (empty X post)
        mask = (df["status"] == "UNPUBLISHED") | \
               ((df["status"] == "GENERATED") & (df["x"].isnull() | (df["x"] == "")))
        indices_to_process = df[mask].index
        
        total_jobs = len(indices_to_process)
        if total_jobs == 0:
            print("No new or incomplete jobs to process.")
            if progress_callback: progress_callback("No new jobs to process.")
            return

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("GOOGLE_API_KEY not found. Skipping social media post generation.")
            client = None
        else:
            client = genai.Client(api_key=api_key)

        for i, idx in enumerate(indices_to_process):
            row = df.loc[idx]
            url = row["href"]
            msg = f"Processing {i+1}/{total_jobs}: {url}"
            print(msg)
            if progress_callback: progress_callback(msg)
            
            # Enforce Rate Limit
            time.sleep(RATE_LIMIT_DELAY)
            
            try:
                driver.get(url)
                time.sleep(3) # Wait for page load
                content = extract_content(driver.page_source)
                
                if content:
                    posts = None
                    if client:
                        # Retry logic for API call and JSON parsing
                        for attempt in range(MAX_RETRIES):
                            try:
                                posts_json_str = generate_social_post(content, client)
                                if posts_json_str:
                                    import json
                                    # Clean up potential markdown code blocks
                                    clean_json = posts_json_str.replace("```json", "").replace("```", "").strip()
                                    posts = json.loads(clean_json)
                                    break # Success, exit retry loop
                                else:
                                    print(f"Attempt {attempt+1}: No response from API.")
                            except json.JSONDecodeError as e:
                                print(f"Attempt {attempt+1}: JSON Parse Error for {url}: {e}")
                            except Exception as e:
                                print(f"Attempt {attempt+1}: API Error for {url}: {e}")
                            
                            time.sleep(2) # Backoff before retry
                    
                    if posts:
                        print(f"Generated Posts for {url}")
                        df.at[idx, "x"] = posts.get("x", "")
                        df.at[idx, "ln"] = posts.get("ln", "")
                        df.at[idx, "fb"] = posts.get("fb", "")
                        df.at[idx, "ig"] = posts.get("ig", "")
                        df.at[idx, "wp"] = posts.get("wp", "")
                        df.at[idx, "th"] = posts.get("th", "")
                        # Mark as GENERATED instead of PUBLISHED so user sees it needs action
                        df.at[idx, "status"] = "GENERATED"
                    else:
                        print(f"Failed to generate posts for {url} after {MAX_RETRIES} attempts.")
                    
                    # Save immediately to avoid data loss
                    df.to_csv(CSV_PATH, index=False)
                else:
                    print("No content extracted.")
            except Exception as e:
                print(f"Error processing {url}: {e}")
        
        if progress_callback: progress_callback("Processing complete.")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    process_jobs()
