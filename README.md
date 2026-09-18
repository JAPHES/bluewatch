# BlueWatch

**Detecting waste before it reaches the ocean.**

BlueWatch is a maintainable Django MVP for privacy-conscious illegal-dumpsite reporting, mapping, government verification, risk prioritisation, cleanup coordination and evidence-backed closure. It is designed initially for Kenya's coastal counties and requires no dedicated hardware.

## The problem and users

Waste dumped near drains, rivers, beaches, wetlands and mangroves can threaten public health, livelihoods and marine ecosystems. BlueWatch gives:

- residents an anonymous, safe reporting and reference-tracking route;
- county administrators and waste officers a verified operational case queue;
- cleanup teams scoped assignments and evidence capture;
- environmental analysts privacy-safe maps and trends;
- the public a database-driven marine-impact dashboard.

Government accounts are administrator-created. There is no public self-registration.

## Completed MVP features

- Custom user model with System Administrator, County Administrator, Waste Management Officer, Cleanup Team Member and Environmental Analyst roles.
- Anonymous reports with Pillow-backed image validation, honeypot, consent, truthful-report confirmation, rate limiting, deliberate browser geolocation and adjustable Leaflet map marker.
- Secure human-readable references; the tracker exposes only general location, dates, status, risk and cleanup confirmation.
- Counties, wards, authorised waste sites and environmentally sensitive locations.
- Rule-based risk scoring and possible-duplicate detection in reusable Python services.
- Controlled report transitions and append-only activity history. Operational reports cannot be deleted through the normal admin.
- Cleanup teams, assignments, team-level object access, before/after evidence, disposal and recycling records, and officer verification.
- County, cleanup-team and public dashboards using database records, Leaflet/OpenStreetMap and Chart.js.
- A county-scoped earth-observation workspace where staff draw an area of interest, switch to satellite imagery, overlay resident reports, map suspected candidates, record human review decisions and promote reviewed candidates into the normal report-verification workflow.
- In-system notifications, read/unread actions, assignment-due command and future email/SMS extension points.
- Professionally configured Django admin, repeatable demo data, and automated tests.
- A deliberately unimplemented analysis service interface for future AI/earth-observation providers. No synthetic confidence scores or AI claims are shown.

## Technology

Python, Django, SQLite, HTML5, CSS3, Bootstrap 5, Bootstrap Icons, vanilla JavaScript, Leaflet/OpenStreetMap, Chart.js and Pillow. The model uses decimal latitude/longitude fields and isolated distance services, making a future PostgreSQL migration straightforward without requiring PostGIS for this MVP.

## Architecture

```text
BlueWatch/
├── bluewatch/        # settings, root URLs, central operational thresholds
├── core/             # landing/content pages, health endpoint, demo command
├── accounts/         # custom user, roles, profiles, staff account management
├── locations/        # counties, wards, authorised/sensitive places, distance service
├── reports/          # public reporting/tracking, verification, risk/duplicate services
├── earth_observation/# areas, imagery surveys, mapped candidates, provider interface
├── operations/       # cleanup teams, assignments, evidence and officer verification
├── dashboard/        # county, team and public impact dashboards
├── notifications/    # in-app notifications and due-assignment command
├── templates/        # reusable server-rendered UI
├── static/           # BlueWatch styles
├── media/            # local uploaded media (runtime)
├── manage.py
├── requirements.txt
└── .env.example
```

Services in `reports/services.py` own risk calculation, duplicate matching, authorised-site review and workflow transitions. `locations/services.py` owns Haversine distance. `earth_observation/services.py` owns polygon containment and the external-provider contract. Final verification remains a human decision. The default provider intentionally refuses automated analysis because no validated model is configured.

## Local installation

