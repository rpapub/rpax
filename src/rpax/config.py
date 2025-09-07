"""Configuration management for rpax using Pydantic models."""

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectType(str, Enum):
    """UiPath project types."""
    PROCESS = "process"
    LIBRARY = "library"


class OutputFormat(str, Enum):
    """Output format types."""
    JSON = "json"
    MERMAID = "mermaid"
    MARKDOWN = "markdown"
    HTML = "html"


class ReportFormat(str, Enum):
    """Report format types."""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


class LogLevel(str, Enum):
    """Logging levels."""
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


class ProjectConfig(BaseModel):
    """Project configuration section."""
    name: str | None = None
    root: str = "."
    type: ProjectType

    model_config = ConfigDict(use_enum_values=True)


class ScanConfig(BaseModel):
    """Scanning configuration section."""
    exclude: list[str] = Field(default_factory=lambda: [
        ".local/**",
        ".settings/**",
        ".screenshots/**",
        "TestResults/**"
    ])
    follow_dynamic: bool = Field(alias="followDynamic", default=False)
    max_depth: int = Field(alias="maxDepth", default=10)

    @field_validator("max_depth")
    @classmethod
    def validate_max_depth(cls, v):
        if v < 1:
            raise ValueError("max_depth must be >= 1")
        return v

    model_config = ConfigDict(populate_by_name=True)


class OutputConfig(BaseModel):
    """Output configuration section."""
    dir: str = ".rpax-lake"
    formats: list[OutputFormat] = Field(default_factory=lambda: [
        OutputFormat.JSON, OutputFormat.MERMAID
    ])
    summaries: bool = True
    generate_activities: bool = Field(alias="generateActivities", default=True)

    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)


class ValidationConfig(BaseModel):
    """Validation configuration section."""
    fail_on_missing: bool = Field(alias="failOnMissing", default=True)
    fail_on_cycles: bool = Field(alias="failOnCycles", default=False)
    warn_on_dynamic: bool = Field(alias="warnOnDynamic", default=True)

    model_config = ConfigDict(populate_by_name=True)


class DiffConfig(BaseModel):
    """Diff configuration section."""
    baseline_dir: str = Field(alias="baselineDir", default=".rpax-cache")
    report_format: ReportFormat = Field(alias="reportFormat", default=ReportFormat.JSON)

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)


class ParserConfig(BaseModel):
    """Parser configuration section."""
    use_enhanced: bool = Field(alias="useEnhanced", default=True)
    visual_detection: bool = Field(alias="visualDetection", default=True)
    include_structural: bool = Field(alias="includeStructural", default=False)
    max_depth: int = Field(alias="maxDepth", default=50)
    custom_blacklist: list[str] = Field(alias="customBlacklist", default_factory=list)
    custom_whitelist: list[str] = Field(alias="customWhitelist", default_factory=list)

    @field_validator("max_depth")
    @classmethod
    def validate_parser_max_depth(cls, v):
        if v < 1:
            raise ValueError("parser max_depth must be >= 1")
        return v

    model_config = ConfigDict(populate_by_name=True)


class McpConfig(BaseModel):
    """MCP configuration section."""
    enabled: bool = True
    uri_prefix: str = Field(alias="uriPrefix", default="uipath://proj")
    private: list[str] = Field(default_factory=lambda: ["runtime://**"])

    model_config = ConfigDict(populate_by_name=True)


class ApiConfig(BaseModel):
    """API configuration section per ADR-022."""
    enabled: bool = False  # Default false in dev, true when packaged
    bind: str = "127.0.0.1"  # Never public by default - localhost only
    port: int = 8623  # RPAX port (R-P-A-X numeric); auto-increment on clash
    read_only: bool = Field(alias="readOnly", default=True)  # Always true - no mutations allowed

    @field_validator("bind")
    @classmethod
    def validate_bind_address(cls, v):
        """Validate bind address - only localhost addresses allowed."""
        allowed_localhost = ["127.0.0.1", "localhost", "::1"]
        if v not in allowed_localhost:
            raise ValueError(f"bind address must be localhost only, got: {v}")
        return v

    @field_validator("port")
    @classmethod
    def validate_port_range(cls, v):
        """Validate port is in valid range."""
        if not (1024 <= v <= 65535):
            raise ValueError(f"port must be between 1024-65535, got: {v}")
        return v

    model_config = ConfigDict(populate_by_name=True)


class PseudocodeConfig(BaseModel):
    """Pseudocode generation configuration section per ADR-023."""
    generate_expanded: bool = Field(alias="generateExpanded", default=True)
    max_expansion_depth: int = Field(alias="maxExpansionDepth", default=3)
    cycle_handling: str = Field(alias="cycleHandling", default="detect_and_mark")

    @field_validator("max_expansion_depth")
    @classmethod
    def validate_max_expansion_depth(cls, v):
        """Validate expansion depth is reasonable."""
        if v < 0:
            raise ValueError("max_expansion_depth must be >= 0")
        if v > 10:
            raise ValueError("max_expansion_depth must be <= 10 to prevent excessive recursion")
        return v

    @field_validator("cycle_handling")
    @classmethod
    def validate_cycle_handling(cls, v):
        """Validate cycle handling strategy."""
        valid_strategies = ["detect_and_mark", "detect_and_stop", "ignore"]
        if v not in valid_strategies:
            raise ValueError(f"cycle_handling must be one of {valid_strategies}, got: {v}")
        return v

    model_config = ConfigDict(populate_by_name=True)


class LoggingConfig(BaseModel):
    """Logging configuration section."""
    level: LogLevel = LogLevel.INFO

    model_config = ConfigDict(use_enum_values=True)


class RpaxConfig(BaseModel):
    """Complete rpax configuration model."""
    project: ProjectConfig
    scan: ScanConfig = Field(default_factory=ScanConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    diff: DiffConfig = Field(default_factory=DiffConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    pseudocode: PseudocodeConfig = Field(default_factory=PseudocodeConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    mcp: McpConfig = Field(default_factory=McpConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = ConfigDict(extra="forbid")  # Corresponds to additionalProperties: false


def load_config(config_path: str | Path | None = None) -> RpaxConfig:
    """Load configuration from file with fallback to defaults.
    
    Args:
        config_path: Optional path to configuration file. If None, searches
                    current directory and parents for .rpax.json
                    
    Returns:
        RpaxConfig: Loaded and validated configuration
        
    Raises:
        FileNotFoundError: If config file specified but not found
        ValueError: If configuration is invalid
    """
    if config_path is None:
        # Search for .rpax.json in current directory and parents
        config_path = find_config_file()
    else:
        config_path = Path(config_path)

    if config_path and config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                config_data = json.load(f)
            return RpaxConfig(**config_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file {config_path}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {e}")
    else:
        # Return zero-config defaults - need to infer project type
        return create_default_config()


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Find .rpax.json configuration file by searching up directory tree.
    
    Args:
        start_dir: Directory to start search from (default: current directory)
        
    Returns:
        Path to config file if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()

    current = Path(start_dir).resolve()

    while True:
        config_file = current / ".rpax.json"
        if config_file.exists():
            return config_file

        parent = current.parent
        if parent == current:  # Reached root directory
            break
        current = parent

    return None


def create_default_config() -> RpaxConfig:
    """Create default configuration with sensible defaults.
    
    Note: For zero-config operation, we default to 'process' type.
    This can be overridden by project.json detection in parser layer.
    """
    return RpaxConfig(
        project=ProjectConfig(type=ProjectType.PROCESS)
    )
