import uvicorn
from fastapi import FastAPI, Request, HTTPException
from omnitide.transformer import transform_data, evolve_transformation_logic
from omnitide.db import store_data, query_data, ensure_db_connection
import asyncio
import logging
from fastapi import APIRouter
from omnitide.self_patch import apply_patch, monitor_and_optimize_transformation_path

app = FastAPI()

# Setup advanced logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("omnitide")

router = APIRouter()


@app.on_event("startup")
async def startup_event():
    await ensure_db_connection()
    await evolve_transformation_logic()
    asyncio.create_task(monitor_and_optimize_transformation_path())
    logger.info("Omnitide Nexus Microservice started and monitoring.")


@app.post("/architects_patch/{patch_id}")
async def architects_patch(patch_id: str, patch_code: dict):
    """Live patch the transformation logic at runtime."""
    try:
        result = await apply_patch(patch_id, patch_code)
        logger.info(f"Patch {patch_id} applied: {result}")
        return {"status": "patched", "patch_id": patch_id, "result": result}
    except Exception as e:
        logger.error(f"Patch {patch_id} failed: {e}")
        raise HTTPException(status_code=500, detail=f"Patch failed: {e}")


@app.post("/ingest")
async def ingest(request: Request):
    logger.info("Received /ingest request")
    try:
        data = await request.json()
        transformed, meta = await transform_data(data)
        await store_data(transformed, meta)
        logger.info(f"Ingested and transformed data: {meta}")
        return {"status": "success", "meta": meta}
    except Exception as e:
        logger.warning(f"Ingest error: {e}, attempting self-heal.")
        await evolve_transformation_logic(error=str(e))
        try:
            data = await request.json()
            transformed, meta = await transform_data(data)
            await store_data(transformed, meta)
            logger.info(f"Self-healed ingest: {meta}")
            return {"status": "success", "meta": meta, "self_healed": True}
        except Exception as e2:
            logger.critical(f"Ingestion failed after self-heal: {e2}")
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {e2}")


@app.get("/query/{item_id}")
async def query_by_id(item_id: str):
    result = await query_data(item_id)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Item not found")


@app.get("/query")
async def query_by_param(param: str = None, value: str = None):
    results = await query_data(param=param, value=value)
    return results


if __name__ == "__main__":
    uvicorn.run("omnitide.main:app", host="0.0.0.0", port=8080, reload=True)
