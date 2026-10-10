"""Human-in-the-loop LinkedIn job search and application assistant.

Searches the public LinkedIn Jobs pages, optionally drafts an application note
with OpenAI, then opens the job for the user to review and submit themselves.
It never logs in, answers screening questions, or clicks an Apply/Submit button.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)  # Load .env file if present, but allow environment variables to override

GEMINI_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL="gemini-3.5-flash-lite"
API_KEY = os.getenv("GOOGLE_APY_KEY")

@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    listed: str = ""
    description: str = ""
    draft: str = ""


def _plain_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = html.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s+", " ", html).strip()

def search_linkedin_with_selenium(title: str, location: str = "", limit: int = 10) -> list[Job]:
    """Fetch public job-search results using Selenium. This method is more robust
    against LinkedIn's dynamic content and rate-limiting, but requires a Selenium
    WebDriver to be set up.
    It opens linkedin and follows this steps:
        1. Opens the LinkedIn job search page with the given title and location.
        2. Iterate through the job cards
        3. Click on each job card to load the job details
        4. Extract the job description from the job details panel
        5. Store the job information in a Job dataclass and add it to the jobs list
    Returns a list of Job dataclasses with the job information and description.
    """
    jobs_cards_class = "base-card"
    job_description_class = "jobs-description__container"



def search_linkedin(title: str, location: str = "", limit: int = 10) -> list[Job]:
    """Fetch public job-search results. May return fewer results if LinkedIn
    changes or rate-limits its public page; no login or scraping evasion used.
    """
    query = urllib.parse.urlencode({"keywords": title, "location": location})
    url = f"https://www.linkedin.com/jobs/search-results/?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; JobSearchAssistant/1.0)"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")

    # LinkedIn's public results include structured job-card links. Parse only
    # cards that have a recognizable job ID URL and title/company metadata.
    cards = re.findall(
        r'(?is)<li[^>]*>.*?href="(https://www\.linkedin\.com/jobs/view/[^"]+)".*?</li>',
        html,
    )
    jobs: list[Job] = []
    seen: set[str] = set()
    for card in cards:
        href_match = re.search(r'href="([^"]+)"', card)
        if not href_match:
            continue
        job_url = urllib.parse.unquote(href_match.group(1).split("?")[0])
        if job_url in seen:
            continue
        seen.add(job_url)
        title_match = re.search(r'(?is)class="[^"]*base-search-card__title[^"]*"[^>]*>(.*?)</h3>', card)
        company_match = re.search(r'(?is)class="[^"]*base-search-card__subtitle[^"]*"[^>]*>(.*?)</h[234]>', card)
        location_match = re.search(r'(?is)class="[^"]*job-search-card__location[^"]*"[^>]*>(.*?)</span>', card)
        date_match = re.search(r'(?is)<time[^>]*>(.*?)</time>', card)
        if not title_match:
            continue
        jobs.append(Job(
            title=_plain_text(title_match.group(1)),
            company=_plain_text(company_match.group(1)) if company_match else "Unknown company",
            location=_plain_text(location_match.group(1)) if location_match else location,
            url=job_url,
            listed=_plain_text(date_match.group(1)) if date_match else "",
        ))
        if len(jobs) >= limit:
            break
    return jobs


def draft_application(job: Job, profile: str, model: str = "gpt-4.1-mini") -> str:
    """Draft a short, factual note. Do not invent qualifications."""
    if not API_KEY:
        return ""
    try:
        client = OpenAI(base_url=GEMINI_URL, api_key=API_KEY)
        response = client.responses.create(
            model=model,
            instructions=(
                "Write a concise application note (80-120 words) for the candidate. "
                "Use only facts in the candidate profile, do not invent experience, "
                "credentials, or results. If the match is unclear, say so plainly."
            ),
            input=(
                f"Candidate profile:\n{profile}\n\nJob title: {job.title}\n"
                f"Company: {job.company}\nLocation: {job.location}\n"
                f"Job description excerpt: {job.description[:5000]}"
            ),
        )
        return response.output_text.strip()
    except Exception as exc:
        print(f"Could not draft with OpenAI: {exc}", file=sys.stderr)
        return ""


def load_profile(path: Path | None) -> str:
    if not path:
        return ""
    return path.read_text(encoding="utf-8").strip()


def save_results(jobs: list[Job], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(j) for j in jobs], indent=2, ensure_ascii=False), encoding="utf-8")


def run(titles: list[str], location: str, limit: int, profile: str, model: str, output: Path) -> None:
    all_jobs: list[Job] = []
    for title in titles:
        print(f"\nSearching LinkedIn public jobs for: {title} ({location or 'any location'})")
        try:
            found = search_linkedin(title, location, limit)
        except Exception as exc:
            print(f"Search failed: {exc}\nOpen this search manually: https://www.linkedin.com/jobs/search-results/?{urllib.parse.urlencode({'keywords': title, 'location': location})}")
            continue
        if not found:
            print(f"No public results parsed. LinkedIn may have changed its page; use the manual search link. https://www.linkedin.com/jobs/search-results/?{urllib.parse.urlencode({'keywords': title, 'location': location})}")
        for job in found:
            all_jobs.append(job)
            print(f"- {job.title} — {job.company} — {job.location}\n  {job.url}")
            if profile and os.getenv("OPENAI_API_KEY"):
                job.draft = draft_application(job, profile, model)
                if job.draft:
                    print(f"  Draft (review and edit before use):\n  {job.draft}")
            answer = input("Open this job to review and apply yourself? [y/N] ").strip().lower()
            if answer == "y":
                import webbrowser
                webbrowser.open(job.url)
                print("Review the role, verify every field and screening answer, then submit on LinkedIn yourself.")
                time.sleep(1)
    save_results(all_jobs, output)
    print(f"\nSaved {len(all_jobs)} result(s) to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search LinkedIn jobs and prepare human-reviewed application drafts.")
    parser.add_argument("titles", nargs="+", help="Job titles, e.g. 'Data Engineer' 'AI Engineer'")
    parser.add_argument("--location", default="", help="Location or city")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results per title")
    parser.add_argument("--profile", type=Path, help="Markdown/text file with your truthful career profile")
    parser.add_argument("--profile_url", type=str, help="URL to your public profile (LinkedIn, GitHub, personal site) to include in the draft")
    parser.add_argument("--model", default="gemini-3.5-flash-lite", help="OpenAI model used for draft notes")
    parser.add_argument("--output", type=Path, default=Path("jobs.json"), help="Where to save search results")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    run(args.titles, args.location, args.limit, load_profile(args.profile), args.model, args.output)


if __name__ == "__main__":
    main()
