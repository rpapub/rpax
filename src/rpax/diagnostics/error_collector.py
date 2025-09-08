"""Lake-level error collection for rpax runs.

Collects errors during a single rpax CLI run and flushes them to lake-level
filesystem artifacts for analysability and debugging support.
"""

import json
import logging
import traceback
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"  # System failures, crashes
    ERROR = "error"       # Operation failures, exceptions
    WARNING = "warning"   # Recoverable issues, degraded performance
    INFO = "info"         # Notable events, configuration issues


@dataclass
class ErrorContext:
    """Context information for an error occurrence."""
    operation: str                    # Operation that failed (e.g., "parse_project")
    component: str                   # Component that failed (e.g., "XamlAnalyzer") 
    project_slug: Optional[str] = None      # Project being processed
    project_root: Optional[str] = None      # Project root path
    workflow_path: Optional[str] = None     # Workflow file path
    additional_context: Optional[Dict[str, Any]] = None


@dataclass
class RpaxError:
    """Represents a single error occurrence during rpax execution."""
    error_id: str                    # Unique error identifier
    run_id: str                      # Run identifier
    timestamp: str                   # ISO timestamp
    severity: ErrorSeverity          # Error severity level
    error_type: str                  # Exception class name
    message: str                     # Error message
    context: Dict[str, Any]          # Error context
    traceback_lines: List[str]       # Stack trace lines
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "error_id": self.error_id,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "error_type": self.error_type,
            "message": self.message,
            "context": self.context,
            "traceback_lines": self.traceback_lines
        }


@dataclass  
class ErrorSummary:
    """Summary of errors for a complete rpax run."""
    run_id: str                      # Run identifier
    command: str                     # CLI command executed
    started_at: str                  # ISO timestamp
    completed_at: str                # ISO timestamp
    duration_seconds: float          # Run duration
    total_errors: int                # Total error count
    errors_by_severity: Dict[str, int]  # Count by severity
    errors: List[RpaxError]          # All errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "schema_version": "1.0.0",
            "run_id": self.run_id,
            "command": self.command,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "total_errors": self.total_errors,
            "errors_by_severity": self.errors_by_severity,
            "errors": [error.to_dict() for error in self.errors]
        }


