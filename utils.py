from bs4 import BeautifulSoup
import requests
import json
import logging
import os
from openai import OpenAI

logging.basicConfig(level=logging.DEBUG)

def scrape_jobs(preferences):
    """
    Scrape jobs from Oracle Cloud portal based on preferences
    """
    base_url = "https://ecsr.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/requisitions"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        # Find all job listings
        job_listings = soup.find_all('div', class_='joblist-wrapper')
        logging.debug(f"Found {len(job_listings)} potential job listings")
        
        for job in job_listings:
            try:
                # Extract job details
                title_elem = job.find('h3', class_='joblist-title')
                location_elem = job.find('span', class_='joblist-location')
                desc_elem = job.find('div', class_='joblist-description')
                link_elem = job.find('a', class_='joblist-link')
                
                if title_elem:  # Only process if we found a title
                    job_data = {
                        'title': title_elem.text.strip(),
                        'company': 'Oracle',
                        'location': location_elem.text.strip() if location_elem else 'Location not specified',
                        'description': desc_elem.text.strip() if desc_elem else 'No description available',
                        'url': f"{base_url}/{link_elem['href']}" if link_elem and 'href' in link_elem.attrs else base_url
                    }
                    jobs.append(job_data)
                    logging.debug(f"Successfully parsed job: {job_data['title']}")
            except Exception as e:
                logging.error(f"Error parsing individual job listing: {str(e)}")
                continue
                
        # If no jobs found through primary selectors, try alternate selectors
        if not jobs:
            logging.debug("No jobs found with primary selectors, trying alternate selectors")
            alt_listings = soup.find_all('div', class_='job-posting')
            
            for job in alt_listings:
                try:
                    title = job.find('div', class_='posting-title').text.strip()
                    location = job.find('div', class_='posting-location').text.strip()
                    description = job.find('div', class_='posting-description').text.strip()
                    url = job.find('a')['href'] if job.find('a') else base_url
                    
                    jobs.append({
                        'title': title,
                        'company': 'Oracle',
                        'location': location,
                        'description': description,
                        'url': url if url.startswith('http') else f"{base_url}/{url.lstrip('/')}"
                    })
                except Exception as e:
                    logging.error(f"Error parsing alternate job listing: {str(e)}")
                    continue
        
        logging.info(f"Successfully scraped {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        logging.error(f"Error scraping jobs: {e}")
        return []

def format_job_match(job, analysis):
    """
    Use OpenAI to analyze job fit based on user preferences
    """
    try:
        # Create a prompt for job analysis
        prompt = f"""
        Based on the candidate's preferences:
        {analysis}
        
        Analyze this job posting and provide a match score and reasoning:
        Job Title: {job.get('title')}
        Description: {job.get('description')}
        Location: {job.get('location')}
        
        Return response in JSON format with fields:
        - match_score (0-100)
        - reasoning (brief explanation)
        """
        
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "match_score": result.get("match_score", 0),
            "reasoning": result.get("reasoning", "No analysis available"),
            "url": job.get("url")
        }
        
    except Exception as e:
        logging.error(f"Error analyzing job match: {e}")
        return {
            "title": job.get("title"),
            "company": job.get("company"),
            "match_score": 0,
            "url": job.get("url"),
            "reasoning": "Error analyzing job match"
        }
