

# LD76 Domain Finder

LD76 Domain Finder is a defensive web-research and domain-analysis tool designed to discover active `.top` domains and identify websites that may contain investment, HYIP, high-return, deposit/withdrawal, referral, payment, or similar financial-risk signals.

The project is designed for security research, monitoring, investigation, and risk analysis.

> **Disclaimer:** This project is intended for defensive research and analysis. It does not provide, operate, or promote investment schemes, financial fraud, or deceptive services.

---

## Project Goals

The main goals of LD76 Domain Finder are:

- Discover active `.top` domains.
- Check whether discovered domains are reachable.
- Extract useful website content.
- Detect suspicious financial/investment signals using Python.
- Score domains before expensive AI analysis.
- Send only strong candidates to Gemini.
- Reduce unnecessary Gemini API usage.
- Store evidence and scan history.
- Detect content changes and avoid duplicate AI analysis.
- Provide structured results that can later be consumed by an Android application.

---

## Architecture

The current scanner follows this pipeline:

```text
Domain Discovery
       |
       v
Normalize + Deduplicate
       |
       v
HTTP / HTTPS Check
       |
       v
HTML Extraction
       |
       v
Python Signal Detection
       |
       v
Weighted Python Score
       |
       +---- Weak Candidate ----> Store / History
       |
       +---- Strong Candidate ---> Gemini Queue
                                      |
                                      v
                              Gemini Analysis
                                      |
                                      v
                              Structured Result
                                      |
                                      v
                           Results + Scan History

The most important design principle is:

> Python does the maximum amount of filtering. Gemini does only the minimum amount of expensive semantic analysis.




---

Why Python Comes First

Sending every discovered domain to Gemini would be:

Expensive

Slow

Rate-limit heavy

Unnecessary

More difficult to scale


Instead, Python performs deterministic analysis first.

Python checks:

Investment terminology

Profit/return claims

Deposit and withdrawal language

Payment methods

Referral/network language

Cryptocurrency references

VIP/membership language

Communication/support channels

Buttons and forms

Headings

Meta description

Page title

Visible website content


Only domains with sufficiently strong Python scores are placed into the Gemini queue.


---

Signal Categories

The scanner currently uses weighted signal groups including:

Investment

Examples:

investment

invest

investor

portfolio

funding

financial plan


Profit / HYIP

Examples:

profit

daily return

weekly return

ROI

high return

passive income

earn


Deposit / Withdrawal

Examples:

deposit

withdraw

withdrawal

minimum deposit

payout

cash out


Referral / Network

Examples:

referral

invite

affiliate

commission

team

downline

network


Crypto / Payment

Examples:

Bitcoin

USDT

cryptocurrency

wallet

payment

crypto deposit


Pakistani Payment Signals

The scanner can detect payment-related signals such as:

JazzCash

Easypaisa

bank transfer

local payment terminology


VIP / Membership

Examples:

VIP

premium

membership

upgrade

package

plan


Communication / Social

Examples:

Telegram

WhatsApp

Discord

support

contact

customer service



---

False Positive Protection

Keyword matching alone is not enough.

The scanner therefore considers negative context such as:

"not an investment"

"do not invest"

"not financial advice"

"avoid investment scams"

"educational purposes only"


These patterns can reduce misleading scores when a website is discussing scams or investments without actually offering an investment service.


---

Website Content Extraction

The scanner prioritizes useful content instead of blindly sending the entire HTML page to Gemini.

Important extraction targets include:

1. Page title


2. Meta description


3. Headings


4. Buttons


5. Forms


6. Pricing/package sections


7. Investment sections


8. Payment information


9. FAQ content


10. Support/contact information


11. Visible body text



This keeps analysis focused and reduces unnecessary payload size.


---

Python Scoring

Each detected signal contributes a weighted score.

Additional combination bonuses can increase the score when multiple related categories appear together.

For example:

Investment + Profit + Deposit

is more significant than a page containing only:

Investment

The final Python score determines whether the domain is strong enough for Gemini analysis.


---

Gemini Analysis

Gemini is used only for strong candidates.

The current system supports:

Gemini request limits

Daily usage limits

Queue-based processing

Controlled concurrency

Request delays

Retry handling

Structured JSON responses

Content-hash caching

Duplicate-analysis prevention


The Gemini model can classify a candidate and provide structured information such as:

Classification

Confidence

Investment signals

Payment methods

Profit claims

Deposit/withdrawal indicators

Referral indicators

Reasoning summary


Gemini is not trusted as the first-stage filter.


---

Gemini Request Protection

The scanner supports environment variables for controlling Gemini usage:

GEMINI_DAILY_LIMIT
GEMINI_MAX_REQUESTS
GEMINI_CONCURRENCY
GEMINI_REQUEST_DELAY
PYTHON_GEMINI_THRESHOLD

The effective request budget is controlled conservatively so the scanner does not unnecessarily consume the Gemini quota.


---

Gemini Cache

Gemini analysis is cached in:

data/gemini_cache.json

The scanner calculates a SHA-256 content hash.

If the same content has already been analyzed, the previous Gemini analysis can be reused instead of sending the same content again.

This is especially useful when:

A domain is scanned repeatedly.

Website content has not changed.

Multiple domains serve identical content.



---

Domain History

The scanner maintains:

data/scan_history.json

History records include fields such as:

domain
first_seen
last_seen
last_scan
python_score
gemini_score
gemini_analyzed
content_changed
content_hash

This allows future versions of the project to track domain activity over time.


---

Current Result Storage

The main result file is:

data/results.json

It contains the stronger candidates selected by the scanner.

The development system currently uses JSON files so the scanner can work without requiring a database.

A production version can later migrate this data to a proper database.


---

Project Structure

LD76_Domain_finder/
│
├── .github/
│   └── workflows/
│       └── scan.yml
│
├── data/
│   ├── results.json
│   ├── scan_history.json
│   └── gemini_cache.json
│
├── scanner/
│   ├── scanner.py
│   ├── gemini_analyzer.py
│   ├── gemini_queue.py
│   └── requirements.txt
│
└── README.md


---

Main Components

scanner/scanner.py

Main scanning engine.

Responsible for:

Domain discovery

HTTP requests

HTML extraction

Signal detection

Python scoring

Content hashing

Result generation

History management

Gemini queue integration


scanner/gemini_analyzer.py

Responsible for:

Gemini API communication

Request limits

Cache management

Evidence preparation

Prompt construction

JSON parsing

Gemini result normalization


scanner/gemini_queue.py

Responsible for:

Selecting Gemini candidates

Queue management

Controlled concurrency

Processing candidates

Merging Gemini results


data/results.json

Stores important scanner results.

data/scan_history.json

Stores scan history and domain state.

data/gemini_cache.json

Stores reusable Gemini analyses.


---

Configuration

The scanner supports environment-based configuration.

Important variables include:

DOMAIN_TLD
DISCOVERY_LIMIT
REQUEST_TIMEOUT
CRTSH_TIMEOUT
MAX_RESPONSE_BYTES
PYTHON_MIN_SCORE
PYTHON_RESULT_SCORE
PYTHON_GEMINI_THRESHOLD
SCAN_DELAY
SCANNER_USER_AGENT

ENABLE_GEMINI
GEMINI_MODEL
GEMINI_DAILY_LIMIT
GEMINI_MAX_REQUESTS
GEMINI_CONCURRENCY
GEMINI_REQUEST_DELAY
GEMINI_MAX_EVIDENCE_ITEMS
GEMINI_MAX_EVIDENCE_CHARS
GEMINI_FORCE_REANALYSIS

Example:

DOMAIN_TLD=top
DISCOVERY_LIMIT=200
REQUEST_TIMEOUT=8
PYTHON_RESULT_SCORE=80
PYTHON_GEMINI_THRESHOLD=80
GEMINI_MODEL=gemini-2.5-flash
GEMINI_DAILY_LIMIT=50
GEMINI_MAX_REQUESTS=10
GEMINI_CONCURRENCY=2


---

Gemini API Key

The Gemini API key must never be hard-coded into the repository.

For GitHub Actions, configure it as a repository secret:

GEMINI_API_KEY

The scanner reads the key from the environment.

Important

Never put the Gemini API key inside an Android APK.

The future Android architecture will communicate with a secure backend, and the backend will communicate with Gemini.


---

GitHub Actions

The repository includes:

.github/workflows/scan.yml

The workflow can run the scanner automatically on a schedule or manually through GitHub Actions.

The workflow:

1. Checks out the repository.


2. Installs Python.


3. Installs scanner dependencies.


4. Runs the scanner.


5. Validates generated JSON files.


6. Commits changed scanner data.


7. Pushes the updated data back to the repository.




---

Local Installation

Clone the repository:

git clone https://github.com/lagenddesi/LD76_Domain_finder.git
cd LD76_Domain_finder

Install dependencies:

pip install -r scanner/requirements.txt

Run the scanner:

python scanner/scanner.py

For Gemini analysis, configure:

GEMINI_API_KEY

as an environment variable.


---

Security Principles

LD76 Domain Finder follows these principles:

Never expose API keys in client applications.

Do not send every domain to Gemini.

Do not trust keyword matching alone.

Preserve evidence for important classifications.

Handle failed websites without crashing the scanner.

Limit HTTP response sizes.

Respect API quotas.

Cache reusable analysis.

Detect content changes.

Keep the Android client separate from Gemini credentials.

Use a secure backend before exposing scanning functionality publicly.



---

Future Architecture

The long-term architecture is:

Android App
     |
     | HTTPS + Authentication
     v
Secure Backend API
     |
     v
Python Scanner / Worker
     |
     +---- Domain Discovery
     |
     +---- Python Analysis
     |
     +---- Database
     |
     v
Gemini API

The Android application should never communicate directly with Gemini using a private server API key.


---

Planned Backend API

The following endpoints are part of the planned architecture:

POST /api/scan/start
GET  /api/scan/status
GET  /api/results
GET  /api/results/:domain
POST /api/rescan/:domain
GET  /api/history
GET  /api/stats

These endpoints are planned for the future backend phase and are not claimed to be implemented by the current scanner.


---

Planned Android App

The Android application will eventually provide:

Home

Scanner status

Last scan

Domain statistics

High-risk candidate count


Live Scan

Current scanner status

Domains discovered

Domains checked

Candidates found

Gemini queue status


Results

Domain

Python score

Gemini score

Classification

Risk indicators

Payment signals


Details

Matched keywords

Evidence

Website metadata

Profit claims

Payment methods

Deposit/withdrawal indicators

Referral signals

Gemini analysis


Filters

Possible filters:

All
High Score
Investment
HYIP / Profit
Deposit / Withdrawal
Referral
Crypto
Payment
Recently Changed
Gemini Analyzed


---

Development Roadmap

Phase 1 — Scanner Engine

Domain discovery

HTTP checking

Content extraction

Python signal detection

Weighted scoring

Evidence collection

History tracking


Phase 2 — Gemini

Gemini analyzer

Queue system

Request limits

Content caching

Structured JSON analysis


Phase 3 — Backend

Secure API

Authentication

Database

Worker system

Rate limiting

Server-side Gemini key


Phase 4 — Android

Native Android UI

Authentication

Scan controls

Live status

Results

Domain details

Filters

History


Phase 5 — Testing

Scanner unit tests

False-positive tests

Gemini JSON tests

API security tests

Android UI tests

Load testing


Phase 6 — APK

Release build

Secure configuration

Production API

Error handling

Performance optimization


Phase 7 — Deployment

Production worker

Database

Backend hosting

Monitoring

Logs

Scheduled scanning



---

Golden Rules

These rules define the core architecture of LD76 Domain Finder:

1. Gemini must not analyze every domain.


2. Python performs the maximum possible filtering.


3. Only strong candidates enter the Gemini queue.


4. The same unchanged content should not be analyzed repeatedly.


5. Evidence must be preserved.


6. Failed websites must not crash the scanner.


7. API keys must never be included in the APK.


8. Gemini access should eventually be controlled by the backend.


9. Scanner data should eventually move from JSON files to a production database.


10. The Android application should be a proper client, not simply a WebView wrapper.




---

Current Status

The current repository contains the first working scanner architecture with:

Domain discovery

Website scanning

Python-based signal detection

Weighted scoring

Evidence extraction

Scan history

Gemini analysis

Gemini queue

Gemini caching

GitHub Actions automation


The next major development stage is the secure backend and Android application.


---

License

This project is intended for defensive security research and website analysis.

Use responsibly and only against systems and data that you are authorized to research.