class ErrorCollector:
    """Collects errors during a single rpax run for lake-level diagnostics."""
    
    def __init__(self, lake_root: Path, command: str):
        """Initialize error collector.
        
        Args:
            lake_root: Lake root directory
            command: CLI command being executed
        """
        self.lake_root = lake_root
        self.command = command
        self.run_id = self._generate_run_id()
        self.start_time = datetime.now(UTC)
        self.errors: List[RpaxError] = []
        
        logger.debug(f"Initialized error collector for run {self.run_id}")
    
    def collect_error(
        self,
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ) -> str:
        """Collect error with context for later flush.
        
        Args:
            error: Exception that occurred
            context: Error context information
            severity: Error severity level
            
        Returns:
            Error ID for reference
        """
        error_id = str(uuid.uuid4())[:8]  # Short error ID
        
        rpax_error = RpaxError(
            error_id=error_id,
            run_id=self.run_id,
            timestamp=datetime.now(UTC).isoformat(),
            severity=severity,
            error_type=type(error).__name__,
            message=str(error),
            context=asdict(context),
            traceback_lines=traceback.format_exc().split('\n')
        )
        
        self.errors.append(rpax_error)
        
        logger.debug(f"Collected error {error_id}: {error_type} - {message}", 
                    extra={"error_id": error_id, "error_type": type(error).__name__, "message": str(error)})
        
        return error_id
    
    def collect_warning(
        self,
        message: str,
        context: ErrorContext
    ) -> str:
        """Collect warning message.
        
        Args:
            message: Warning message
            context: Error context
            
        Returns:
            Error ID for reference
        """
        # Create a RuntimeWarning for consistency
        warning = RuntimeWarning(message)
        return self.collect_error(warning, context, ErrorSeverity.WARNING)
    
    def collect_info(
        self,
        message: str,
        context: ErrorContext  
    ) -> str:
        """Collect informational message.
        
        Args:
            message: Info message
            context: Error context
            
        Returns:
            Error ID for reference
        """
        # Create a generic exception for consistency
        info = RuntimeError(message)
        return self.collect_error(info, context, ErrorSeverity.INFO)
    
    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        return len(self.errors) > 0
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors have been collected."""
        return any(error.severity == ErrorSeverity.CRITICAL for error in self.errors)
    
    def get_error_counts(self) -> Dict[str, int]:
        """Get error counts by severity."""
        counts = {severity.value: 0 for severity in ErrorSeverity}
        
        for error in self.errors:
            counts[error.severity.value] += 1
        
        return counts
    
    def flush_to_filesystem(self) -> Optional[Path]:
        """Flush collected errors to lake-level errors directory.
        
        Returns:
            Path to error summary file, or None if no errors
        """
        if not self.errors:
            logger.debug(f"No errors to flush for run {self.run_id}")
            return None
        
        # Create errors directory
        errors_dir = self.lake_root / "_errors"
        errors_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate run duration
        end_time = datetime.now(UTC)
        duration = (end_time - self.start_time).total_seconds()
        
        # Create error summary
        error_summary = ErrorSummary(
            run_id=self.run_id,
            command=self.command,
            started_at=self.start_time.isoformat(),
            completed_at=end_time.isoformat(),
            duration_seconds=duration,
            total_errors=len(self.errors),
            errors_by_severity=self.get_error_counts(),
            errors=self.errors
        )
        
        # Write error summary file
        error_file = errors_dir / f"{self.run_id}.json"
        with open(error_file, "w", encoding="utf-8") as f:
            json.dump(error_summary.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Update errors index
        self._update_errors_index(errors_dir, error_summary)
        
        logger.info(f"Flushed {len(self.errors)} errors to: {error_file}")
        return error_file
    
    def _update_errors_index(self, errors_dir: Path, error_summary: ErrorSummary):
        """Update errors index with current run summary."""
        index_file = errors_dir / "index.json"
        
        # Load existing index or create new
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to read errors index, creating new one: {e}")
                index_data = self._create_empty_index()
        else:
            index_data = self._create_empty_index()
        
        # Add current run to index
        run_entry = {
            "run_id": error_summary.run_id,
            "command": error_summary.command,
            "started_at": error_summary.started_at,
            "duration_seconds": error_summary.duration_seconds,
            "total_errors": error_summary.total_errors,
            "errors_by_severity": error_summary.errors_by_severity,
            "error_file": f"{error_summary.run_id}.json"
        }
        
        # Remove existing entry for this run_id (shouldn't happen, but be safe)
        index_data["runs"] = [run for run in index_data["runs"] if run["run_id"] != error_summary.run_id]
        
        # Add new entry and sort by timestamp (most recent first)
        index_data["runs"].append(run_entry)
        index_data["runs"].sort(key=lambda r: r["started_at"], reverse=True)
        
        # Update index metadata
        index_data["total_runs"] = len(index_data["runs"])
        index_data["last_updated"] = datetime.now(UTC).isoformat()
        
        # Keep only last 100 runs to prevent unbounded growth
        if len(index_data["runs"]) > 100:
            # Remove old error files
            for old_run in index_data["runs"][100:]:
                old_error_file = errors_dir / old_run["error_file"]
                if old_error_file.exists():
                    old_error_file.unlink()
            
            # Truncate index
            index_data["runs"] = index_data["runs"][:100]
            index_data["total_runs"] = 100
        
        # Write updated index
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    def _create_empty_index(self) -> Dict[str, Any]:
        """Create empty errors index structure."""
        return {
            "schema_version": "1.0.0",
            "created_at": datetime.now(UTC).isoformat(),
            "last_updated": datetime.now(UTC).isoformat(),
            "total_runs": 0,
            "description": "Lake-level error collection index for rpax runs",
            "runs": []
        }
    
    def _generate_run_id(self) -> str:
        """Generate unique run identifier."""
        # Format: run-YYYYMMDD-HHMMSS-{short_uuid}
        timestamp_part = self.start_time.strftime("run-%Y%m%d-%H%M%S")
        uuid_part = str(uuid.uuid4())[:8]
        return f"{timestamp_part}-{uuid_part}"


def create_error_collector(lake_root: Path, command: str) -> ErrorCollector:
    """Create error collector for rpax run.
    
    Args:
        lake_root: Lake root directory
        command: CLI command being executed
        
    Returns:
        ErrorCollector instance
    """
    return ErrorCollector(lake_root, command)