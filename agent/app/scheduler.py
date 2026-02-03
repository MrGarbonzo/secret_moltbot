# Heartbeat Scheduler
"""
Background scheduler for autonomous agent operation.
"""

import asyncio
import structlog
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable

from .config import settings


log = structlog.get_logger()


class HeartbeatScheduler:
    """
    Scheduler for periodic heartbeat execution.
    
    Runs the agent's heartbeat method at configured intervals.
    
    Usage:
        agent = MoltbookAgent()
        scheduler = HeartbeatScheduler(agent.heartbeat)
        
        # Start in background
        await scheduler.start()
        
        # Or run as task
        task = asyncio.create_task(scheduler.run())
        
        # Stop
        scheduler.stop()
    """
    
    def __init__(
        self,
        heartbeat_fn: Callable[[], Awaitable],
        interval_hours: Optional[float] = None,
    ):
        self.heartbeat_fn = heartbeat_fn
        self.interval_hours = interval_hours or settings.heartbeat_interval_hours
        self.interval = timedelta(hours=self.interval_hours)
        
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
        self._next_run: Optional[datetime] = None
    
    async def run(self):
        """Run the scheduler loop."""
        self.running = True
        log.info(
            "Scheduler started", 
            interval_hours=self.interval_hours
        )
        
        while self.running:
            self._next_run = datetime.utcnow() + self.interval
            
            try:
                log.info("Executing scheduled heartbeat")
                await self.heartbeat_fn()
                self._last_run = datetime.utcnow()
                
            except Exception as e:
                log.error("Scheduled heartbeat failed", error=str(e))
            
            if self.running:
                log.info(f"Next heartbeat in {self.interval_hours} hours")
                await asyncio.sleep(self.interval.total_seconds())
        
        log.info("Scheduler stopped")
    
    async def start(self):
        """Start scheduler as background task."""
        if self._task is not None:
            log.warning("Scheduler already running")
            return
        
        self._task = asyncio.create_task(self.run())
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()
            self._task = None
    
    def set_interval(self, hours: float):
        """Update the interval."""
        self.interval_hours = hours
        self.interval = timedelta(hours=hours)
        log.info(f"Interval updated to {hours} hours")
    
    def next_run_time(self) -> Optional[str]:
        """Get the next scheduled run time."""
        if self._next_run is None:
            return None
        return self._next_run.isoformat()
    
    def last_run_time(self) -> Optional[str]:
        """Get the last run time."""
        if self._last_run is None:
            return None
        return self._last_run.isoformat()
    
    def time_until_next(self) -> Optional[timedelta]:
        """Get time until next heartbeat."""
        if self._next_run is None:
            return None
        return self._next_run - datetime.utcnow()
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.running and self._task is not None
