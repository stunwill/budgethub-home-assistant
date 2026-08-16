from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal
from .security import utcnow

router = APIRouter(prefix="/api/intelligence")
DB = Depends(get_db)
USER = Depends(get_current_user)
RULE_TYPES = {"merchant", "category"}
MATCH_TYPES = {"exact", "contains", "prefix", "suffix", "regex"}
KNOWN = {"woolworths": "Woolworths", "woolies": "Woolworths", "coles": "Coles", "telstra": "Telstra", "powershop": "Powershop", "netflix": "Netflix", "spotify": "Spotify", "uber": "Uber", "budget direct": "Budget Direct", "payroll": "Payroll"}


def ensure_intelligence_schema(db: DbSession) -> None:
    db.execute(text("""CREATE TABLE IF NOT EXISTS intelligence_rules (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, rule_type VARCHAR(40) NOT NULL,
        name VARCHAR(160) NOT NULL, match_type VARCHAR(40) NOT NULL, pattern TEXT NOT NULL,
        normalised_merchant VARCHAR(180), category VARCHAR(180), priority INTEGER NOT NULL DEFAULT 100,
        apply_automatically BOOLEAN NOT NULL DEFAULT 1, is_active BOOLEAN NOT NULL DEFAULT 1,
        notes TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id))"""))
    db.execute(text("""CREATE TABLE IF NOT EXISTS intelligence_suggestions (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, suggestion_type VARCHAR(80) NOT NULL,
        title VARCHAR(220) NOT NULL, description TEXT NOT NULL, confidence VARCHAR(20) NOT NULL,
        evidence_json TEXT NOT NULL, action_payload_json TEXT, status VARCHAR(40) NOT NULL DEFAULT 'new',
        fingerprint VARCHAR(180) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
        dismissed_at DATETIME, accepted_at DATETIME, UNIQUE(user_id, fingerprint),
        FOREIGN KEY(user_id) REFERENCES users(id))"""))
    db.execute(text("""CREATE TABLE IF NOT EXISTS transaction_intelligence (
        id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, transaction_id INTEGER NOT NULL,
        normalised_merchant VARCHAR(180), suggested_category VARCHAR(180), category_confidence VARCHAR(20),
        category_evidence TEXT, is_recurring_candidate BOOLEAN NOT NULL DEFAULT 0,
        anomaly_status VARCHAR(80), anomaly_evidence TEXT, exclude_from_baseline BOOLEAN NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
        UNIQUE(user_id, transaction_id), FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(transaction_id) REFERENCES transactions(id))"""))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_intel_rules_user ON intelligence_rules(user_id, rule_type, is_active, priority)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_intel_suggestions_user ON intelligence_suggestions(user_id, status, suggestion_type)"))
    current = db.execute(text("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")).scalar()
    if current is None:
        db.execute(text("INSERT INTO schema_version (version) VALUES (9)"))
    elif current < 9:
        db.execute(text("UPDATE schema_version SET version = 9"))
    db.commit()