Python 3.12+ is recommended.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`; administration is at `/admin/`, public reporting at `/reports/new/`, and health status at `/health/`.

Authorised county staff can open the earth-observation workspace at `/earth-observation/`.

## Environment configuration

The project reads process variables and optionally a local `.env` file through `python-dotenv`. `.env` is ignored by Git.

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Required long random production secret |
| `DJANGO_DEBUG` | `True` only for local development |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names |
| `DJANGO_SECURE_COOKIES` | Enables secure session and CSRF cookies |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS in production |
| `DJANGO_HSTS_SECONDS` | HSTS duration after HTTPS is verified |
| `BLUEWATCH_DEMO_PASSWORD` | Optional password applied explicitly to demo users |
| `SATELLITE_TILE_URL` | Browser-visible XYZ imagery tile URL used by the review map |
| `SATELLITE_TILE_ATTRIBUTION` | Required imagery-provider attribution shown on the map |

Generate a secret with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. Never commit the result.

## Administrators and roles

Create the first system administrator with:

```bash
python manage.py createsuperuser
```

Further government users can be created in Django admin or from **Add staff** by an authorised administrator. County administrators can create officers, team members and analysts only within their county. Officers and analysts cannot create accounts. Cleanup team members see only assignments belonging to their team.

## Demo data

The command is idempotent and uses fictional names/details:

```bash
python manage.py seed_demo_data
```

Without `BLUEWATCH_DEMO_PASSWORD`, newly created demo accounts have unusable passwords. Set individual credentials explicitly:

```bash
python manage.py changepassword mombasa_officer
python manage.py changepassword cleanup_member
```

Alternatively set `BLUEWATCH_DEMO_PASSWORD` before the seed command. Demo usernames include `bw_admin`, `mombasa_county_admin`, `mombasa_officer`, `coastal_analyst` and `cleanup_member`.

Create due/overdue notifications manually (schedule this daily in production):

```bash
python manage.py notify_due_assignments
```

## Anonymous reporting and privacy

The reporter chooses **Use My Current Location** before the browser asks for location permission, or selects the map point manually. The server validates county/ward consistency, date, coordinates and actual image content; file extensions alone are not trusted. Randomised upload names avoid user-controlled paths. A hidden honeypot and cache-backed per-IP rate limit reduce basic spam.

After submission, a reference such as `BW-2607-A1B2C3` is shown once and can be copied. Tracking uses this reference—not a database ID—and never renders names, phone numbers, email, exact staff details or internal notes. Public map coordinates are rounded. Configure a shared cache and trusted proxy/IP handling before multi-instance production deployment.

## Earth observation and satellite mapping

The MVP now supports a second discovery path alongside resident reports:

1. A county administrator, officer or analyst draws a polygon area of interest.
2. The user creates an imagery survey and records the imagery source, optional capture date and catalogue/source link.
3. The review canvas displays the configured satellite basemap and overlays existing resident/officer reports.
4. Staff click within the selected boundary to map waste-like candidates. Server-side containment prevents candidates outside that area.
5. A human reviewer marks each candidate as suspected or dismissed and records a reason.
6. An authorised administrator/officer may convert a suspected candidate into a pending BlueWatch report by supplying a licensed imagery extract or field photograph and operational details.
7. The resulting report is **not verified automatically**. It enters Under Review and follows the same risk, duplicate, verification, cleanup and audit workflow as a resident report.

The default satellite layer is a browser basemap, not a dated scientific scene catalogue. Attribution must remain visible, and its licensing/terms must be reviewed for the intended deployment. The tile URL is delivered to browsers, so never embed a server secret in it. For dated Sentinel/Landsat analysis, implement a provider adapter that fetches authorised scenes server-side, preserves scene identifiers/licensing/cloud metadata, and returns candidates for human review.

## Workflow

Verification states are Pending, Verified, Rejected, Duplicate and Needs More Information. Operational states follow:

```text
Reported → Under Review → Verified → Assigned → Cleanup In Progress → Cleaned → Closed
```

Limited review/rework transitions are allowed. An unverified report cannot advance into verified cleanup states unless an authorised service call explicitly uses an override and supplies a recorded explanation. Assignment evidence must be submitted and then verified by an officer before a report becomes Cleaned. Report activity stores action, old/new values, user, time and note.

Possible duplicates remain separate reports and may be linked to a primary case; they are not auto-deleted. Proximity to an authorised facility only creates a review flag and never auto-rejects a report.

## Risk scoring

`reports.services.calculate_risk` produces a 0–100 decision-support score. It adds:

- category-configured weight (hazardous-looking categories are seeded with higher weights);
- size: 2 / 8 / 15 / 25 points;
- reporter water proximity: 35 in water, 25 under 50 m, 12 within 200 m, 2 farther away, 5 unknown;
- 18 points for each protected-radius water/marine location and 10 for a school, market or residential location;
- 4 points per nearby active report, capped at 16;
- 3 points per unresolved week, capped at 15.

The total is capped at 100. Default levels are Low below 20, Moderate from 20, High from 45 and Critical from 70. Key thresholds and matching radii live in `bluewatch/config.py`; category weights are database-configurable. The score supports human prioritisation and is **not** an official environmental determination.

## Tests and checks

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check
```

