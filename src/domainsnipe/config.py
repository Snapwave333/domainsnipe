"""Configuration management for DomainSnipe."""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class APIConfig(BaseModel):
    """API configuration for external services."""

    # SEO APIs
    moz_access_id: str = Field(default="", description="Moz API Access ID")
    moz_secret_key: str = Field(default="", description="Moz API Secret Key")
    ahrefs_api_key: str = Field(default="", description="Ahrefs API Key")

    # LLM for brandability
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")

    # Registrar APIs
    godaddy_api_key: str = Field(default="", description="GoDaddy API Key")
    godaddy_api_secret: str = Field(default="", description="GoDaddy API Secret")
    namecheap_api_user: str = Field(default="", description="Namecheap API User")
    namecheap_api_key: str = Field(default="", description="Namecheap API Key")
    namecheap_username: str = Field(default="", description="Namecheap Username")


class ScannerConfig(BaseModel):
    """Configuration for domain scanning."""

    # Data sources
    sources: list[str] = Field(
        default=["expireddomains", "dropcatch", "namejet"],
        description="Sources to scan for expiring domains"
    )

    # Filtering
    min_domain_age: int = Field(1, description="Minimum domain age in years")
    tlds: list[str] = Field(
        default=["com", "net", "org", "io", "co", "ai"],
        description="TLDs to consider"
    )
    max_length: int = Field(20, description="Maximum domain name length")
    min_length: int = Field(3, description="Minimum domain name length")

    # Performance
    batch_size: int = Field(100, description="Batch size for processing")
    scan_interval_hours: int = Field(6, description="How often to scan (hours)")


class AnalyzerConfig(BaseModel):
    """Configuration for domain analysis."""

    # Thresholds
    min_da_score: int = Field(10, description="Minimum Domain Authority to consider")
    min_brandability: float = Field(5.0, description="Minimum brandability score")
    gem_threshold: float = Field(60.0, description="Score threshold for 'gem' domains")

    # Analysis settings
    check_spam: bool = Field(True, description="Check for spam backlinks")
    use_llm_analysis: bool = Field(True, description="Use LLM for brandability")
    llm_model: str = Field("claude-sonnet-4-20250514", description="LLM model to use")


class SniperConfig(BaseModel):
    """Configuration for domain registration."""

    # Strategy
    max_registration_cost: float = Field(15.0, description="Max cost per domain in USD")
    min_profit_margin: float = Field(10.0, description="Minimum expected profit multiplier")
    auto_register: bool = Field(False, description="Automatically register gems")

    # Registrar priority
    registrar_priority: list[str] = Field(
        default=["namecheap", "godaddy"],
        description="Order of registrars to try"
    )

    # Rate limiting
    max_registrations_per_day: int = Field(10, description="Max registrations per day")
    retry_attempts: int = Field(3, description="Retry attempts per registrar")


class Config(BaseModel):
    """Main configuration for DomainSnipe."""

    api: APIConfig = Field(default_factory=APIConfig)
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    analyzer: AnalyzerConfig = Field(default_factory=AnalyzerConfig)
    sniper: SniperConfig = Field(default_factory=SniperConfig)

    # Storage
    data_dir: Path = Field(default=Path("./data"), description="Directory for data storage")
    log_level: str = Field(default="INFO", description="Logging level")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        api_config = APIConfig(
            moz_access_id=os.getenv("MOZ_ACCESS_ID", ""),
            moz_secret_key=os.getenv("MOZ_SECRET_KEY", ""),
            ahrefs_api_key=os.getenv("AHREFS_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            godaddy_api_key=os.getenv("GODADDY_API_KEY", ""),
            godaddy_api_secret=os.getenv("GODADDY_API_SECRET", ""),
            namecheap_api_user=os.getenv("NAMECHEAP_API_USER", ""),
            namecheap_api_key=os.getenv("NAMECHEAP_API_KEY", ""),
            namecheap_username=os.getenv("NAMECHEAP_USERNAME", ""),
        )

        return cls(api=api_config)

    def save_to_file(self, path: Path) -> None:
        """Save configuration to JSON file."""
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load_from_file(cls, path: Path) -> "Config":
        """Load configuration from JSON file."""
        if path.exists():
            return cls.model_validate_json(path.read_text())
        return cls.from_env()


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
