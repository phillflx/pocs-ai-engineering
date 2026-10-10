# LinkedIn Jobs Application Assistant

A small Python CLI that searches LinkedIn's public job listings by title,
prints matching jobs, optionally drafts an application note with OpenAI, and
lets you open each listing for your own review.

## Setup

From the repository root, install the existing project dependencies (including
`openai`). Set `OPENAI_API_KEY` in your environment only if you want draft
notes. Do not put a resume, API key, or other private data in this directory's
committed files.

Create a private Markdown profile file outside version control. Include only
facts you want used in application drafts, for example:

```markdown
## Experience
- Data Engineer at Example Co (2022–2025): built Python and SQL pipelines.

## Skills
- Python, SQL, dbt, Airflow

## Education
- B.S. in Computer Science
```

## Run

```powershell
python concepts/jobs-applier/agent.py "Data Engineer" "Software Engineer" "AI Engineer" --location "São Paulo, Brazil" --profile C:\private\career-profile.md --output jobs.json
```
or
```powershell
python concepts/jobs-applier/agent.py "Data Engineer" "Software Engineer" "AI Engineer" --location "São Paulo, Brazil" --profile_url "https://www.linkedin.com/in/philipefelix/" --output jobs.json
```

Without a profile and `OPENAI_API_KEY`, it still searches and saves listings,
but skips the AI draft. Search results are also printed as direct job links.
For each job, answer `y` to open it in your browser and review it manually.

## Application and site limits

This proof of concept searches the public LinkedIn Jobs page. LinkedIn can
change its markup, restrict requests, or return no parseable results; in that
case the program prints a manual search link. It does not sign in, automate
Easy Apply, complete screening questions, upload a resume, or submit an
application. Review the role and every application field yourself, and submit
through LinkedIn only after confirming the information is accurate.

AI-generated text is a draft, not a claim of fact. The model is instructed to
use only the supplied profile, but you must verify and edit every draft before
using it. Search results are written to the selected JSON output path.
