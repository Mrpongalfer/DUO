"""
Scheduler: Provides scheduling capabilities for recurring tasks.

Uses APScheduler to schedule and manage recurring orchestration tasks.
"""

import logging
import threading
import asyncio
from typing import Any, Dict, List, Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.date import DateTrigger
except ImportError:
    logging.error(
        "APScheduler not installed. Scheduling functionality will be disabled."
    )
    BackgroundScheduler = None
    MemoryJobStore = None
    SQLAlchemyJobStore = None
    CronTrigger = None
    IntervalTrigger = None
    DateTrigger = None

from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.games.nexus_omniengine_v3.core.config import Config

logger = get_logger(__name__)
config = Config()


class SchedulerService:
    """Service for scheduling recurring orchestration tasks."""

    def __init__(self, orchestrator=None):
        """
        Initialize the scheduler service.

        Args:
            orchestrator: The orchestrator instance to use for executing instructions
        """
        self.orchestrator = orchestrator
        self.scheduler = None
        self.job_store_path = "scheduler.sqlite"
        self.lock = threading.RLock()

        # Initialize scheduler if APScheduler is available
        if BackgroundScheduler is not None:
            self._init_scheduler()

    def _init_scheduler(self):
        """Initialize the scheduler."""
        with self.lock:
            try:
                # Configure job stores
                job_stores = {
                    "default": MemoryJobStore(),
                }

                # Try to set up persistent storage if enabled
                use_persistent = config.get("scheduler", "persistent", False)
                if use_persistent:
                    try:
                        job_stores["persistent"] = SQLAlchemyJobStore(
                            url=f"sqlite:///{self.job_store_path}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to set up persistent job store: {str(e)}"
                        )

                # Create scheduler
                self.scheduler = BackgroundScheduler(jobstores=job_stores)

                logger.info("Scheduler service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize scheduler: {str(e)}")
                self.scheduler = None

    def start(self):
        """Start the scheduler."""
        with self.lock:
            if self.scheduler is None:
                logger.error("Cannot start scheduler: APScheduler not available")
                return False

            if not self.scheduler.running:
                try:
                    self.scheduler.start()
                    logger.info("Scheduler service started")
                    return True
                except Exception as e:
                    logger.error(f"Failed to start scheduler: {str(e)}")
                    return False

            return True

    def stop(self):
        """Stop the scheduler."""
        with self.lock:
            if self.scheduler is not None and self.scheduler.running:
                try:
                    self.scheduler.shutdown()
                    logger.info("Scheduler service stopped")
                    return True
                except Exception as e:
                    logger.error(f"Failed to stop scheduler: {str(e)}")
                    return False

            return True

    def schedule_instruction(
        self,
        instruction: Dict[str, Any],
        trigger: str,
        trigger_args: Dict[str, Any],
        job_id: str = None,
        replace_existing: bool = True,
        persistent: bool = False,
    ) -> Optional[str]:
        """
        Schedule an instruction to be executed.

        Args:
            instruction: The instruction to execute
            trigger: Type of trigger ('interval', 'cron', 'date')
            trigger_args: Arguments for the trigger
            job_id: Optional job ID (generated if not provided)
            replace_existing: Whether to replace existing job with same ID
            persistent: Whether to store the job persistently

        Returns:
            Job ID if successful, None otherwise
        """
        with self.lock:
            if self.scheduler is None:
                logger.error("Cannot schedule instruction: APScheduler not available")
                return None

            # Generate job ID if not provided
            if job_id is None:
                import uuid

                job_id = f"job_{uuid.uuid4().hex[:8]}"

            # Create the trigger
            if trigger == "interval":
                # Convert interval arguments to timedelta
                interval_args = {}
                for key, value in trigger_args.items():
                    if key in ["weeks", "days", "hours", "minutes", "seconds"]:
                        interval_args[key] = int(value)

                if not interval_args:
                    logger.error("Invalid interval trigger arguments")
                    return None

                job_trigger = IntervalTrigger(**interval_args)

            elif trigger == "cron":
                # Direct pass through of cron arguments
                job_trigger = CronTrigger(**trigger_args)

            elif trigger == "date":
                # Schedule for a specific date/time
                if "run_date" in trigger_args:
                    job_trigger = DateTrigger(run_date=trigger_args["run_date"])
                else:
                    logger.error("Missing run_date in date trigger arguments")
                    return None

            else:
                logger.error(f"Unknown trigger type: {trigger}")
                return None

            # Determine job store
            job_store = "persistent" if persistent else "default"
            if persistent and "persistent" not in self.scheduler.jobstores:
                logger.warning("Persistent job store not available, using default")
                job_store = "default"

            # Add the job
            try:
                self.scheduler.add_job(
                    self._execute_scheduled_instruction,
                    trigger=job_trigger,
                    args=[instruction, job_id],
                    id=job_id,
                    replace_existing=replace_existing,
                    jobstore=job_store,
                )

                logger.info(f"Scheduled instruction with job ID {job_id}")
                return job_id

            except Exception as e:
                logger.error(f"Failed to schedule job: {str(e)}")
                return None

    def _execute_scheduled_instruction(self, instruction: Dict[str, Any], job_id: str):
        """
        Execute a scheduled instruction.

        Args:
            instruction: The instruction to execute
            job_id: Job ID
        """
        if self.orchestrator is None:
            logger.error("Cannot execute scheduled instruction: Orchestrator not set")
            return

        try:
            logger.info(f"Executing scheduled instruction (job ID: {job_id})")

            # Create an event loop for asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Execute the instruction
            result = loop.run_until_complete(
                self.orchestrator.execute_instruction(instruction)
            )

            # Close the loop
            loop.close()

            # Log the result
            if result.get("success", False):
                logger.info(
                    f"Scheduled instruction executed successfully (job ID: {job_id})"
                )
            else:
                logger.error(
                    f"Scheduled instruction failed (job ID: {job_id}): {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(
                f"Error executing scheduled instruction (job ID: {job_id}): {str(e)}"
            )

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.

        Args:
            job_id: ID of the job to remove

        Returns:
            bool: True if removal was successful
        """
        with self.lock:
            if self.scheduler is None:
                logger.error("Cannot remove job: APScheduler not available")
                return False

            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed job with ID {job_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to remove job {job_id}: {str(e)}")
                return False

    def get_jobs(self) -> List[Dict[str, Any]]:
        """
        Get list of scheduled jobs.

        Returns:
            List of job dictionaries
        """
        with self.lock:
            if self.scheduler is None:
                logger.error("Cannot get jobs: APScheduler not available")
                return []

            try:
                jobs = []
                for job in self.scheduler.get_jobs():
                    jobs.append(
                        {
                            "id": job.id,
                            "name": job.name,
                            "trigger": str(job.trigger),
                            "next_run_time": (
                                job.next_run_time.isoformat()
                                if job.next_run_time
                                else None
                            ),
                            "jobstore": job.jobstore,
                        }
                    )

                return jobs

            except Exception as e:
                logger.error(f"Failed to get jobs: {str(e)}")
                return []

    def pause_job(self, job_id: str) -> bool:
        """
        Pause a scheduled job.

        Args:
            job_id: ID of the job to pause

        Returns:
            bool: True if pause was successful
        """
        with self.lock:
            if self.scheduler is None:
                logger.error("Cannot pause job: APScheduler not available")
                return False

            try:
                self.scheduler.pause_job(job_id)
                logger.info(f"Paused job with ID {job_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to pause job {job_id}: {str(e)}")
                return False

    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.

        Args:
            job_id: ID of the job to resume

        Returns:
            bool: True if resume was successful
        """
        with self.lock:
            if self.scheduler is None:
                logger.error("Cannot resume job: APScheduler not available")
                return False

            try:
                self.scheduler.resume_job(job_id)
                logger.info(f"Resumed job with ID {job_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to resume job {job_id}: {str(e)}")
                return False


# Global scheduler service instance
_scheduler = None


def get_scheduler(orchestrator=None) -> SchedulerService:
    """
    Get the global scheduler service instance.

    Args:
        orchestrator: The orchestrator instance to use

    Returns:
        SchedulerService: The scheduler service
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService(orchestrator)
    elif orchestrator is not None and _scheduler.orchestrator is None:
        _scheduler.orchestrator = orchestrator

    return _scheduler


def init_scheduler(orchestrator=None) -> SchedulerService:
    """
    Initialize and start the scheduler service.

    Args:
        orchestrator: The orchestrator instance to use

    Returns:
        SchedulerService: The initialized scheduler service
    """
    scheduler = get_scheduler(orchestrator)
    scheduler.start()

    return scheduler
