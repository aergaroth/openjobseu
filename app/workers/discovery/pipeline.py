'''

This is company/ats discovery pipeline.
KISS

'''
import json
from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery
from app.workers.discovery.company_sources import run_company_source_discovery


def run_discovery_pipeline():
    sources = run_company_source_discovery()
    careers = run_careers_discovery()
    guessing = run_ats_guessing()

    return {
        "status": "ok",
        "actions": ["discovery_completed"],
        "metrics": {
            "status": "ok",
            "pipeline": "discovery",
            "sources": sources,
            "careers": careers,
            "ats_guessing": guessing,
        }
    }


if __name__ == "__main__":
    print(json.dumps(run_discovery_pipeline(), indent=2, default=str))