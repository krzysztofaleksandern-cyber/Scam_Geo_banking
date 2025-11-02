
"""
Lightweight STIX 2.1 exporter without hard dependency on stix2 package.
Produces a minimal valid-ish bundle as JSON (bank POC level).
"""
import json, uuid, datetime

def _ts():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _sid(typ):
    return f"{typ}--{uuid.uuid4()}"

def ioc_to_observable(ioc):
    t = (ioc.get("type") or "").lower()
    v = ioc.get("value")
    if t in ("url", "uri"):
        return {
            "type": "observed-data",
            "id": _sid("observed-data"),
            "created": _ts(),
            "modified": _ts(),
            "first_observed": _ts(),
            "last_observed": _ts(),
            "number_observed": 1,
            "object_refs": [
                {
                    "type": "url",
                    "id": _sid("url"),
                    "value": v
                }
            ]
        }
    if t in ("domain", "hostname"):
        return {
            "type": "domain-name",
            "id": _sid("domain-name"),
            "value": v
        }
    if t in ("email", "email-address"):
        return {
            "type": "email-addr",
            "id": _sid("email-addr"),
            "value": v
        }
    if t in ("ip", "ipv4", "ipv6"):
        return {
            "type": "ipv4-addr" if ":" not in v else "ipv6-addr",
            "id": _sid("ipv4-addr" if ":" not in v else "ipv6-addr"),
            "value": v
        }
    if t in ("iban",):
        return {
            "type": "x-ibAN",
            "id": _sid("x-ibAN"),
            "value": v
        }
    return None

def export_stix21(iocs, case_id:str=None):
    objs = []
    for i in iocs or []:
        o = ioc_to_observable(i)
        if o:
            objs.append(o)
    bundle = {
        "type": "bundle",
        "id": _sid("bundle"),
        "objects": objs,
        "spec_version": "2.1",
        "x_case_id": case_id,
        "x_generated_utc": _ts()
    }
    return json.dumps(bundle, indent=2)
