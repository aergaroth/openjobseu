#!/usr/bin/env python3
"""Audit new public job sources for EU/UK remote suitability.

Criteria:
- Count offers that look like remote roles available in EU/UK.
- Reject offers with explicit on-site / hybrid signals.
- Source is ACCEPT only when:
  - remote_eu_uk_percent > 30

This script is heuristic by design and intended for source discovery.
"""

from __future__ import annotations

import argparse
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable

import requests


USER_AGENT = "OpenJobsEU-source-discovery-audit/1.0"
TIMEOUT = 30

EU_UK_MARKERS = {
    "eu",
    "europe",
    "european union",
    "eea",
    "uk",
    "united kingdom",
    "great britain",
    "worldwide",
    "austria",
    "belgium",
    "bulgaria",
    "croatia",
    "cyprus",
    "czech",
    "czechia",
    "denmark",
    "estonia",
    "finland",
    "france",
    "germany",
    "greece",
    "hungary",
    "ireland",
    "italy",
    "latvia",
    "lithuania",
    "luxembourg",
    "malta",
    "netherlands",
    "poland",
    "portugal",
    "romania",
    "slovakia",
    "slovenia",
    "spain",
    "sweden",
}

REMOTE_KEYWORDS = [
    "remote",
    "work from home",
    "wfh",
    "distributed",
    "anywhere",
]

NEGATIVE_REMOTE_KEYWORDS = [
    "not remote",
    "do not offer remote",
    "office-first",
]

ONSITE_KEYWORDS = [
    "on-site",
    "onsite",
    "hybrid",
    "in-office",
    "in office",
    "office-based",
    "relocation",
]


@dataclass
class Offer:
    title: str
    location: str
    description: str
    remote_hint: bool = False


@dataclass
class SourceResult:
    name: str
    endpoint: str
    source_type: str
    total: int
    remote_eu_uk: int
    onsite_hits: int
    sample_size: int

    @property
    def remote_pct(self) -> float:
        return (100.0 * self.remote_eu_uk / self.total) if self.total else 0.0

    @property
    def accepted(self) -> bool:
        return self.remote_pct > 30.0


@dataclass
class SourceSpec:
    name: str
    endpoint: str
    source_type: str
    loader: Callable[[requests.Session], list[Offer]]


def normalize_text(value: str | None) -> str:
    raw = html.unescape(value or "").lower()
    return re.sub(r"\s+", " ", raw).strip()


def contains_any(text: str, keywords: list[str] | set[str]) -> bool:
    ntext = normalize_text(text)
    return any(keyword in ntext for keyword in keywords)


def looks_eu_uk(location_text: str, full_text: str) -> bool:
    return contains_any(location_text, EU_UK_MARKERS) or contains_any(full_text, EU_UK_MARKERS)


def looks_remote(offer: Offer, full_text: str) -> bool:
    has_remote_signal = offer.remote_hint or contains_any(full_text, REMOTE_KEYWORDS)
    if not has_remote_signal:
        return False
    return not contains_any(full_text, NEGATIVE_REMOTE_KEYWORDS)


def looks_onsite(full_text: str) -> bool:
    return contains_any(full_text, ONSITE_KEYWORDS)


def load_arbeitnow_api(session: requests.Session) -> list[Offer]:
    data = session.get("https://arbeitnow.com/api/job-board-api", timeout=TIMEOUT).json()
    offers: list[Offer] = []
    for raw in data.get("data", []):
        offers.append(
            Offer(
                title=str(raw.get("title") or ""),
                location=str(raw.get("location") or ""),
                description=str(raw.get("description") or ""),
                remote_hint=bool(raw.get("remote")),
            )
        )
    return offers


def load_jobicy_api(session: requests.Session) -> list[Offer]:
    data = session.get("https://jobicy.com/api/v2/remote-jobs", timeout=TIMEOUT).json()
    offers: list[Offer] = []
    for raw in data.get("jobs", []):
        offers.append(
            Offer(
                title=str(raw.get("jobTitle") or ""),
                location=str(raw.get("jobGeo") or ""),
                description=str(raw.get("jobDescription") or ""),
                remote_hint=True,
            )
        )
    return offers


def _parse_xml(endpoint: str, session: requests.Session, fix_prefixes: bool = False) -> ET.Element:
    xml_text = session.get(endpoint, timeout=TIMEOUT).text
    if fix_prefixes:
        # Himalayas feed includes undeclared prefixed tags.
        xml_text = re.sub(r"<(/?)([A-Za-z_][\w.-]*):", r"<\1\2_", xml_text)
    return ET.fromstring(xml_text)


def load_himalayas_rss(session: requests.Session) -> list[Offer]:
    root = _parse_xml("https://himalayas.app/jobs/rss", session, fix_prefixes=True)
    offers: list[Offer] = []
    for item in root.findall("./channel/item"):
        restrictions = " ".join((node.text or "") for node in item.findall("himalayasJobs_locationRestriction"))
        description = f"{item.findtext('description') or ''} {item.findtext('content_encoded') or ''}"
        offers.append(
            Offer(
                title=item.findtext("title") or "",
                location=restrictions,
                description=description,
                remote_hint=True,
            )
        )
    return offers


