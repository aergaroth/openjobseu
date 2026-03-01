import requests

# GREENHOUSE_BOARDS = ["adyen"]


class GreenhouseApiAdapter:
    source = "greenhouse"
    API_URL_TEMPLATE = (
        "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    )

    def __init__(self, board_token: str):
        token = (board_token or "").strip()
        if not token:
            raise ValueError("board_token cannot be empty")
        self.board_token = token
        self.api_url = self.API_URL_TEMPLATE.format(board_token=token)

    def fetch(self) -> list[dict]:
        resp = requests.get(
            self.api_url,
            headers={
                "User-Agent": "OpenJobsEU/1.0 (https://openjobseu.org)",
                "Accept": "application/json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()

        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            raise ValueError("Greenhouse API did not return a dict payload")

        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            raise ValueError("Greenhouse API payload does not contain a jobs list")

        return jobs
