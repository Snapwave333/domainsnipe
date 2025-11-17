"""Domain analyzer for scoring SEO value and brandability."""

import asyncio
import json
import re
from abc import ABC, abstractmethod

import aiohttp
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_config
from .models import (
    BacklinkQuality,
    BrandabilityScore,
    DomainAnalysis,
    DomainInfo,
    SEOMetrics,
)


class SEOAnalyzer(ABC):
    """Abstract base class for SEO analysis."""

    @abstractmethod
    async def analyze(self, domain: str) -> SEOMetrics:
        """Analyze SEO metrics for a domain."""
        pass


class MozAPIAnalyzer(SEOAnalyzer):
    """SEO analyzer using Moz API."""

    BASE_URL = "https://lsapi.seomoz.com/v2"

    async def analyze(self, domain: str) -> SEOMetrics:
        """Fetch SEO metrics from Moz API."""
        config = get_config()

        if not config.api.moz_access_id or not config.api.moz_secret_key:
            # Return empty metrics if not configured
            return SEOMetrics()

        try:
            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(
                    config.api.moz_access_id,
                    config.api.moz_secret_key
                )

                payload = {
                    "targets": [domain],
                    "metrics": ["domain_authority", "spam_score", "linking_domains"]
                }

                async with session.post(
                    f"{self.BASE_URL}/url_metrics",
                    json=payload,
                    auth=auth
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "results" in data and data["results"]:
                            result = data["results"][0]
                            return SEOMetrics(
                                domain_authority=int(result.get("domain_authority", 0)),
                                referring_domains=int(result.get("linking_domains", 0)),
                                backlink_count=int(result.get("linking_domains", 0) * 10),  # Estimate
                            )
        except Exception as e:
            print(f"Moz API error for {domain}: {e}")

        return SEOMetrics()


class SimulatedSEOAnalyzer(SEOAnalyzer):
    """
    Simulated SEO analyzer for demonstration.

    In production, this would integrate with real APIs like:
    - Moz API
    - Ahrefs API
    - SEMrush API
    - Majestic API
    """

    async def analyze(self, domain: str) -> SEOMetrics:
        """Generate simulated SEO metrics based on domain characteristics."""
        await asyncio.sleep(0.1)  # Simulate API delay

        # Heuristics for simulation
        base_name = domain.rsplit(".", 1)[0] if "." in domain else domain
        tld = domain.rsplit(".", 1)[1] if "." in domain else "com"

        # Base scores
        base_da = 20
        base_dr = 25

        # Boost for short, memorable names
        if len(base_name) <= 6:
            base_da += 15
            base_dr += 10

        # Boost for single words (no hyphens)
        if "-" not in base_name:
            base_da += 10
            base_dr += 10

        # Boost for premium TLDs
        tld_boost = {"com": 15, "net": 8, "org": 7, "io": 12, "ai": 18}
        base_da += tld_boost.get(tld, 0)
        base_dr += tld_boost.get(tld, 0)

        # Add some randomness
        import random
        variance = random.randint(-10, 20)
        da = min(100, max(0, base_da + variance))
        dr = min(100, max(0, base_dr + variance + random.randint(-5, 5)))

        # Estimate backlinks based on DA
        ref_domains = int(da * da * 0.5)  # Quadratic relationship
        backlinks = ref_domains * random.randint(3, 15)

        # Determine backlink quality
        if da >= 50:
            quality = BacklinkQuality.EXCELLENT
        elif da >= 35:
            quality = BacklinkQuality.HIGH
        elif da >= 20:
            quality = BacklinkQuality.MEDIUM
        elif da >= 10:
            quality = BacklinkQuality.LOW
        else:
            quality = BacklinkQuality.SPAM

        # Estimate organic traffic
        organic_traffic = int(da * da * random.uniform(0.5, 2.0))

        return SEOMetrics(
            domain_authority=da,
            domain_rating=dr,
            backlink_count=backlinks,
            referring_domains=ref_domains,
            backlink_quality=quality,
            organic_traffic=organic_traffic,
        )


class BrandabilityAnalyzer:
    """Analyzes domain brandability using LLM."""

    def __init__(self):
        self.client: Anthropic | None = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Anthropic client if API key is available."""
        config = get_config()
        if config.api.anthropic_api_key:
            self.client = Anthropic(api_key=config.api.anthropic_api_key)

    def _analyze_basic(self, domain: str) -> BrandabilityScore:
        """Basic brandability analysis without LLM."""
        base_name = domain.rsplit(".", 1)[0] if "." in domain else domain

        # Length score (shorter is better)
        length = len(base_name)
        if length <= 5:
            length_score = 10.0
        elif length <= 8:
            length_score = 8.0
        elif length <= 12:
            length_score = 6.0
        elif length <= 15:
            length_score = 4.0
        else:
            length_score = 2.0

        # Memorability (based on patterns)
        memorability = 5.0

        # Single word bonus
        if "-" not in base_name and base_name.isalpha():
            memorability += 2.0

        # Common word patterns
        common_suffixes = ["ly", "ify", "hub", "lab", "box", "io", "fy"]
        if any(base_name.endswith(suffix) for suffix in common_suffixes):
            memorability += 1.0

        # Pronounceability
        pronounceability = 5.0

        # Check for vowel-consonant patterns
        vowels = sum(1 for c in base_name.lower() if c in "aeiou")
        consonants = sum(1 for c in base_name.lower() if c.isalpha() and c not in "aeiou")

        if vowels > 0 and consonants > 0:
            ratio = vowels / (vowels + consonants)
            if 0.3 <= ratio <= 0.5:  # Good balance
                pronounceability += 2.0

        # Penalize double consonants clusters
        if re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", base_name.lower()):
            pronounceability -= 2.0

        # Overall score
        score = (length_score + memorability + pronounceability) / 3

        return BrandabilityScore(
            score=min(10, score),
            length_score=length_score,
            memorability=min(10, memorability),
            pronounceability=min(10, pronounceability),
            industry_fit=[],
            reasoning="Basic heuristic analysis"
        )

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def analyze_with_llm(self, domain: str) -> BrandabilityScore:
        """Analyze brandability using Claude LLM."""
        if not self.client:
            return self._analyze_basic(domain)

        config = get_config()

        prompt = f"""Analyze the brandability of the domain name: {domain}

Please provide a JSON response with the following structure:
{{
    "score": <number 0-10>,
    "length_score": <number 0-10>,
    "memorability": <number 0-10>,
    "pronounceability": <number 0-10>,
    "industry_fit": [<list of industries this domain would be perfect for>],
    "reasoning": "<brief explanation of the scores>"
}}

Consider:
1. How short and memorable is it?
2. Is it easy to spell and pronounce?
3. Does it have brandable qualities (evocative, professional, modern)?
4. What industries or businesses would find this domain valuable?
5. Would you pay $1000+ for this domain?

Be strict in your scoring - only give 9-10 for exceptional domains like apple.com or amazon.com level quality.
Response with ONLY the JSON, no other text."""

        try:
            # Run synchronous API call in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    model=config.analyzer.llm_model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
            )

            # Parse response
            content = response.content[0].text.strip()

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content)

            return BrandabilityScore(
                score=float(data.get("score", 5)),
                length_score=float(data.get("length_score", 5)),
                memorability=float(data.get("memorability", 5)),
                pronounceability=float(data.get("pronounceability", 5)),
                industry_fit=data.get("industry_fit", []),
                reasoning=data.get("reasoning", "LLM analysis")
            )

        except Exception as e:
            print(f"LLM analysis failed for {domain}: {e}")
            return self._analyze_basic(domain)

    async def analyze(self, domain: str) -> BrandabilityScore:
        """Analyze domain brandability."""
        config = get_config()

        if config.analyzer.use_llm_analysis and self.client:
            return await self.analyze_with_llm(domain)
        else:
            return self._analyze_basic(domain)


class DomainAnalyzer:
    """Main analyzer that combines SEO and brandability analysis."""

    def __init__(self):
        self.seo_analyzer: SEOAnalyzer = self._get_seo_analyzer()
        self.brandability_analyzer = BrandabilityAnalyzer()

    def _get_seo_analyzer(self) -> SEOAnalyzer:
        """Get the appropriate SEO analyzer based on config."""
        config = get_config()

        # Use real API if configured, otherwise use simulation
        if config.api.moz_access_id and config.api.moz_secret_key:
            return MozAPIAnalyzer()

        # Default to simulated for demonstration
        return SimulatedSEOAnalyzer()

    async def analyze_domain(self, domain_info: DomainInfo) -> DomainAnalysis:
        """Perform complete analysis of a domain."""
        # Run SEO and brandability analysis concurrently
        seo_task = self.seo_analyzer.analyze(domain_info.name)
        brandability_task = self.brandability_analyzer.analyze(domain_info.name)

        seo_metrics, brandability_score = await asyncio.gather(
            seo_task,
            brandability_task
        )

        # Create analysis object
        analysis = DomainAnalysis(
            domain=domain_info,
            seo=seo_metrics,
            brandability=brandability_score,
        )

        # Calculate total score and determine if it's a gem
        analysis.calculate_total_score()

        return analysis

    async def analyze_batch(self, domains: list[DomainInfo]) -> list[DomainAnalysis]:
        """Analyze multiple domains concurrently."""
        config = get_config()
        results = []

        # Process in smaller batches to avoid rate limits
        batch_size = 10

        for i in range(0, len(domains), batch_size):
            batch = domains[i:i + batch_size]
            tasks = [self.analyze_domain(domain) for domain in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, DomainAnalysis):
                    results.append(result)
                else:
                    print(f"Analysis error: {result}")

            # Rate limiting between batches
            if i + batch_size < len(domains):
                await asyncio.sleep(1)

        return results

    def filter_gems(self, analyses: list[DomainAnalysis]) -> list[DomainAnalysis]:
        """Filter analyses to only include high-value 'gem' domains."""
        config = get_config()

        gems = [
            analysis for analysis in analyses
            if (
                analysis.is_gem or
                analysis.total_score >= config.analyzer.gem_threshold
            )
        ]

        # Sort by total score (highest first)
        gems.sort(key=lambda x: x.total_score, reverse=True)

        return gems

    def rank_domains(self, analyses: list[DomainAnalysis]) -> list[DomainAnalysis]:
        """Rank all analyzed domains by potential value."""
        # Sort by ROI potential (estimated value / registration cost)
        analyses.sort(
            key=lambda x: (x.estimated_value / x.registration_cost, x.total_score),
            reverse=True
        )
        return analyses


async def analyze_domains(domains: list[DomainInfo]) -> list[DomainAnalysis]:
    """Convenience function to analyze a list of domains."""
    analyzer = DomainAnalyzer()
    return await analyzer.analyze_batch(domains)


async def find_gem_domains(domains: list[DomainInfo]) -> list[DomainAnalysis]:
    """Find high-value 'gem' domains from a list."""
    analyzer = DomainAnalyzer()
    analyses = await analyzer.analyze_batch(domains)
    return analyzer.filter_gems(analyses)
