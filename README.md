# Job Post AI - Selenium Scraper

This application is a Selenium-powered job scraper designed to fetch job listings from `freejobalert.com`, organize them in a CSV file, and use Google's Gemini GenAI to generate social media posts for each listing. It includes a Flask web interface to manage the scraping process and view results.

## Prerequisites

- **Python 3.8+**: Ensure you have Python installed.
- **Google Chrome**: Required for Selenium WebDriver.

## Installation

1.  **Clone the Repository** (if applicable):
    ```bash
    git clone <repository_url>
    cd job_post_ai/selenium_scraper
    ```

2.  **Install Dependencies**:
    It is recommended to use a virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Environment Setup**:
    Create a `.env` file in the project root directory. You can copy the example file:
    ```bash
    cp .env.example .env
    ```
    Open `.env` and add your Google API Key:
    ```
    GOOGLE_API_KEY=your_google_api_key_here
    ```

## Usage

### Running the Application

You can start the application using the provided shell script:

```bash
./run.sh
```

Or manually:

```bash
python3 app.py
```

This will start the Flask server at `http://localhost:5000`.

### Using the Dashboard

1.  **Start Scraping**: Click the "Run Scraper" button (or similar) on the dashboard to start the job fetching process. The progress will be displayed.
2.  **View Jobs**: The table displays fetched jobs.
    -   **Published**: Jobs already processed.
    -   **Generated**: Job content fetched and social media posts generated.
    -   **Unpublished**: New jobs found but content not yet generated.
3.  **Social Media Posts**: For each job, you can view and copy the generated social media content for platforms like X (Twitter), LinkedIn, Facebook, Instagram, WhatsApp, and Threads. You can also directly post to some platforms.

## Key Files

-   `app.py`: The Flask application serving the web interface and API endpoints.
-   `scraper.py`: Core logic for scraping job listings using Selenium and generating content with Google GenAI.
-   `index.html`: The frontend dashboard for interacting with the scraper.
-   `requirements.txt`: List of Python dependencies.
-   `run.sh`: Helper script to stop existing processes and start the application.
-   `latest_jobs.csv`: Data storage for job listings and their status.

## Configuration

-   **Scraping URL**: The base URL `https://www.freejobalert.com/` is configured in `scraper.py`.
-   **Model**: The AI model used for content generation is `gemma-3-27b-it` (configured in `scraper.py`).

## Troubleshooting

-   **Driver Issues**: If you encounter issues with Chrome driver, ensure your Chrome browser is up to date. `webdriver-manager` should handle the driver installation automatically.
-   **API Key Error**: Ensure `GOOGLE_API_KEY` is correctly set in your `.env` file for content generation to work.
