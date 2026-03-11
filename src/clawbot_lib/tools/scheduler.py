"""Task scheduler module."""

import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..channels import slack as slack_actions
from ..database import create_scheduled_task, get_pending_tasks, update_task_status
from ..logger import get_logger
from ..models import ScheduledTask, TaskStatus

logger = get_logger("scheduler")


class TaskScheduler:
    """Background task scheduler."""

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler()
        self._running = False

    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        # Schedule periodic task checking
        self._scheduler.add_job(
            self._check_pending_tasks,
            "interval",
            minutes=1,
            id="check_pending_tasks",
        )

        self._scheduler.start()
        self._running = True
        logger.info("Task scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._scheduler.shutdown(wait=True)
        self._running = False
        logger.info("Task scheduler stopped")

    def _check_pending_tasks(self) -> None:
        """Check and execute pending tasks."""
        try:
            tasks = asyncio.run(get_pending_tasks())
            for task in tasks:
                self._execute_task_sync(task)
        except Exception as e:
            logger.error(f"Error checking pending tasks: {e}")

    def _execute_task_sync(self, task: ScheduledTask) -> None:
        """Execute a scheduled task (sync wrapper for APScheduler thread)."""
        asyncio.run(self._execute_task(task))

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task."""
        if task.id is None:
            logger.error("Task has no id, skipping")
            return
        task_id = task.id
        logger.info(f"Executing task {task_id}: {task.task_description}")

        # Mark as running
        await update_task_status(task_id, TaskStatus.RUNNING)

        try:
            # Send the message
            success, _ = await slack_actions.send_message(
                task.channel_id,
                task.task_description,
            )

            if success:
                await update_task_status(task_id, TaskStatus.COMPLETED)
                logger.info(f"Task {task_id} completed")
            else:
                await update_task_status(task_id, TaskStatus.FAILED)
                logger.error(f"Task {task_id} failed")

        except Exception as e:
            logger.error(f"Task {task_id} error: {e}")
            await update_task_status(task_id, TaskStatus.FAILED)

    async def schedule_task(
        self,
        user_id: str,
        channel_id: str,
        task_description: str,
        scheduled_time: int | None = None,
        cron_expression: str | None = None,
        thread_ts: str | None = None,
    ) -> ScheduledTask:
        """Schedule a new task.

        Args:
            user_id: User who created the task
            channel_id: Channel to send message to
            task_description: Message to send
            scheduled_time: One-time execution time (Unix timestamp)
            cron_expression: Cron expression for recurring tasks
            thread_ts: Thread to reply to

        Returns:
            Created scheduled task
        """
        task = await create_scheduled_task(
            user_id=user_id,
            channel_id=channel_id,
            task_description=task_description,
            scheduled_time=scheduled_time,
            cron_expression=cron_expression,
            thread_ts=thread_ts,
        )

        # Add to scheduler if cron expression
        if cron_expression:
            try:
                parts = cron_expression.split()
                if len(parts) == 5:
                    self._scheduler.add_job(
                        self._execute_task_by_id,
                        CronTrigger(
                            minute=parts[0],
                            hour=parts[1],
                            day=parts[2],
                            month=parts[3],
                            day_of_week=parts[4],
                        ),
                        args=[task.id],
                        id=f"task_{task.id}",
                    )
                    logger.info(f"Scheduled recurring task {task.id} with cron: {cron_expression}")
            except Exception as e:
                logger.error(f"Failed to schedule recurring task: {e}")

        return task

    def _execute_task_by_id(self, task_id: int) -> None:
        """Execute a task by ID."""
        tasks = asyncio.run(get_pending_tasks())
        for task in tasks:
            if task.id == task_id:
                asyncio.run(self._execute_task(task))
                break


# Global scheduler
_task_scheduler: TaskScheduler | None = None


def get_task_scheduler() -> TaskScheduler:
    """Get the global task scheduler."""
    global _task_scheduler
    if _task_scheduler is None:
        _task_scheduler = TaskScheduler()
    return _task_scheduler


def start() -> None:
    """Start the task scheduler."""
    get_task_scheduler().start()


def stop() -> None:
    """Stop the task scheduler."""
    if _task_scheduler:
        _task_scheduler.stop()


async def schedule_task(
    user_id: str,
    channel_id: str,
    task_description: str,
    scheduled_time: int | None = None,
    cron_expression: str | None = None,
    thread_ts: str | None = None,
) -> ScheduledTask:
    """Schedule a new task."""
    return await get_task_scheduler().schedule_task(
        user_id, channel_id, task_description, scheduled_time, cron_expression, thread_ts
    )


# Aliases for backward compatibility
taskScheduler = type(
    "TaskScheduler",
    (),
    {
        "start": staticmethod(start),
        "stop": staticmethod(stop),
        "scheduleTask": staticmethod(schedule_task),
    },
)()
