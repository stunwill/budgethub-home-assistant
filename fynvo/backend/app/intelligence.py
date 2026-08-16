from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from statistics import mean
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter(prefix="/api/intelligence")
DB = Depends(get_db)
USER = Depends(get_current_user)

RULE_TYPES = {"merchant", "category"}
MATCH_TYPES = {"exact", "contains", "prefix", "suffix", "regex"}
SUGGESTION_STATUSES = {"new", "accepted", "dismissed", "ignored"}
CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}

KNOWN_MERCHANTS = {
    "woolworths": "Woolworths",
    "woolies": "Woolworths",
    "coles": "Coles",
    "telstra": "Telstra",
    "powershop": "Powershop",
    "netflix": "Netflix",
    "spotify": "Spotify",
    "uber": "Uber",
    "budget direct": "Budget Direct",
}


def ensure_intelligence_schema(db: DbSession) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS intelligence_rules (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, rule_type VARCHAR(40) NOT NULL,
            name VARCHAR(160) NOT NULL, match_type VARCHAR(40) NOT NULL, pattern TEXT NOT NULL,
            normalised_merchant VARCHAR(180), category VARCHAR(180), priority INTEGER NOT NULL DEFAULT 100,
            apply_automatically BOOLEAN NOT NULL DEFAULT 1, is_active BOOLEAN NOT NULL DEFAULT 1,
            notes TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS intelligence_suggestions (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, suggestion_type VARCHAR(80) NOT NULL,
            title VARCHAR(220) NOT NULL, description TEXT NOT NULL, confidence VARCHAR(20) NOT NULL,
            evidence_json TEXT NOT NULL, action_payload_json TEXT, status VARCHAR(40) NOT NULL DEFAULT 'new',
            fingerprint VARCHAR(180) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
            dismissed_at DATETIME, accepted_at DATETIME, UNIQUE(user_id, fingerprint),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS transaction_intelligence (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, transaction_id INTEGER NOT NULL,
            normalised_merchant VARCHAR(180), suggested_category VARCHAR(180), category_confidence VARCHAR(20),
            category_evidence TEXT, is_recurring_candidate BOOLEAN NOT NULL DEFAULT 0,
            anomaly_status VARCHAR(80), anomaly_evidence TEXT, exclude_from_baseline BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
            UNIQUE(user_id, transaction_id), FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(transaction_id) REFERENCES transactions(id)
        )
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_intel_rules_user ON intelligence_rules(user_id, rule_type, is_active, priority)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_intel_suggestions_user ON intelligence_suggestions(user_id, status, suggestion_type)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_tx_intel_user_merchant ON transaction_intelligence(user_id, normalised_merchant)"))
    current = db.execute(text("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")).scalar()
    if current is None:
        db.execute(text("INSERT INTO schema_version (version) VALUES (9)"))
    elif current < 9:
        db.execute(text("UPDATE schema_version SET version = 9"))
    db.commit()


def _json(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def _loads(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def _clean(value: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    cleaned = re.sub(r"\b(VIC|NSW|QLD|SA|WA|TAS|NT|ACT|AU|AUS)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[#*]?\d{3,}\b", "", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9 &/+-]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _rule_matches(rule: dict, description: str, merchant: str | None = None) -> bool:
    target = f"{description or ''} {merchant or ''}".strip()
    pattern = rule["pattern"] or ""
    target_lower = target.lower()
    pattern_lower = pattern.lower()
    if rule["match_type"] == "exact":
        return target_lower == pattern_lower
    if rule["match_type"] == "contains":
        return pattern_lower in target_lower
    if rule["match_type"] == "prefix":
        return target_lower.startswith(pattern_lower)
    if rule["match_type"] == "suffix":
        return target_lower.endswith(pattern_lower)
    if rule["match_type"] == "regex":
        try:
            return bool(re.search(pattern, target, flags=re.IGNORECASE))
        except re.error:
            return False
    return False


def _normalise_with_rules(db: DbSession, user: User, description: str, merchant: str | None = None) -> tuple[str | None, dict | None]:
    rules = db.execute(text("SELECT * FROM intelligence_rules WHERE user_id=:user_id AND rule_type='merchant' AND is_active=1 ORDER BY priority ASC, id ASC"), {"user_id": user.id}).mappings().all()
    for rule in rules:
        rule_dict = dict(rule)
        if _rule_matches(rule_dict, description, merchant):
            return rule_dict.get("normalised_merchant"), rule_dict
    cleaned = _clean(merchant or description).lower()
    for key, value in KNOWN_MERCHANTS.items():
        if key in cleaned:
            return value, {"name": "Built-in Australian merchant seed", "pattern": key, "match_type": "contains"}
    words = _clean(merchant or description).split()
    return (words[0].title() if words else None), None


def _category_suggestion(db: DbSession, user: User, normalised: str | None, description: str, merchant: str | None) -> tuple[str | None, str, dict]:
    rules = db.execute(text("SELECT * FROM intelligence_rules WHERE user_id=:user_id AND rule_type='category' AND is_active=1 ORDER BY priority ASC, id ASC"), {"user_id": user.id}).mappings().all()
    for rule in rules:
        rule_dict = dict(rule)
        if _rule_matches(rule_dict, description, merchant or normalised):
            return rule_dict.get("category"), "high", {"reason": f"Matched user rule '{rule_dict['name']}'", "rule_id": rule_dict["id"]}
    if not normalised:
        return None, "low", {"reason": "No merchant could be normalised"}
    rows = db.execute(text("""
        SELECT category, COUNT(*) AS count FROM transactions t
        LEFT JOIN transaction_intelligence ti ON ti.transaction_id=t.id AND ti.user_id=t.user_id
        WHERE t.user_id=:user_id AND t.category IS NOT NULL
          AND (lower(t.merchant)=:merchant OR lower(t.description) LIKE :needle OR lower(ti.normalised_merchant)=:merchant)
        GROUP BY category ORDER BY count DESC
    """), {"user_id": user.id, "merchant": normalised.lower(), "needle": f"%{normalised.split()[0].lower()}%"}).mappings().all()
    total = sum(int(row["count"]) for row in rows)
    if not rows:
        return None, "low", {"reason": "No previous categorised transactions for this merchant"}
    top = rows[0]
    ratio = int(top["count"]) / max(total, 1)
    confidence = "high" if total >= 5 and ratio >= 0.8 else "medium" if total >= 2 and ratio >= 0.55 else "low"
    return top["category"], confidence, {"reason": f"{top['count']} of {total} previous {normalised} transactions used this category", "sample_size": total}


def _confidence(score: float) -> str:
    if score >= 0.78:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _upsert_suggestion(db: DbSession, user: User, suggestion_type: str, title: str, description: str, confidence: str, evidence: dict, action: dict | None) -> None:
    fingerprint = f"{suggestion_type}:{json.dumps(action or evidence, sort_keys=True, default=str)}"[:180]
    existing = db.execute(text("SELECT id, status FROM intelligence_suggestions WHERE user_id=:user_id AND fingerprint=:fingerprint"), {"user_id": user.id, "fingerprint": fingerprint}).mappings().first()
    if existing and existing["status"] in {"dismissed", "ignored", "accepted"}:
        return
    now = utcnow()
    if existing:
        db.execute(text("UPDATE intelligence_suggestions SET title=:title, description=:description, confidence=:confidence, evidence_json=:evidence, action_payload_json=:action, updated_at=:now WHERE id=:id"), {"id": existing["id"], "title": title, "description": description, "confidence": confidence, "evidence": _json(evidence), "action": _json(action), "now": now})
    else:
        db.execute(text("INSERT INTO intelligence_suggestions (user_id, suggestion_type, title, description, confidence, evidence_json, action_payload_json, status, fingerprint, created_at, updated_at) VALUES (:user_id,:type,:title,:description,:confidence,:evidence,:action,'new',:fingerprint,:now,:now)"), {"user_id": user.id, "type": suggestion_type, "title": title, "description": description, "confidence": confidence, "evidence": _json(evidence), "action": _json(action), "fingerprint": fingerprint, "now": now})


def _transaction_rows(db: DbSession, user: User, days: int = 540) -> list[dict]:
    start = (utcnow().date() - timedelta(days=days)).isoformat()
    return [dict(row) for row in db.execute(text("""
        SELECT id, account_id, transaction_date, amount_cents, transaction_type, description, merchant, category, source, status, raw_description
        FROM transactions WHERE user_id=:user_id AND transaction_date >= :start AND transaction_type IN ('expense','income') ORDER BY transaction_date ASC
    """), {"user_id": user.id, "start": start}).mappings().all()]


def process_transactions(db: DbSession, user: User) -> dict:
    ensure_intelligence_schema(db)
    rows = _transaction_rows(db, user)
    now = utcnow()
    processed = 0
    merchant_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        normalised, rule = _normalise_with_rules(db, user, row["description"], row.get("merchant"))
        category, cat_confidence, cat_evidence = _category_suggestion(db, user, normalised, row["description"], row.get("merchant"))
        db.execute(text("""
            INSERT INTO transaction_intelligence (user_id, transaction_id, normalised_merchant, suggested_category, category_confidence, category_evidence, created_at, updated_at)
            VALUES (:user_id,:tx,:merchant,:category,:confidence,:evidence,:now,:now)
            ON CONFLICT(user_id, transaction_id) DO UPDATE SET normalised_merchant=:merchant, suggested_category=:category, category_confidence=:confidence, category_evidence=:evidence, updated_at=:now
        """), {"user_id": user.id, "tx": row["id"], "merchant": normalised, "category": category, "confidence": cat_confidence, "evidence": _json(cat_evidence), "now": now})
        if normalised and normalised != row.get("merchant"):
            _upsert_suggestion(db, user, "merchant_normalisation", f"Normalise {row['description']} to {normalised}", f"Fynvo can preserve the original description and use {normalised} as the cleaner merchant name.", "medium" if rule else "low", {"original_description": row["description"], "normalised_merchant": normalised, "rule": rule}, {"normalised_merchant": normalised})
        if category and row.get("category") != category:
            _upsert_suggestion(db, user, "category_suggestion", f"Categorise {normalised or row['description']} as {category}", cat_evidence["reason"], cat_confidence, {"transaction_id": row["id"], "merchant": normalised, "suggested_category": category, **cat_evidence}, {"transaction_id": row["id"], "category": category})
        merchant_groups[(row["transaction_type"], normalised or _clean(row["description"]).title())].append(row)
        processed += 1
    recurring = _detect_recurring(db, user, merchant_groups)
    trends = _generate_trends(db, user, rows)
    anomalies = _detect_anomalies(db, user, rows)
    db.commit()
    return {"processed_transactions": processed, "recurring_suggestions": recurring, "trend_count": len(trends), "anomaly_count": anomalies}


def _cadence(days: list[int]) -> tuple[str | None, float]:
    if len(days) < 2:
        return None, 0
    avg = mean(days)
    patterns = [("weekly", 7), ("fortnightly", 14), ("every_4_weeks", 28), ("monthly", 30.4), ("quarterly", 91.3), ("annual", 365)]
    name, target = min(patterns, key=lambda item: abs(avg - item[1]))
    variance = mean(abs(day - target) for day in days)
    score = max(0, 1 - variance / max(target, 1))
    return name, score


def _detect_recurring(db: DbSession, user: User, groups: dict[tuple[str, str], list[dict]]) -> int:
    created = 0
    existing_expense_names = {str(row[0]).lower() for row in db.execute(text("SELECT name FROM recurring_expenses WHERE user_id=:user_id AND is_active=1"), {"user_id": user.id}).all()}
    existing_income_names = {str(row[0]).lower() for row in db.execute(text("SELECT name FROM income_sources WHERE user_id=:user_id AND is_active=1"), {"user_id": user.id}).all()}
    for (direction, merchant), rows in groups.items():
        if len(rows) < 3 or direction not in {"expense", "income"}:
            continue
        lowered = merchant.lower()
        if direction == "expense" and any(lowered in name or name in lowered for name in existing_expense_names):
            continue
        if direction == "income" and any(lowered in name or name in lowered for name in existing_income_names):
            continue
        dates = [row["transaction_date"] if isinstance(row["transaction_date"], date) else date.fromisoformat(str(row["transaction_date"])[:10]) for row in rows]
        dates.sort()
        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        frequency, cadence_score = _cadence(gaps)
        amounts = [abs(int(row["amount_cents"])) for row in rows]
        amount_score = 1 - (max(amounts) - min(amounts)) / max(mean(amounts), 1)
        score = max(0, min(1, cadence_score * 0.65 + amount_score * 0.35))
        if frequency and score >= 0.55:
            avg_amount = round(mean(amounts))
            confidence = _confidence(score)
            suggestion_type = "recurring_income_detected" if direction == "income" else "recurring_expense_detected"
            title = f"{merchant} appears to be {frequency.replace('_', ' ')} {direction}"
            description = f"{len(rows)} transactions from {merchant} occurred around a {frequency.replace('_', ' ')} cadence with an average amount of {cents_to_decimal(avg_amount)}."
            _upsert_suggestion(db, user, suggestion_type, title, description, confidence, {"merchant": merchant, "transactions": len(rows), "gaps_days": gaps, "average_amount": cents_to_decimal(avg_amount), "frequency": frequency}, {"merchant": merchant, "amount_cents": avg_amount, "frequency": frequency, "direction": direction, "next_date": str(dates[-1] + timedelta(days=round(mean(gaps))))})
            _detect_amount_change(db, user, merchant, direction, rows, frequency)
            created += 1
    return created


def _detect_amount_change(db: DbSession, user: User, merchant: str, direction: str, rows: list[dict], frequency: str) -> None:
    if len(rows) < 5:
        return
    amounts = [abs(int(row["amount_cents"])) for row in rows]
    old = round(mean(amounts[:-2]))
    new = round(mean(amounts[-2:]))
    if old <= 0:
        return
    delta = new - old
    if abs(delta) / old < 0.12:
        return
    change = "increased" if delta > 0 else "decreased"
    title = f"{merchant} appears to have {change}"
    description = f"Previous payments averaged {cents_to_decimal(old)}. The last two averaged {cents_to_decimal(new)}, a change of {cents_to_decimal(abs(delta))}."
    _upsert_suggestion(db, user, "recurring_amount_change", title, description, "medium", {"merchant": merchant, "old_amount": cents_to_decimal(old), "new_amount": cents_to_decimal(new), "frequency": frequency, "direction": direction}, {"merchant": merchant, "old_amount_cents": old, "new_amount_cents": new, "frequency": frequency, "direction": direction, "effective_from": str(rows[-2]["transaction_date"])})


def _period_start(d: date, weeks: int) -> date:
    return d - timedelta(days=weeks * 7)


def _generate_trends(db: DbSession, user: User, rows: list[dict]) -> list[dict]:
    today = utcnow().date()
    current_start = _period_start(today, 8)
    previous_start = _period_start(today, 16)
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"current": 0, "previous": 0})
    for row in rows:
        if row["transaction_type"] != "expense" or not row.get("category"):
            continue
        tx_date = row["transaction_date"] if isinstance(row["transaction_date"], date) else date.fromisoformat(str(row["transaction_date"])[:10])
        bucket = "current" if tx_date >= current_start else "previous" if tx_date >= previous_start else None
        if bucket:
            by_category[row["category"]][bucket] += abs(int(row["amount_cents"]))
    trends = []
    for category, values in by_category.items():
        if values["current"] == 0 or values["previous"] == 0:
            continue
        change = values["current"] - values["previous"]
        percent = round((change / values["previous"]) * 100, 1)
        state = "increasing" if percent >= 15 else "decreasing" if percent <= -15 else "stable"
        trend = {"category": category, "current_8_weeks": cents_to_decimal(values["current"]), "previous_8_weeks": cents_to_decimal(values["previous"]), "change": cents_to_decimal(change), "percent_change": percent, "state": state, "evidence": f"Compared the latest 8 weeks with the previous 8 weeks for {category}."}
        trends.append(trend)
        if abs(percent) >= 15:
            _upsert_suggestion(db, user, "spending_trend", f"{category} spending is {state}", f"{category} changed by {percent}% compared with the previous 8 weeks.", "medium", trend, {"category": category})
    return trends


def _detect_anomalies(db: DbSession, user: User, rows: list[dict]) -> int:
    groups: dict[str, list[int]] = defaultdict(list)
    count = 0
    for row in rows:
        if row["transaction_type"] == "expense" and row.get("category"):
            groups[row["category"]].append(abs(int(row["amount_cents"])))
    for row in rows:
        category = row.get("category")
        if row["transaction_type"] != "expense" or not category or len(groups[category]) < 5:
            continue
        baseline = mean(groups[category][:-1] or groups[category])
        amount = abs(int(row["amount_cents"]))
        if baseline > 0 and amount >= baseline * 1.8 and amount - baseline >= 5000:
            evidence = {"transaction_id": row["id"], "category": category, "amount": cents_to_decimal(amount), "baseline_average": cents_to_decimal(round(baseline)), "difference_percent": round(((amount - baseline) / baseline) * 100, 1), "period": "recent category history"}
            db.execute(text("UPDATE transaction_intelligence SET anomaly_status='higher_than_usual', anomaly_evidence=:evidence, updated_at=:now WHERE user_id=:user_id AND transaction_id=:tx"), {"user_id": user.id, "tx": row["id"], "evidence": _json(evidence), "now": utcnow()})
            _upsert_suggestion(db, user, "unusual_spending", f"Higher than usual {category} transaction", f"This transaction is {evidence['difference_percent']}% above the recent {category} average.", "medium", evidence, {"transaction_id": row["id"]})
            count += 1
    return count


def _suggestion(row: Any) -> dict:
    item = dict(row)
    item["evidence"] = _loads(item.pop("evidence_json"), {})
    item["action_payload"] = _loads(item.pop("action_payload_json"), {})
    return item


@router.post("/process")
def process(current_user: User = USER, db: DbSession = DB):
    return process_transactions(db, current_user)


@router.get("/suggestions")
def list_suggestions(status_filter: str = "new", current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    rows = db.execute(text("SELECT * FROM intelligence_suggestions WHERE user_id=:user_id AND (:status='all' OR status=:status) ORDER BY CASE confidence WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC"), {"user_id": current_user.id, "status": status_filter}).mappings().all()
    return [_suggestion(row) for row in rows]


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
    suggestion = _suggestion(row)
    action = suggestion.get("action_payload") or {}
    now = utcnow()
    if suggestion["suggestion_type"] == "category_suggestion" and action.get("transaction_id"):
        db.execute(text("UPDATE transactions SET category=:category, updated_at=:now WHERE id=:tx AND user_id=:user_id"), {"category": action["category"], "tx": action["transaction_id"], "user_id": current_user.id, "now": now})
    elif suggestion["suggestion_type"] == "merchant_normalisation" and action.get("normalised_merchant"):
        pattern = suggestion["evidence"].get("original_description", action["normalised_merchant"])
        create_rule(db, current_user, {"rule_type": "merchant", "name": f"Normalise {action['normalised_merchant']}", "match_type": "contains", "pattern": pattern.split()[0], "normalised_merchant": action["normalised_merchant"], "priority": 100})
    elif suggestion["suggestion_type"] == "recurring_expense_detected":
        db.execute(text("INSERT INTO recurring_expenses (user_id,name,amount_cents,frequency,interval_count,next_due_date,category,is_active,source,created_at,updated_at) VALUES (:user_id,:name,:amount,:frequency,1,:next_due,NULL,1,'intelligence',:now,:now)"), {"user_id": current_user.id, "name": action["merchant"], "amount": action["amount_cents"], "frequency": action["frequency"], "next_due": action["next_date"], "now": now})
    elif suggestion["suggestion_type"] == "recurring_income_detected":
        db.execute(text("INSERT INTO income_sources (user_id,name,amount_cents,frequency,interval_count,next_payment_date,is_active,source,created_at,updated_at) VALUES (:user_id,:name,:amount,:frequency,1,:next_date,1,'intelligence',:now,:now)"), {"user_id": current_user.id, "name": action["merchant"], "amount": action["amount_cents"], "frequency": action["frequency"], "next_date": action["next_date"], "now": now})
    elif suggestion["suggestion_type"] == "recurring_amount_change":
        table = "recurring_expenses" if action.get("direction") == "expense" else "income_sources"
        name_col = "name"
        record = db.execute(text(f"SELECT id FROM {table} WHERE user_id=:user_id AND lower({name_col}) LIKE :name ORDER BY updated_at DESC LIMIT 1"), {"user_id": current_user.id, "name": f"%{action['merchant'].lower()}%"}).mappings().first()
        if record:
            db.execute(text("INSERT INTO effective_amount_changes (user_id, record_type, record_id, new_amount_cents, effective_from, source, notes, created_at, updated_at) VALUES (:user_id,:record_type,:record_id,:amount,:effective_from,'intelligence','Accepted recurring amount change suggestion',:now,:now)"), {"user_id": current_user.id, "record_type": "recurring_expense" if action.get("direction") == "expense" else "income", "record_id": record["id"], "amount": action["new_amount_cents"], "effective_from": action["effective_from"], "now": now})
    db.execute(text("UPDATE intelligence_suggestions SET status='accepted', accepted_at=:now, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"id": suggestion_id, "user_id": current_user.id, "now": now})
    db.commit()
    return {"status": "accepted", "suggestion_type": suggestion["suggestion_type"]}


@router.get("/rules")
def list_rules(current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    return [dict(row) for row in db.execute(text("SELECT * FROM intelligence_rules WHERE user_id=:user_id ORDER BY priority ASC, id ASC"), {"user_id": current_user.id}).mappings().all()]


def create_rule(db: DbSession, user: User, payload: dict[str, Any]) -> dict:
    ensure_intelligence_schema(db)
    rule_type = payload.get("rule_type")
    match_type = payload.get("match_type") or "contains"
    if rule_type not in RULE_TYPES or match_type not in MATCH_TYPES:
        raise HTTPException(status_code=400, detail="Invalid rule type or match type")
    if match_type == "regex":
        try:
            re.compile(payload.get("pattern") or "")
        except re.error as exc:
            raise HTTPException(status_code=400, detail="Invalid regular expression") from exc
    now = utcnow()
    db.execute(text("""
        INSERT INTO intelligence_rules (user_id, rule_type, name, match_type, pattern, normalised_merchant, category, priority, apply_automatically, is_active, notes, created_at, updated_at)
        VALUES (:user_id,:rule_type,:name,:match_type,:pattern,:merchant,:category,:priority,:auto,:active,:notes,:now,:now)
    """), {"user_id": user.id, "rule_type": rule_type, "name": payload.get("name") or payload.get("pattern") or "Rule", "match_type": match_type, "pattern": payload.get("pattern") or "", "merchant": payload.get("normalised_merchant"), "category": payload.get("category"), "priority": int(payload.get("priority", 100)), "auto": bool(payload.get("apply_automatically", True)), "active": bool(payload.get("is_active", True)), "notes": payload.get("notes"), "now": now})
    rule = db.execute(text("SELECT * FROM intelligence_rules WHERE id=last_insert_rowid()")).mappings().first()
    return dict(rule)


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
    values = {"id": rule_id, "user_id": current_user.id, "now": utcnow(), **updates}
    assignments = [f"{key}=:{key}" for key in updates]
    if assignments:
        db.execute(text(f"UPDATE intelligence_rules SET {', '.join(assignments)}, updated_at=:now WHERE id=:id AND user_id=:user_id"), values)
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
    matches = [row for row in _transaction_rows(db, current_user) if _rule_matches(dict(rule), row["description"], row.get("merchant"))]
    return {"match_count": len(matches), "transactions": matches[:25]}


@router.post("/rules/{rule_id}/apply-history")
def apply_rule_history(rule_id: int, current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    rule = db.execute(text("SELECT * FROM intelligence_rules WHERE id=:id AND user_id=:user_id"), {"id": rule_id, "user_id": current_user.id}).mappings().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    count = 0
    now = utcnow()
    for row in _transaction_rows(db, current_user, 3650):
        if _rule_matches(dict(rule), row["description"], row.get("merchant")):
            if rule["rule_type"] == "merchant" and rule["normalised_merchant"]:
                db.execute(text("UPDATE transactions SET merchant=:merchant, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"merchant": rule["normalised_merchant"], "id": row["id"], "user_id": current_user.id, "now": now})
                count += 1
            if rule["rule_type"] == "category" and rule["category"]:
                db.execute(text("UPDATE transactions SET category=:category, updated_at=:now WHERE id=:id AND user_id=:user_id"), {"category": rule["category"], "id": row["id"], "user_id": current_user.id, "now": now})
                count += 1
    db.commit()
    return {"updated": count}


@router.get("/merchants")
def merchant_summary(current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    process_transactions(db, current_user)
    rows = db.execute(text("""
        SELECT ti.normalised_merchant AS merchant, COUNT(*) AS count, SUM(ABS(t.amount_cents)) AS total, AVG(ABS(t.amount_cents)) AS average,
               MIN(t.transaction_date) AS first_seen, MAX(t.transaction_date) AS last_seen
        FROM transaction_intelligence ti JOIN transactions t ON t.id=ti.transaction_id
        WHERE ti.user_id=:user_id AND ti.normalised_merchant IS NOT NULL AND t.transaction_type='expense'
        GROUP BY ti.normalised_merchant ORDER BY total DESC
    """), {"user_id": current_user.id}).mappings().all()
    result = []
    for row in rows:
        categories = db.execute(text("SELECT t.category, COUNT(*) AS count FROM transaction_intelligence ti JOIN transactions t ON t.id=ti.transaction_id WHERE ti.user_id=:user_id AND ti.normalised_merchant=:merchant AND t.category IS NOT NULL GROUP BY t.category ORDER BY count DESC"), {"user_id": current_user.id, "merchant": row["merchant"]}).mappings().first()
        result.append({"merchant": row["merchant"], "transaction_count": row["count"], "total_spend": cents_to_decimal(row["total"] or 0), "average_transaction": cents_to_decimal(round(row["average"] or 0)), "first_seen": str(row["first_seen"]), "last_seen": str(row["last_seen"]), "common_category": categories["category"] if categories else None})
    return result


@router.get("/trends")
def trends(current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    rows = _transaction_rows(db, current_user)
    return _generate_trends(db, current_user, rows)


@router.post("/transactions/{transaction_id}/exclude-baseline")
def exclude_transaction_baseline(transaction_id: int, current_user: User = USER, db: DbSession = DB):
    ensure_intelligence_schema(db)
    db.execute(text("""
        INSERT INTO transaction_intelligence (user_id, transaction_id, exclude_from_baseline, created_at, updated_at)
        VALUES (:user_id,:tx,1,:now,:now)
        ON CONFLICT(user_id, transaction_id) DO UPDATE SET exclude_from_baseline=1, updated_at=:now
    """), {"user_id": current_user.id, "tx": transaction_id, "now": utcnow()})
    db.commit()
    return {"status": "excluded_from_baseline"}
