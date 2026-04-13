"""

This is company/ats discovery pipeline.
KISS

"""

import json
import logging

from app.workers.discovery.ats_guessing import run_ats_guessing
from app.workers.discovery.careers_crawler import run_careers_discovery
from app.workers.discovery.company_sources import run_company_source_discovery
from app.workers.discovery.ats_reverse import run_ats_reverse_discovery
from app.workers.discovery.dorking import run_dorking_discovery
from app.workers.discovery.dorking_crt import run_dorking_crt_discovery
from app.workers.discovery.promote_discovered_slugs import run_promote_discovered_slugs
from app.utils.pipeline_runner import run_pipeline_steps

logger = logging.getLogger(__name__)

PIPELINE_STEPS = [
    ("sources", run_company_source_discovery),
    ("careers", run_careers_discovery),
    ("ats_reverse", run_ats_reverse_discovery),
    ("ats_guessing", run_ats_guessing),
    ("dorking", run_dorking_discovery),
    ("dorking_crt", run_dorking_crt_discovery),
    ("promote_discovered", run_promote_discovered_slugs),
]


def run_discovery_pipeline():
    metrics = run_pipeline_steps("discovery", PIPELINE_STEPS, logger)

    return {
        "status": "ok",
        "actions": ["discovery_completed"],
        "metrics": metrics,
    }


if __name__ == "__main__":
    logger.info(json.dumps(run_discovery_pipeline(), indent=2, default=str))
