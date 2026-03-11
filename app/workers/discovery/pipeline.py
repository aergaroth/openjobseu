'''

This is company/ats discovery pipeline.
KISS

'''
import json
from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery


def run_discovery_pipeline():
    careers = run_careers_discovery()
    guessing = run_ats_guessing()

    return {
        "pipeline": "discovery",
        "careers": careers,
        "ats_guessing": guessing,
    }


if __name__ == "__main__":
    print(json.dumps(run_discovery_pipeline(), indent=2, default=str))