def _dump(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def _load(value: str | None) -> Any:
    return json.loads(value) if value else {}


def _clean(value: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    cleaned = re.sub(r"\b(VIC|NSW|QLD|SA|WA|TAS|NT|ACT|AU|AUS)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[#*]?\d{3,}\b", "", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9 &/+-]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _tx_date(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _matches_rule(rule: dict, description: str, merchant: str | None = None) -> bool:
    target = f"{description or ''} {merchant or ''}".strip()
    pattern = rule.get("pattern") or ""
    t = target.lower()
    p = pattern.lower()
    if rule["match_type"] == "exact":
        return t == p
    if rule["match_type"] == "contains":
        return p in t
    if rule["match_type"] == "prefix":
        return t.startswith(p)
    if rule["match_type"] == "suffix":
        return t.endswith(p)
    if rule["match_type"] == "regex":
        try:
            return bool(re.search(pattern, target, flags=re.IGNORECASE))
        except re.error:
            return False
    return False


def _normalise(db: DbSession, user: User, description: str, merchant: str | None = None) -> tuple[str | None, dict | None]:
    rules = db.execute(text("SELECT * FROM intelligence_rules WHERE user_id=:user_id AND rule_type='merchant' AND is_active=1 ORDER BY priority ASC, id ASC"), {"user_id": user.id}).mappings().all()
    for rule in rules:
        data = dict(rule)
        if _matches_rule(data, description, merchant):
            return data.get("normalised_merchant"), data
    cleaned = _clean(merchant or description).lower()
    for key, name in KNOWN.items():
        if key in cleaned:
            return name, {"name": "Built-in seed", "pattern": key}
    words = _clean(merchant or description).split()
    return (words[0].title() if words else None), None


def _category(db: DbSession, user: User, normalised: str | None, description: str, merchant: str | None) -> tuple[str | None, str, dict]:
    rules = db.execute(text("SELECT * FROM intelligence_rules WHERE user_id=:user_id AND rule_type='category' AND is_active=1 ORDER BY priority ASC, id ASC"), {"user_id": user.id}).mappings().all()
    for rule in rules:
        data = dict(rule)
        if _matches_rule(data, description, merchant or normalised):
            return data.get("category"), "high", {"reason": f"Matched user rule '{data['name']}'", "rule_id": data["id"]}
    if not normalised:
        return None, "low", {"reason": "No normalised merchant yet"}
    rows = db.execute(text("""SELECT category, COUNT(*) AS count FROM transactions
        WHERE user_id=:user_id AND category IS NOT NULL AND (lower(description) LIKE :needle OR lower(merchant)=:merchant)
        GROUP BY category ORDER BY count DESC"""), {"user_id": user.id, "needle": f"%{normalised.split()[0].lower()}%", "merchant": normalised.lower()}).mappings().all()
    total = sum(int(r["count"]) for r in rows)
    if not rows:
        return None, "low", {"reason": "No previous categorised transactions for this merchant"}
    top = rows[0]
    ratio = int(top["count"]) / max(total, 1)
    confidence = "high" if total >= 5 and ratio >= 0.8 else "medium" if total >= 2 else "low"
    return top["category"], confidence, {"reason": f"{top['count']} of {total} previous {normalised} transactions used this category", "sample_size": total}


def _confidence(score: float) -> str:
    return "high" if score >= 0.78 else "medium" if score >= 0.55 else "low"


def _suggest(db: DbSession, user: User, kind: str, title: str, description: str, confidence: str, evidence: dict, action: dict | None) -> None:
    fingerprint = f"{kind}:{json.dumps(action or evidence, sort_keys=True, default=str)}"[:180]
    existing = db.execute(text("SELECT id, status FROM intelligence_suggestions WHERE user_id=:user_id AND fingerprint=:fingerprint"), {"user_id": user.id, "fingerprint": fingerprint}).mappings().first()
    if existing and existing["status"] in {"dismissed", "ignored", "accepted"}:
        return
    now = utcnow()
    params = {"user_id": user.id, "kind": kind, "title": title, "description": description, "confidence": confidence, "evidence": _dump(evidence), "action": _dump(action), "fingerprint": fingerprint, "now": now}
    if existing:
        db.execute(text("UPDATE intelligence_suggestions SET title=:title, description=:description, confidence=:confidence, evidence_json=:evidence, action_payload_json=:action, updated_at=:now WHERE id=:id"), {**params, "id": existing["id"]})
    else:
        db.execute(text("INSERT INTO intelligence_suggestions (user_id, suggestion_type, title, description, confidence, evidence_json, action_payload_json, status, fingerprint, created_at, updated_at) VALUES (:user_id,:kind,:title,:description,:confidence,:evidence,:action,'new',:fingerprint,:now,:now)"), params)


def _transactions(db: DbSession, user: User, days: int = 540) -> list[dict]:
    start = (utcnow().date() - timedelta(days=days)).isoformat()
    return [dict(row) for row in db.execute(text("""SELECT id, account_id, transaction_date, amount_cents, transaction_type, description, merchant, category, source, status, raw_description
        FROM transactions WHERE user_id=:user_id AND transaction_date >= :start AND transaction_type IN ('expense','income') ORDER BY transaction_date ASC"""), {"user_id": user.id, "start": start}).mappings().all()]


def _cadence(gaps: list[int]) -> tuple[str | None, float]:
    if len(gaps) < 2:
        return None, 0
    avg = mean(gaps)
    name, target = min([("weekly", 7), ("fortnightly", 14), ("every_4_weeks", 28), ("monthly", 30.4), ("quarterly", 91.3), ("annual", 365)], key=lambda item: abs(avg - item[1]))
    variance = mean(abs(gap - target) for gap in gaps)
    return name, max(0, 1 - variance / max(target, 1))


def _detect_recurring(db: DbSession, user: User, groups: dict[tuple[str, str], list[dict]]) -> int:
    existing_expenses = {str(row[0]).lower() for row in db.execute(text("SELECT name FROM recurring_expenses WHERE user_id=:user_id AND is_active=1"), {"user_id": user.id}).all()}
    existing_income = {str(row[0]).lower() for row in db.execute(text("SELECT name FROM income_sources WHERE user_id=:user_id AND is_active=1"), {"user_id": user.id}).all()}
    made = 0
    for (direction, merchant), rows in groups.items():
        if len(rows) < 3 or direction not in {"expense", "income"}:
            continue
        if direction == "expense" and any(merchant.lower() in name or name in merchant.lower() for name in existing_expenses):
            continue
        if direction == "income" and any(merchant.lower() in name or name in merchant.lower() for name in existing_income):
            continue
        dates = sorted(_tx_date(row["transaction_date"]) for row in rows)
        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        frequency, cadence_score = _cadence(gaps)
        amounts = [abs(int(row["amount_cents"])) for row in rows]
        amount_score = 1 - (max(amounts) - min(amounts)) / max(mean(amounts), 1)
        score = max(0, min(1, cadence_score * 0.65 + amount_score * 0.35))
        if frequency and score >= 0.55:
            avg_amount = round(mean(amounts))
            kind = "recurring_income_detected" if direction == "income" else "recurring_expense_detected"
            description = f"{len(rows)} transactions from {merchant} occurred around a {frequency.replace('_', ' ')} cadence with an average amount of {cents_to_decimal(avg_amount)}."
            _suggest(db, user, kind, f"{merchant} appears to be {frequency.replace('_', ' ')} {direction}", description, _confidence(score), {"merchant": merchant, "transactions": len(rows), "gaps_days": gaps, "average_amount": cents_to_decimal(avg_amount), "frequency": frequency}, {"merchant": merchant, "amount_cents": avg_amount, "frequency": frequency, "direction": direction, "next_date": str(dates[-1] + timedelta(days=round(mean(gaps))))})
            _amount_change(db, user, merchant, direction, rows, frequency)
            made += 1
    return made


def _amount_change(db: DbSession, user: User, merchant: str, direction: str, rows: list[dict], frequency: str) -> None:
    if len(rows) < 5:
        return
    amounts = [abs(int(row["amount_cents"])) for row in rows]
    old = round(mean(amounts[:-2]))
    new = round(mean(amounts[-2:]))
    if old > 0 and abs(new - old) / old >= 0.12:
        change = "increased" if new > old else "decreased"
        _suggest(db, user, "recurring_amount_change", f"{merchant} appears to have {change}", f"Previous payments averaged {cents_to_decimal(old)}. The last two averaged {cents_to_decimal(new)}.", "medium", {"merchant": merchant, "old_amount": cents_to_decimal(old), "new_amount": cents_to_decimal(new), "frequency": frequency, "direction": direction}, {"merchant": merchant, "old_amount_cents": old, "new_amount_cents": new, "frequency": frequency, "direction": direction, "effective_from": str(rows[-2]["transaction_date"])})


def _trends(db: DbSession, user: User, rows: list[dict]) -> list[dict]:
    today = utcnow().date()
    current_start = today - timedelta(days=56)
    previous_start = today - timedelta(days=112)
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"current": 0, "previous": 0})
    for row in rows:
        if row["transaction_type"] != "expense" or not row.get("category"):
            continue
        d = _tx_date(row["transaction_date"])
        bucket = "current" if d >= current_start else "previous" if d >= previous_start else None
        if bucket:
            totals[row["category"]][bucket] += abs(int(row["amount_cents"]))
    output = []
    for category, values in totals.items():
        if values["current"] and values["previous"]:
            change = values["current"] - values["previous"]
            pct = round((change / values["previous"]) * 100, 1)
            state = "increasing" if pct >= 15 else "decreasing" if pct <= -15 else "stable"
            item = {"category": category, "current_8_weeks": cents_to_decimal(values["current"]), "previous_8_weeks": cents_to_decimal(values["previous"]), "change": cents_to_decimal(change), "percent_change": pct, "state": state, "evidence": f"Compared the latest 8 weeks with the previous 8 weeks for {category}."}
            output.append(item)
            if abs(pct) >= 15:
                _suggest(db, user, "spending_trend", f"{category} spending is {state}", f"{category} changed by {pct}% compared with the previous 8 weeks.", "medium", item, {"category": category})
    return output


def _anomalies(db: DbSession, user: User, rows: list[dict]) -> int:
    groups: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        if row["transaction_type"] == "expense" and row.get("category"):
            groups[row["category"]].append(abs(int(row["amount_cents"])))
    count = 0
    for row in rows:
        category = row.get("category")
        if row["transaction_type"] != "expense" or not category or len(groups[category]) < 5:
            continue
        amount = abs(int(row["amount_cents"]))
        others = [value for value in groups[category] if value != amount] or groups[category]
        baseline = mean(others)
        if baseline > 0 and amount >= baseline * 1.8 and amount - baseline >= 5000:
            evidence = {"transaction_id": row["id"], "category": category, "amount": cents_to_decimal(amount), "baseline_average": cents_to_decimal(round(baseline)), "difference_percent": round(((amount - baseline) / baseline) * 100, 1), "period": "recent category history"}
            db.execute(text("UPDATE transaction_intelligence SET anomaly_status='higher_than_usual', anomaly_evidence=:evidence, updated_at=:now WHERE user_id=:user_id AND transaction_id=:tx"), {"user_id": user.id, "tx": row["id"], "evidence": _dump(evidence), "now": utcnow()})
            _suggest(db, user, "unusual_spending", f"Higher than usual {category} transaction", f"This transaction is {evidence['difference_percent']}% above the recent {category} average.", "medium", evidence, {"transaction_id": row["id"]})
            count += 1
    return count


def process_transactions(db: DbSession, user: User) -> dict:
    ensure_intelligence_schema(db)
    rows = _transactions(db, user)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    now = utcnow()
    for row in rows:
        normalised, rule = _normalise(db, user, row["description"], row.get("merchant"))
        category, cat_conf, evidence = _category(db, user, normalised, row["description"], row.get("merchant"))
        db.execute(text("""INSERT INTO transaction_intelligence (user_id, transaction_id, normalised_merchant, suggested_category, category_confidence, category_evidence, created_at, updated_at)
            VALUES (:user_id,:tx,:merchant,:category,:confidence,:evidence,:now,:now)
            ON CONFLICT(user_id, transaction_id) DO UPDATE SET normalised_merchant=:merchant, suggested_category=:category, category_confidence=:confidence, category_evidence=:evidence, updated_at=:now"""), {"user_id": user.id, "tx": row["id"], "merchant": normalised, "category": category, "confidence": cat_conf, "evidence": _dump(evidence), "now": now})
        if normalised and normalised != row.get("merchant"):
            _suggest(db, user, "merchant_normalisation", f"Normalise {row['description']} to {normalised}", f"Fynvo can preserve the original description and use {normalised} as the cleaner merchant name.", "medium" if rule else "low", {"original_description": row["description"], "normalised_merchant": normalised, "rule": rule}, {"normalised_merchant": normalised})
        if category and row.get("category") != category:
            _suggest(db, user, "category_suggestion", f"Categorise {normalised or row['description']} as {category}", evidence["reason"], cat_conf, {"transaction_id": row["id"], "merchant": normalised, "suggested_category": category, **evidence}, {"transaction_id": row["id"], "category": category})
        groups[(row["transaction_type"], normalised or _clean(row["description"]).title())].append(row)
    recurring = _detect_recurring(db, user, groups)
    trends = _trends(db, user, rows)
    anomalies = _anomalies(db, user, rows)
    db.commit()
    return {"processed_transactions": len(rows), "recurring_suggestions": recurring, "trend_count": len(trends), "anomaly_count": anomalies}


def _out(row: Any) -> dict:
    item = dict(row)
    item["evidence"] = _load(item.pop("evidence_json"))
    item["action_payload"] = _load(item.pop("action_payload_json"))
    return item


def create_rule(db: DbSession, user: User, payload: dict[str, Any]) -> dict:
    ensure_intelligence_schema(db)
    rule_type = payload.get("rule_type")
    match_type = payload.get("match_type") or "contains"
    if rule_type not in {"merchant", "category"} or match_type not in MATCH_TYPES:
        raise HTTPException(status_code=400, detail="Invalid rule type or match type")
    if match_type == "regex":
        try:
            re.compile(payload.get("pattern") or "")
        except re.error as exc:
            raise HTTPException(status_code=400, detail="Invalid regular expression") from exc
    now = utcnow()
    db.execute(text("""INSERT INTO intelligence_rules (user_id, rule_type, name, match_type, pattern, normalised_merchant, category, priority, apply_automatically, is_active, notes, created_at, updated_at)
        VALUES (:user_id,:rule_type,:name,:match_type,:pattern,:merchant,:category,:priority,:auto,:active,:notes,:now,:now)"""), {"user_id": user.id, "rule_type": rule_type, "name": payload.get("name") or payload.get("pattern") or "Rule", "match_type": match_type, "pattern": payload.get("pattern") or "", "merchant": payload.get("normalised_merchant"), "category": payload.get("category"), "priority": int(payload.get("priority", 100)), "auto": bool(payload.get("apply_automatically", True)), "active": bool(payload.get("is_active", True)), "notes": payload.get("notes"), "now": now})
    return dict(db.execute(text("SELECT * FROM intelligence_rules WHERE id=last_insert_rowid()")).mappings().first())


@router.post("/process")
def process(current_user: User = USER, db: DbSession = DB):
    return process_transactions(db, current_user)


@router.get("/suggestions")
def list_suggestions(status_filter: str = "new", current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    rows = db.execute(text("SELECT * FROM intelligence_suggestions WHERE user_id=:user_id AND (:status='all' OR status=:status) ORDER BY CASE confidence WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC"), {"user_id": current_user.id, "status": status_filter}).mappings().all()
    return [_out(row) for row in rows]


@router.post("/suggestions/{suggestion_id}/dismiss")
def dismiss_suggestion(suggestion_id: int, current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    result = db.execute(text("UPDATE intelligence_suggestions SET status='dismissed', dismissed_at=:now, updated_at=:now WHERE id=:id AND user_id=:user_id AND status='new'"), {"id": suggestion_id, "user_id": current_user.id, "now": utcnow()})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return {"status": "dismissed"}


@router.post("/suggestions/{suggestion_id}/accept")
def accept_suggestion(suggestion_id: int, current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    row = db.execute(text("SELECT * FROM intelligence_suggestions WHERE id=:id AND user_id=:user_id"), {"id": suggestion_id, "user_id": current_user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    suggestion = _out(row)
    action = suggestion.get("action_payload") or {}
    now = utcnow()
    kind = suggestion["suggestion_type"]
    if kind == "category_suggestion" and action.get("transaction_id"):
        db.execute(text("UPDATE transactions SET category=:category, updated_at=:now WHERE id=:tx AND user_id=:user_id"), {"category": action["category"], "tx": action["transaction_id"], "user_id": current_user.id, "now": now})
    elif kind == "recurring_expense_detected":
        db.execute(text("INSERT INTO recurring_expenses (user_id,name,amount_cents,frequency,interval_count,next_due_date,category,is_active,source,created_at,updated_at) VALUES (:user_id,:name,:amount,:frequency,1,:next_due,NULL,1,'intelligence',:now,:now)"), {"user_id": current_user.id, "name": action["merchant"], "amount": action["amount_cents"], "frequency": action["frequency"], "next_due": action["next_date"], "now": now})
    elif kind == "recurring_income_detected":
        db.execute(text("INSERT INTO income_sources (user_id,name,amount_cents,frequency,interval_count,next_payment_date,is_active,source,created_at,updated_at) VALUES (:user_id,:name,:amount,:frequency,1,:next_date,1,'intelligence',:now,:now)"), {"user_id": current_user.id, "name": action["merchant"], "amount": action["amount_cents"], "frequency": action["frequency"], "next_date": action["next_date"], "now": now})
    elif kind == "recurring_amount_change":
        table = "recurring_expenses" if action.get("direction") == "expense" else "income_sources"
        record = db.execute(text(f"SELECT id FROM {table} WHERE user_id=:user_id AND lower(name) LIKE :name ORDER BY updated_at DESC LIMIT 1"), {"user_id": current_user.id, "name": f"%{action['merchant'].lower()}%"}).mappings().first()
        if record:
            db.execute(text("INSERT INTO effective_amount_changes (user_id, record_type, record_id, new_amount_cents, effective_from, source, notes, created_at, updated_at) VALUES (:user_id,:record_type,:record_id,:amount,:effective_from,'intelligence','Accepted recurring amount change suggestion',:now,:now)"), {"user_id": current_user.id, "record_type": "recurring_expense" if action.get("direction") == "expense" else "income", "record_id": record["id"], "amount": action["new_amount_cents"], "effective_from": action["effective_from"], "now": now})
    db.execute(text("UPDATE intelligence_suggestions SET status='accepted', accepted_at=:now, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"id": suggestion_id, "user_id": current_user.id, "now": now})
    db.commit()
    return {"status": "accepted", "suggestion_type": kind}


@router.get("/rules")
def list_rules(current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    return [dict(row) for row in db.execute(text("SELECT * FROM intelligence_rules WHERE user_id=:user_id ORDER BY priority ASC, id ASC"), {"user_id": current_user.id}).mappings().all()]


@router.post("/rules", status_code=status.HTTP_201_CREATED)
def add_rule(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    rule = create_rule(db, current_user, payload)
    db.commit()
    return rule


@router.put("/rules/{rule_id}")
def edit_rule(rule_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    existing = db.execute(text("SELECT * FROM intelligence_rules WHERE id=:id AND user_id=:user_id"), {"id": rule_id, "user_id": current_user.id}).mappings().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")
    updates = {key: payload[key] for key in ["name", "match_type", "pattern", "normalised_merchant", "category", "priority", "apply_automatically", "is_active", "notes"] if key in payload}
    if updates.get("match_type") == "regex":
        re.compile(updates.get("pattern") or existing["pattern"])
    if updates:
        values = {"id": rule_id, "user_id": current_user.id, "now": utcnow(), **updates}
        db.execute(text(f"UPDATE intelligence_rules SET {', '.join(f'{key}=:{key}' for key in updates)}, updated_at=:now WHERE id=:id AND user_id=:user_id"), values)
    db.commit()
    return dict(db.execute(text("SELECT * FROM intelligence_rules WHERE id=:id AND user_id=:user_id"), {"id": rule_id, "user_id": current_user.id}).mappings().first())


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    result = db.execute(text("DELETE FROM intelligence_rules WHERE id=:id AND user_id=:user_id"), {"id": rule_id, "user_id": current_user.id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "deleted"}


@router.post("/rules/{rule_id}/preview")
def preview_rule(rule_id: int, current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    rule = db.execute(text("SELECT * FROM intelligence_rules WHERE id=:id AND user_id=:user_id"), {"id": rule_id, "user_id": current_user.id}).mappings().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    matches = [row for row in _transactions(db, current_user, 3650) if _matches_rule(dict(rule), row["description"], row.get("merchant"))]
    return {"match_count": len(matches), "transactions": matches[:25]}


@router.post("/rules/{rule_id}/apply-history")
def apply_rule_history(rule_id: int, current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    rule = db.execute(text("SELECT * FROM intelligence_rules WHERE id=:id AND user_id=:user_id"), {"id": rule_id, "user_id": current_user.id}).mappings().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    count = 0
    for row in _transactions(db, current_user, 3650):
        if _matches_rule(dict(rule), row["description"], row.get("merchant")):
            if rule["rule_type"] == "merchant" and rule["normalised_merchant"]:
                db.execute(text("UPDATE transactions SET merchant=:merchant, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"merchant": rule["normalised_merchant"], "id": row["id"], "user_id": current_user.id, "now": utcnow()})
                count += 1
            if rule["rule_type"] == "category" and rule["category"]:
                db.execute(text("UPDATE transactions SET category=:category, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"category": rule["category"], "id": row["id"], "user_id": current_user.id, "now": utcnow()})
                count += 1
    db.commit()
    return {"updated": count}


@router.get("/merchants")
def merchant_summary(current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    process_transactions(db, current_user)
    rows = db.execute(text("""SELECT ti.normalised_merchant AS merchant, COUNT(*) AS count, SUM(ABS(t.amount_cents)) AS total, AVG(ABS(t.amount_cents)) AS average, MIN(t.transaction_date) AS first_seen, MAX(t.transaction_date) AS last_seen
        FROM transaction_intelligence ti JOIN transactions t ON t.id=ti.transaction_id
        WHERE ti.user_id=:user_id AND ti.normalised_merchant IS NOT NULL AND t.transaction_type='expense'
        GROUP BY ti.normalised_merchant ORDER BY total DESC"""), {"user_id": current_user.id}).mappings().all()
    return [{"merchant": row["merchant"], "transaction_count": row["count"], "total_spend": cents_to_decimal(row["total"] or 0), "average_transaction": cents_to_decimal(round(row["average"] or 0)), "first_seen": str(row["first_seen"]), "last_seen": str(row["last_seen"])} for row in rows]


@router.get("/trends")
def trends(current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    return _trends(db, current_user, _transactions(db, current_user))


@router.post("/transactions/{transaction_id}/exclude-baseline")
def exclude_transaction_baseline(transaction_id: int, current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    db.execute(text("""INSERT INTO transaction_intelligence (user_id, transaction_id, exclude_from_baseline, created_at, updated_at)
        VALUES (:user_id,:tx,1,:now,:now)
        ON CONFLICT(user_id, transaction_id) DO UPDATE SET exclude_from_baseline=1, updated_at=:now"""), {"user_id": current_user.id, "tx": transaction_id, "now": utcnow()})
    db.commit()
    return {"status": "excluded_from_baseline"}
