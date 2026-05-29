"""One-off: add deepseek-v4-pro to active system_configs (no DB reset)."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402

MODEL = "deepseek-v4-pro"
PROVIDER = "deepseek"
API_BASE = "https://api.deepseek.com"


def main() -> None:
    env_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    env_ok = bool(env_key) and not env_key.startswith("REPLACE_") and "your_" not in env_key
    print(f"env_key_available={env_ok}")

    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    doc = db.system_configs.find_one({"is_active": True})
    if not doc:
        raise SystemExit("no active system_configs document")

    llm_configs = doc.get("llm_configs", [])
    if any(c.get("provider") == PROVIDER and c.get("model_name") == MODEL for c in llm_configs):
        print("llm_config already present")
    else:
        template = next(
            (
                c
                for c in llm_configs
                if c.get("provider") == PROVIDER and c.get("model_name") == "deepseek-chat"
            ),
            None,
        )
        new_cfg = {
            "provider": PROVIDER,
            "model_name": MODEL,
            "model_display_name": "DeepSeek V4 Pro",
            "api_key": "",
            "api_base": API_BASE,
            "max_tokens": (template or {}).get("max_tokens", 6000),
            "temperature": (template or {}).get("temperature", 0.7),
            "timeout": (template or {}).get("timeout", 180),
            "retry_times": (template or {}).get("retry_times", 3),
            "enabled": True,
            "description": "DeepSeek official V4 Pro",
            "model_category": "",
            "custom_endpoint": None,
            "enable_memory": False,
            "enable_debug": False,
            "priority": 0,
            "input_price_per_1k": (template or {}).get("input_price_per_1k", 0.000435),
            "output_price_per_1k": (template or {}).get("output_price_per_1k", 0.00087),
            "currency": "USD",
            "capability_level": 5,
            "suitable_roles": ["both"],
            "features": ["reasoning", "long_context", "tool_calling"],
            "recommended_depths": ["标准", "深度", "全面"],
            "performance_metrics": {"speed": 3, "cost": 3, "quality": 5},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = db.system_configs.update_one(
            {"_id": doc["_id"]},
            {"$push": {"llm_configs": new_cfg}},
        )
        print(f"llm_config push modified={result.modified_count}")

    # Ensure enabled + api_base if re-run
    db.system_configs.update_one(
        {
            "_id": doc["_id"],
            "llm_configs": {
                "$elemMatch": {"provider": PROVIDER, "model_name": MODEL},
            },
        },
        {
            "$set": {
                "llm_configs.$.enabled": True,
                "llm_configs.$.api_base": API_BASE,
                "llm_configs.$.api_key": "",
                "llm_configs.$.updated_at": datetime.utcnow(),
            }
        },
    )

    cat = db.model_catalog.find_one({"provider": PROVIDER})
    if cat:
        names = {m.get("name") for m in cat.get("models", [])}
        if MODEL not in names:
            db.model_catalog.update_one(
                {"provider": PROVIDER},
                {
                    "$push": {
                        "models": {
                            "name": MODEL,
                            "display_name": "DeepSeek V4 Pro",
                            "description": "DeepSeek official V4 Pro API model",
                            "context_length": 1000000,
                            "max_tokens": None,
                            "input_price_per_1k": 0.000435,
                            "output_price_per_1k": 0.00087,
                            "currency": "USD",
                            "is_deprecated": False,
                            "release_date": None,
                            "capabilities": ["reasoning", "tool_calling", "long_context"],
                        }
                    }
                },
            )
            print("model_catalog entry added")
    client.close()
    print("done")


if __name__ == "__main__":
    main()