def load_jobicy_rss(session: requests.Session) -> list[Offer]:
    root = _parse_xml("https://jobicy.com/?feed=job_feed", session)
    namespace = {"job": "https://jobicy.com"}
    offers: list[Offer] = []
    for item in root.findall("./channel/item"):
        offers.append(
            Offer(
                title=item.findtext("title") or "",
                location=item.findtext("job:location", namespaces=namespace) or "",
                description=item.findtext("description") or "",
                remote_hint=True,
            )
        )
    return offers


def load_devitjobs_uk_xml(session: requests.Session) -> list[Offer]:
    root = _parse_xml("https://devitjobs.uk/job_feed.xml", session)
    offers: list[Offer] = []
    for item in root.findall("./job"):
        location_parts = [
            item.findtext("location") or "",
            item.findtext("country") or "",
            item.findtext("city") or "",
            item.findtext("jobtype") or "",
            item.findtext("job-type") or "",
        ]
        location_text = " ".join(part for part in location_parts if part)
        offers.append(
            Offer(
                title=item.findtext("title") or "",
                location=location_text,
                description=item.findtext("description") or "",
                remote_hint=contains_any(location_text, ["remote"]),
            )
        )
    return offers


def load_muse_api(session: requests.Session) -> list[Offer]:
    data = session.get("https://www.themuse.com/api/public/jobs?page=1", timeout=TIMEOUT).json()
    offers: list[Offer] = []
    for raw in data.get("results", []):
        locations = " ".join(item.get("name", "") for item in (raw.get("locations") or []))
        offers.append(
            Offer(
                title=str(raw.get("name") or ""),
                location=locations,
                description=str(raw.get("contents") or ""),
                remote_hint=False,
            )
        )
    return offers


def analyze_source(spec: SourceSpec, session: requests.Session, sample_size: int) -> SourceResult:
    offers = spec.loader(session)
    if sample_size > 0:
        offers = offers[:sample_size]

    total = len(offers)
    remote_eu_uk = 0
    onsite_hits = 0

    for offer in offers:
        full_text = f"{offer.title} {offer.location} {offer.description}"
        is_onsite = looks_onsite(full_text)
        if is_onsite:
            onsite_hits += 1

        if looks_remote(offer, full_text) and looks_eu_uk(offer.location, full_text) and not is_onsite:
            remote_eu_uk += 1

    return SourceResult(
        name=spec.name,
        endpoint=spec.endpoint,
        source_type=spec.source_type,
        total=total,
        remote_eu_uk=remote_eu_uk,
        onsite_hits=onsite_hits,
        sample_size=sample_size,
    )


def print_table(results: list[SourceResult]) -> None:
    print(
        "source,total,remote_eu_uk,remote_pct,onsite_hits,accept,source_type,endpoint"
    )
    for result in results:
        verdict = "ACCEPT" if result.accepted else "REJECT"
        print(
            f"{result.name},{result.total},{result.remote_eu_uk},{result.remote_pct:.1f},"
            f"{result.onsite_hits},{verdict},{result.source_type},{result.endpoint}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit new public RSS/API sources for OpenJobsEU")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=300,
        help="max offers to analyze per source (default: 300)",
    )
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json, application/xml, text/xml"})

    sources = [
        SourceSpec(
            name="arbeitnow_api",
            endpoint="https://arbeitnow.com/api/job-board-api",
            source_type="api",
            loader=load_arbeitnow_api,
        ),
        SourceSpec(
            name="jobicy_api",
            endpoint="https://jobicy.com/api/v2/remote-jobs",
            source_type="api",
            loader=load_jobicy_api,
        ),
        SourceSpec(
            name="himalayas_rss",
            endpoint="https://himalayas.app/jobs/rss",
            source_type="rss",
            loader=load_himalayas_rss,
        ),
        SourceSpec(
            name="jobicy_rss",
            endpoint="https://jobicy.com/?feed=job_feed",
            source_type="rss",
            loader=load_jobicy_rss,
        ),
        SourceSpec(
            name="devitjobs_uk_xml",
            endpoint="https://devitjobs.uk/job_feed.xml",
            source_type="rss",
            loader=load_devitjobs_uk_xml,
        ),
        SourceSpec(
            name="themuse_api",
            endpoint="https://www.themuse.com/api/public/jobs?page=1",
            source_type="api",
            loader=load_muse_api,
        ),
    ]

    results: list[SourceResult] = []
    for spec in sources:
        try:
            results.append(analyze_source(spec, session, args.sample_size))
        except Exception as exc:  # pylint: disable=broad-except
            print(
                f"{spec.name},0,0,0.0,0,ERROR,{spec.source_type},{spec.endpoint} :: {type(exc).__name__}: {exc}"
            )

    print_table(results)


if __name__ == "__main__":
    main()
