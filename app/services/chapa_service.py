import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(frozen=True)
class ChapaInitializeResult:
    checkout_url: str


@dataclass(frozen=True)
class ChapaVerifyResult:
    status: str
    tx_ref: str | None
    reference: str | None
    amount: str | None
    currency: str | None
    raw: dict


class ChapaService:
    def __init__(self, base_url: str, secret_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.secret_key = secret_key

    def _request_json(self, method: str, url: str, payload: dict | None = None) -> dict:
        data = None
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            detail = raw or f"Chapa HTTP error: {exc.code}"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to communicate with Chapa",
            ) from exc

    def initialize_transaction(self, payload: dict) -> ChapaInitializeResult:
        url = f"{self.base_url}/v1/transaction/initialize"
        data = self._request_json("POST", url, payload=payload)
        checkout_url = (((data or {}).get("data") or {}).get("checkout_url")) if isinstance(data, dict) else None
        if not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Chapa initialize did not return checkout_url",
            )
        return ChapaInitializeResult(checkout_url=checkout_url)

    def verify_transaction(self, tx_ref: str) -> ChapaVerifyResult:
        url = f"{self.base_url}/v1/transaction/verify/{tx_ref}"
        data = self._request_json("GET", url)
        d = (data or {}).get("data") if isinstance(data, dict) else None

        status_value = (d or {}).get("status") if isinstance(d, dict) else None
        reference = (d or {}).get("reference") if isinstance(d, dict) else None
        amount = (d or {}).get("amount") if isinstance(d, dict) else None
        currency = (d or {}).get("currency") if isinstance(d, dict) else None
        tx_ref_value = (d or {}).get("tx_ref") if isinstance(d, dict) else None

        return ChapaVerifyResult(
            status=str(status_value) if status_value is not None else "unknown",
            tx_ref=str(tx_ref_value) if tx_ref_value is not None else None,
            reference=str(reference) if reference is not None else None,
            amount=str(amount) if amount is not None else None,
            currency=str(currency) if currency is not None else None,
            raw=data if isinstance(data, dict) else {"raw": data},
        )

