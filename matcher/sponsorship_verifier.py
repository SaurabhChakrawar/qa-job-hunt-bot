"""Evidence-based visa-sponsorship classification for job listings."""

import re


# A listing is sponsored only when it makes a positive statement. Search terms,
# location, and a generic "visa" mention are not evidence.
POSITIVE_PATTERNS = [
    r"visa sponsorship (?:is )?(?:available|provided|offered)",
    r"(?:we|the company|employer) (?:offer|provide) visa sponsorship",
    r"(?:we|the company|employer) (?:will|can) sponsor",
    r"sponsorship (?:is )?(?:available|provided|offered)",
    r"eligible for (?:visa )?sponsorship",
    r"(?:h-?1b|skilled worker|tier 2) sponsorship",
]

NEGATIVE_PATTERNS = [
    r"no (?:visa )?sponsorship",
    r"(?:will not|cannot|can't|do not|don't) sponsor",
    r"not (?:eligible|available) for (?:visa )?sponsorship",
    r"without (?:current |existing )?(?:work )?authorization",
    r"must be (?:currently )?authorized to work.*(?:no|without).*(?:sponsor|visa)",
]


def evaluate_sponsorship(job: dict) -> tuple[bool, str, str]:
    """Return (verified, status, evidence) using only listing text."""
    text = " ".join([
        str(job.get("description", "")),
        str(job.get("requirements", "")),
    ]).lower()
    text = re.sub(r"\s+", " ", text)

    for pattern in NEGATIVE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return False, "explicitly_not_available", match.group(0)

    for pattern in POSITIVE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return True, "verified", match.group(0)

    return False, "not_verified", "No explicit sponsorship statement in listing"


def verify_sponsorship_categories(grouped_jobs: dict) -> tuple[dict, dict]:
    """Keep only evidence-backed jobs in the sponsorship category.

    Jobs found by a sponsorship search but lacking proof are still useful jobs;
    they are moved to the worldwide-review category rather than advertised as
    sponsored roles.
    """
    verified = 0
    downgraded = 0
    result = {category: list(jobs) for category, jobs in grouped_jobs.items()}
    result.setdefault("remote_worldwide", [])

    sponsored_candidates = result.get("sponsorship_worldwide", [])
    result["sponsorship_worldwide"] = []
    for job in sponsored_candidates:
        is_verified, status, evidence = evaluate_sponsorship(job)
        job["sponsorship_verified"] = is_verified
        job["sponsorship_status"] = status
        job["sponsorship_evidence"] = evidence
        if is_verified:
            job["sponsorship"] = True
            result["sponsorship_worldwide"].append(job)
            verified += 1
        else:
            job["sponsorship"] = False
            job["category"] = "remote_worldwide"
            job["type"] = "Remote Worldwide — sponsorship unverified"
            result["remote_worldwide"].append(job)
            downgraded += 1

    return result, {"verified": verified, "downgraded": downgraded}