Tests cover anonymous submission, references, tracking privacy, login, role access, risk scoring, duplicate matching, valid/invalid transitions, assignment access, cleanup verification, content-based file validation, public/protected dashboards, cross-county object access and the health endpoint.

## Media and production preparation

Local development serves `media/` only when `DEBUG=True`. Production should use private object storage or a protected media service with malware scanning, retention rules and authorised access. Reverse proxies should enforce upload limits. Uploaded evidence can contain sensitive geolocation context; define retention and subject-access policies with participating counties.

Before deployment:

- use a unique secret, `DEBUG=False`, explicit hosts and HTTPS;
- enable secure cookies, HSTS only after HTTPS verification, and proxy SSL headers as appropriate;
- move SQLite to PostgreSQL, use a shared cache for rate limits, and use durable object storage;
- run `python manage.py check --deploy`, backups, dependency/security scans and accessibility testing;
- configure structured logging, error monitoring, database backups and a job scheduler;
- review permissions and privacy policy with county and data-protection stakeholders.

## Current limitations

- Risk and duplicate matching are transparent heuristics, not environmental or scientific determinations.
- Haversine checks scan relevant querysets and suit MVP volumes; they are not spatially indexed.
- Satellite imagery can be reviewed and mapped manually, but no trained detection model or automated scene-processing provider is connected.
- In-app due notifications need a scheduled daily command.
- SQLite, local cache and local media are development defaults, not multi-instance production infrastructure.
- Map tiles and CDN assets require network access; production should set an availability/CSP strategy.
- Cleanup weights are operational records, not independently audited measurements. BlueWatch does not claim real-time marine-life impact or scientifically verified waste prevented from reaching the ocean.

## Future improvements

1. Pilot with one county, validate permissions/workflows, run privacy and accessibility reviews, and measure response bottlenecks.
2. Migrate to PostgreSQL; introduce PostGIS only when data volume and spatial-query requirements justify it.
3. Add a task queue and scheduler for risk refreshes, due notifications, thumbnails and retention jobs.
4. Integrate configured email/SMS providers using notification adapters and delivery audit records.
5. Implement a versioned provider adapter around `EarthObservationProvider` and `ReportAnalysisService`. A future YOLO service should store raw suggestions separately, model/version metadata and confidence, while requiring officer confirmation. Never convert suggestions directly into final verification.
6. Connect a governed Sentinel/Landsat catalogue and processing pipeline with provenance, capture date, licensing, resolution and cloud-quality checks. It should create candidates—not public claims or automatically verified cases.
7. Add API documentation, stronger proxy-aware throttling, malware scanning, audit exports and deeper browser/accessibility tests.
