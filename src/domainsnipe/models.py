"""Data models for domain information and scoring."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class DomainStatus(str, Enum):
    PENDING_DELETE = "pending_delete"
    AVAILABLE = "available"
    REGISTERED = "registered"
    UNKNOWN = "unknown"


class BacklinkQuality(str, Enum):
    SPAM = "spam"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXCELLENT = "excellent"


class DomainInfo(BaseModel):
    """Basic domain information from expiring lists."""

    name: str = Field(..., description="Domain name (e.g., example.com)")
    tld: str = Field(..., description="Top-level domain (e.g., com, net)")
    drop_date: datetime | None = Field(None, description="Expected deletion date")
    age_years: int | None = Field(None, description="Domain age in years")
    registrar: str | None = Field(None, description="Current registrar")
    status: DomainStatus = Field(default=DomainStatus.PENDING_DELETE)

    @property
    def base_name(self) -> str:
        """Get domain name without TLD."""
        return self.name.rsplit(".", 1)[0] if "." in self.name else self.name


class SEOMetrics(BaseModel):
    """SEO-related metrics for a domain."""

    domain_authority: int = Field(0, ge=0, le=100, description="Moz Domain Authority score")
    domain_rating: int = Field(0, ge=0, le=100, description="Ahrefs Domain Rating")
    backlink_count: int = Field(0, ge=0, description="Total number of backlinks")
    referring_domains: int = Field(0, ge=0, description="Number of unique referring domains")
    backlink_quality: BacklinkQuality = Field(default=BacklinkQuality.UNKNOWN)
    organic_traffic: int = Field(0, ge=0, description="Estimated monthly organic traffic")

    @property
    def seo_score(self) -> float:
        """Calculate composite SEO score (0-100)."""
        # Weight different factors
        da_weight = 0.3
        dr_weight = 0.3
        ref_domains_weight = 0.25
        quality_weight = 0.15

        quality_scores = {
            BacklinkQuality.SPAM: 0,
            BacklinkQuality.LOW: 25,
            BacklinkQuality.MEDIUM: 50,
            BacklinkQuality.HIGH: 75,
            BacklinkQuality.EXCELLENT: 100,
        }

        # Normalize referring domains (cap at 1000 for scoring)
        ref_score = min(self.referring_domains / 10, 100)

        return (
            self.domain_authority * da_weight +
            self.domain_rating * dr_weight +
            ref_score * ref_domains_weight +
            quality_scores.get(self.backlink_quality, 50) * quality_weight
        )


class BrandabilityScore(BaseModel):
    """Brandability assessment from LLM analysis."""

    score: float = Field(0, ge=0, le=10, description="Brandability score 0-10")
    length_score: float = Field(0, ge=0, le=10, description="Score based on domain length")
    memorability: float = Field(0, ge=0, le=10, description="How memorable the domain is")
    pronounceability: float = Field(0, ge=0, le=10, description="How easy to pronounce")
    industry_fit: list[str] = Field(default_factory=list, description="Industries this domain fits")
    reasoning: str = Field("", description="LLM reasoning for the score")

    @property
    def composite_score(self) -> float:
        """Get weighted composite brandability score."""
        return (
            self.score * 0.4 +
            self.memorability * 0.3 +
            self.pronounceability * 0.2 +
            self.length_score * 0.1
        )


class DomainAnalysis(BaseModel):
    """Complete analysis of a domain."""

    domain: DomainInfo
    seo: SEOMetrics = Field(default_factory=SEOMetrics)
    brandability: BrandabilityScore = Field(default_factory=BrandabilityScore)
    estimated_value: float = Field(0, ge=0, description="Estimated value in USD")
    total_score: float = Field(0, ge=0, le=100, description="Overall domain score")
    is_gem: bool = Field(False, description="Whether this is a high-value 'gem'")
    registration_cost: float = Field(10.0, description="Cost to register in USD")

    def calculate_total_score(self) -> float:
        """Calculate overall domain score."""
        # Weights for different factors
        seo_weight = 0.4
        brandability_weight = 0.3
        age_weight = 0.2
        tld_weight = 0.1

        # TLD scoring
        tld_scores = {
            "com": 100,
            "net": 70,
            "org": 65,
            "io": 60,
            "co": 55,
            "ai": 80,
            "app": 50,
        }
        tld_score = tld_scores.get(self.domain.tld, 30)

        # Age scoring (cap at 20 years)
        age_score = min((self.domain.age_years or 0) * 5, 100)

        self.total_score = (
            self.seo.seo_score * seo_weight +
            self.brandability.composite_score * 10 * brandability_weight +
            age_score * age_weight +
            tld_score * tld_weight
        )

        # Determine if it's a gem
        self.is_gem = (
            self.total_score >= 60 or
            (self.seo.domain_authority >= 40 and self.brandability.score >= 7) or
            (self.domain.age_years and self.domain.age_years >= 10 and self.seo.domain_authority >= 30)
        )

        # Estimate value based on score
        if self.total_score >= 80:
            self.estimated_value = 5000 + (self.total_score - 80) * 250
        elif self.total_score >= 60:
            self.estimated_value = 1000 + (self.total_score - 60) * 200
        elif self.total_score >= 40:
            self.estimated_value = 200 + (self.total_score - 40) * 40
        else:
            self.estimated_value = max(10, self.total_score * 5)

        return self.total_score


class RegistrationResult(BaseModel):
    """Result of attempting to register a domain."""

    domain: str
    success: bool
    registrar: str
    cost: float = 0
    confirmation_id: str | None = None
    error_message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
