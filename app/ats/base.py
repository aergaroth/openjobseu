from abc import ABC, abstractmethod
from typing import Any, Iterable, Dict

from app.utils.cleaning import normalize_remote_scope as _normalize_remote_scope


class ATSAdapter(ABC):
    """
    Abstract base class for ATS adapters.
    
    Each adapter must implement:
    - source_name: unique identifier for the ATS provider
    - fetch(company, updated_since): fetch raw jobs from ATS API
    - normalize(raw_job): convert raw ATS payload to canonical job dict
    """
    
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


# Backward compatibility alias
BaseATSAdapter = ATSAdapter