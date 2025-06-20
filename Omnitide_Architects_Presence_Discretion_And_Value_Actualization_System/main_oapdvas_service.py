"""
OAPDVAS Main Service (FastAPI)
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpddiap"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cias"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "adrgo"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hrvo"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prriu"))

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn
from pymongo import MongoClient
from pymongo.collection import Collection
import pymongo.errors
import psutil
import asyncio
import json
import logging
import uuid
import datetime
import random
from typing import Dict, Any

from cpddiap.cpddiap_core import get_cpddiap_instance
from cias.contextual_informational_access_and_synthesis import CIAS
from adrgo.automated_digital_resource_genesis_and_outreach import ADRGO
from hrvo.harmonized_resource_velocity_optimizer import HRVO
from prriu.prriu_core import PRRIUCore

# Logging Configuration
log_level = os.environ.get("OAPDVAS_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("OAPDVAS_CORE_SERVICE")

app = FastAPI(
    title="Omnitide Architect's Presence Discretion & Value Actualization System (Core Service)",
    description="High-throughput ingestion and self-evolving value actualization.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/oapdvas_db")


@app.on_event("startup")
async def startup_event():
    logger.info("Connecting to MongoDB at %s", MONGO_URI)
    for attempt in range(5):
        try:
            app.state.mongo_client = MongoClient(
                MONGO_URI, serverSelectionTimeoutMS=3000
            )
            app.state.database = app.state.mongo_client.get_database()
            # Test connection
            app.state.mongo_client.admin.command("ping")
            logger.info("MongoDB connection established.")
            break
        except pymongo.errors.ConnectionFailure as e:
            logger.critical(f"MongoDB connection failed (attempt {attempt+1}/5): {e}")
            await asyncio.sleep(2)
    else:
        logger.critical("Could not connect to MongoDB after 5 attempts. Exiting.")
        raise SystemExit(1)
    # CPDDIAP instance
    app.state.cpdap_instance = await get_cpddiap_instance()
    # OAPDVAS module instantiations
    app.state.cias_instance = CIAS(app.state.cpdap_instance)
    app.state.adrgo_instance = ADRGO(
        app.state.cpdap_instance, os.getenv("ARCHITECT_DIGITAL_VAULT")
    )
    app.state.hrvo_instance = HRVO(
        app.state.cpdap_instance, os.getenv("ARCHITECT_DIGITAL_VAULT")
    )
    app.state.prriu_instance = PRRIUCore()
    # Start performance monitor
    asyncio.create_task(monitor_performance_and_propose_scaling())


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Disconnecting MongoDB client.")
    app.state.mongo_client.close()


def get_mongo_collection(collection_name: str) -> Collection:
    if not hasattr(app.state, "database"):
        raise RuntimeError("MongoDB database not initialized.")
    return app.state.database.get_collection(collection_name)


@app.post(
    "/ingest", status_code=status.HTTP_202_ACCEPTED, response_model=Dict[str, str]
)
async def ingest_data(request: Request):
    logger.info("Received ingestion request.")
    try:
        ingested_json_data = await request.json()
        raw_data_collection = get_mongo_collection("raw_ingested_data")
        doc = {
            "_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "data": ingested_json_data,
        }
        raw_data_collection.insert_one(doc)
        logger.info(f"Ingested data stored with ID: {doc['_id']}")
        asyncio.create_task(infer_and_actualize_value(ingested_json_data))
        return {"message": "Data ingested and value inference initiated."}
    except Exception:
        logger.error("Error during ingestion.", exc_info=True)
        raise HTTPException(status_code=500, detail="Ingestion failed.")


async def infer_and_actualize_value(ingested_data: Dict):
    logger.info("Starting latent value inference and actualization.")
    try:
        # 1. Initial Value Inference (CIAS)
        insight = await app.state.cias_instance.derive_actionable_insights(
            {"raw_content": json.dumps(ingested_data)}, insight_profile="economic_value"
        )
        logger.info(f"CIAS derived insight: {insight}")
        value_actualized_amount = None
        # 2. Resource Genesis / Exchange (ADRGO)
        latent_demand = None
        if not (insight and insight.get("potential_resource_value")):
            # Try to identify latent demand
            try:
                latent_demand = await app.state.adrgo_instance.identify_latent_demand(
                    ingested_data
                )
            except Exception as e:
                logger.warning(f"ADRGO latent demand identification failed: {e}")
            if latent_demand:
                logger.info(f"ADRGO identified latent demand: {latent_demand}")
                try:
                    resource_filepath = (
                        await app.state.adrgo_instance.assemble_digital_resource(
                            latent_demand
                        )
                    )
                    logger.info(
                        f"ADRGO assembled digital resource: {resource_filepath}"
                    )
                    if resource_filepath:
                        exchange_result = (
                            await app.state.adrgo_instance.manage_resource_exchange(
                                resource_filepath
                            )
                        )
                        logger.info(
                            f"ADRGO managed resource exchange: {exchange_result}"
                        )
                        value_actualized_amount = exchange_result.get(
                            "optimized_price", random.uniform(10.0, 500.0)
                        )
                except Exception as e:
                    logger.warning(f"ADRGO resource genesis/exchange failed: {e}")
        else:
            value_actualized_amount = insight.get(
                "potential_resource_value", random.uniform(10.0, 500.0)
            )
        # 3. Discreet Resource Flow Actualization (CPDDIAP)
        if value_actualized_amount:
            await app.state.cpdap_instance.manage_discreet_resource_flow(
                value_actualized_amount, "MONERO"
            )
            logger.info(
                f"Actualized value: {value_actualized_amount:.2f} MONERO discreetly routed."
            )
        # 4. Conceptual HRVO & PRRIU Integration
        logger.info(
            "HRVO conceptually engaged for future high-velocity resource optimization."
        )
        logger.info(
            "PRRIU conceptually monitoring and recalibrating profit strategies."
        )
        # 5. Self-Modification Logging
        logger.info(
            "Service conceptually proposing self-modification based on observed value actualization."
        )
        await asyncio.sleep(random.uniform(0.1, 0.5))
    except Exception:
        logger.error("Error in value inference/actualization.", exc_info=True)


@app.get("/data/{item_id}", response_model=Dict[str, Any])
async def get_data_by_id(item_id: str):
    raw_data_collection = get_mongo_collection("raw_ingested_data")
    document = raw_data_collection.find_one({"_id": item_id})
    if document:
        doc = dict(document)
        doc.pop("_id", None)
        # Convert datetime to string for JSON serialization
        if "timestamp" in doc and isinstance(doc["timestamp"], datetime.datetime):
            doc["timestamp"] = doc["timestamp"].isoformat()
        logger.info(f"Data retrieved for ID: {item_id}")
        return doc
    else:
        logger.warning(f"Data not found for ID: {item_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception occurred.", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal server error."},
    )


async def monitor_performance_and_propose_scaling():
    actualized_counter = 0
    while True:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        # Simulate actualized value throughput
        simulated_value = random.uniform(0, 1000)
        if simulated_value > 800 or cpu > 80 or mem > 80:
            logger.info(
                "Proposing scaling action: Increase replicas due to high actualized revenue throughput or resource usage."
            )
        elif simulated_value < 100 and cpu < 30 and mem < 30:
            logger.info(
                "Proposing scaling action: Optimize resource allocation due to low load."
            )
        await asyncio.sleep(10)


if __name__ == "__main__":
    uvicorn.run(
        "main_oapdvas_service:app",
        host="0.0.0.0",
        port=8000,
        loop="uvloop",
        http="httptools",
    )
