from abc import ABC, abstractmethod
from typing import Any, Iterable, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.utils.cleaning import normalize_remote_scope as _normalize_remote_scope


class TimeoutSession(requests.Session):
    """
    Custom requests.Session that enforces a default timeout on all HTTP requests
    and provides automatic retries for transient network/server errors.
    """
    def __init__(self, timeout: int = 30, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout
        
        # Configure automatic retries for 429 (Rate Limit) and 5xx (Server Errors)
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.mount("https://", adapter)
        self.mount("http://", adapter)

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return super().request(method, url, **kwargs)

class ATSAdapter(ABC):
    """
    Abstract base class for ATS adapters.
    
    Each adapter must implement:
    - source_name: unique identifier for the ATS provider
    - fetch(company, updated_since): fetch raw jobs from ATS API
    - normalize(raw_job): convert raw ATS payload to canonical job dict
  
    The normalize method should return a dict with at least the following fields:
    - source: str (e.g. "greenhouse:acme")
    - source_job_id: str (unique ID from ATS)
    - title: str
    - description: str
    - remote_scope: str
    - company_name: str (optional)
    Adapters can also implement provider-specific logic for handling API requests, pagination, rate limits, etc.
       
    """
    def __init__(self):
        self.session = TimeoutSession(timeout=30)
        self.session.headers.update({
            "User-Agent": "OpenJobsEU/1.0 (https://openjobseu.org)",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
        })
    source_name: str
    
    # Backward compatibility: allow access via 'provider' attribute
    @property
    def provider(self) -> str:
        """Alias for source_name (backward compatibility)."""
        return self.source_name
    
    def normalize_remote_scope(self, value: str | None) -> str:
        """
        Normalize remote/location strings across ATS providers.
        """
        return _normalize_remote_scope(value)
    
    @abstractmethod
    def fetch(self, company: Dict, updated_since: Any = None) -> Iterable[Dict]:
        """
        Fetch raw jobs from ATS API.
        
        Args:
            company: Company dict with ats_slug and other metadata
            updated_since: Optional datetime for incremental fetching
            
        Returns:
            Iterable of raw ATS job payloads
        """
        raise NotImplementedError
    
    @abstractmethod
    def normalize(self, raw_job: Dict) -> Dict | None:
        """
        Convert raw ATS payload to canonical job dict.
        
        Returns None if job should be skipped.
        
        Expected output fields:
        - source: str
        - source_job_id: str
        - title: str
        - description: str
        - remote_scope: str
        - company_name: str (optional)
        """
        raise NotImplementedError

    @abstractmethod
    def probe_jobs(self, slug: str) -> Dict[str, Any]:
        """Lightweight discovery probe that inspects availability of jobs."""
        raise NotImplementedError


# Backward compatibility alias
BaseATSAdapter = ATSAdapter