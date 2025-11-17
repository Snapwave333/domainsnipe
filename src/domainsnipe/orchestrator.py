"""Main orchestrator that coordinates scanning, analysis, and sniping."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from .analyzer import DomainAnalyzer
from .config import get_config
from .models import DomainAnalysis, RegistrationResult
from .scanner import DomainScanner
from .sniper import DomainSniper


class Orchestrator:
    """Coordinates the entire domain sniping pipeline."""

    def __init__(self):
        self.scanner = DomainScanner()
        self.analyzer = DomainAnalyzer()
        self.sniper = DomainSniper()
        self.results_history: list[dict] = []

    async def scan_and_analyze(self, max_domains: int | None = None) -> list[DomainAnalysis]:
        """
        Scan for expiring domains and analyze them.

        Returns list of analyzed domains sorted by potential value.
        """
        print("Scanning for expiring domains...")

        # Scan for domains
        domains = await self.scanner.scan_batch(batch_size=max_domains or 100)
        print(f"Found {len(domains)} domains matching criteria")

        if not domains:
            return []

        # Analyze domains
        print("Analyzing domain values...")
        analyses = await self.analyzer.analyze_batch(domains)
        print(f"Completed analysis of {len(analyses)} domains")

        # Rank by value
        ranked = self.analyzer.rank_domains(analyses)

        return ranked

    async def find_gems(self, max_scan: int | None = None) -> list[DomainAnalysis]:
        """
        Find high-value 'gem' domains from expiring lists.

        Returns only domains that meet the 'gem' criteria.
        """
        analyses = await self.scan_and_analyze(max_domains=max_scan)
        gems = self.analyzer.filter_gems(analyses)

        print(f"Found {len(gems)} gem domains out of {len(analyses)} analyzed")

        return gems

    async def auto_snipe(self, max_scan: int | None = None) -> dict:
        """
        Automatically scan, analyze, and register valuable domains.

        Returns summary of the sniping session.
        """
        config = get_config()

        if not config.sniper.auto_register:
            print("Auto-registration is disabled. Enable in config to use auto_snipe.")
            return {"error": "auto_register is disabled"}

        print("Starting auto-snipe session...")

        # Find gems
        gems = await self.find_gems(max_scan=max_scan)

        if not gems:
            return {
                "status": "no_gems_found",
                "scanned": max_scan or 100,
                "gems_found": 0,
                "registrations": []
            }

        # Attempt to snipe
        print(f"Attempting to register {len(gems)} gem domains...")
        results = await self.sniper.snipe_batch(gems, auto_only=True)

        # Generate summary
        summary = self.sniper.get_registration_summary(results)
        summary["gems_found"] = len(gems)
        summary["top_gems"] = [
            {
                "domain": g.domain.name,
                "score": round(g.total_score, 2),
                "estimated_value": round(g.estimated_value, 2),
            }
            for g in gems[:10]
        ]

        # Save results
        self._save_session_results(summary, gems, results)

        return summary

    async def manual_snipe(self, domain_name: str) -> RegistrationResult | None:
        """
        Manually attempt to register a specific domain.

        Bypasses auto-register checks but still checks availability.
        """
        from .models import DomainInfo

        # Create a minimal domain info
        parts = domain_name.rsplit(".", 1)
        if len(parts) != 2:
            print(f"Invalid domain name: {domain_name}")
            return None

        base_name, tld = parts

        domain_info = DomainInfo(
            name=domain_name,
            tld=tld,
            drop_date=None,
            age_years=None,
            registrar="manual",
        )

        # Analyze the domain
        print(f"Analyzing {domain_name}...")
        analysis = await self.analyzer.analyze_domain(domain_info)

        print(f"Domain Score: {analysis.total_score:.2f}")
        print(f"Estimated Value: ${analysis.estimated_value:.2f}")
        print(f"Is Gem: {analysis.is_gem}")

        # Attempt registration
        print(f"Attempting to register {domain_name}...")
        result = await self.sniper.snipe_domain(analysis, force=True)

        return result

    def _save_session_results(
        self,
        summary: dict,
        gems: list[DomainAnalysis],
        results: list[RegistrationResult]
    ) -> None:
        """Save session results to file for record keeping."""
        config = get_config()
        data_dir = config.data_dir
        data_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        results_file = data_dir / f"session_{timestamp}.json"

        session_data = {
            "timestamp": timestamp,
            "summary": summary,
            "gems": [
                {
                    "domain": g.domain.name,
                    "tld": g.domain.tld,
                    "age_years": g.domain.age_years,
                    "seo_score": g.seo.seo_score,
                    "da": g.seo.domain_authority,
                    "brandability": g.brandability.score,
                    "total_score": g.total_score,
                    "estimated_value": g.estimated_value,
                    "is_gem": g.is_gem,
                }
                for g in gems
            ],
            "registrations": [
                {
                    "domain": r.domain,
                    "success": r.success,
                    "registrar": r.registrar,
                    "cost": r.cost,
                    "confirmation_id": r.confirmation_id,
                    "error": r.error_message,
                }
                for r in results
            ],
        }

        results_file.write_text(json.dumps(session_data, indent=2, default=str))
        print(f"Session results saved to {results_file}")

        self.results_history.append(session_data)

    def generate_report(self, analyses: list[DomainAnalysis]) -> str:
        """Generate a human-readable report of domain analyses."""
        lines = []
        lines.append("=" * 80)
        lines.append("DOMAIN SNIPER ANALYSIS REPORT")
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append("=" * 80)
        lines.append("")

        # Summary stats
        gems = [a for a in analyses if a.is_gem]
        total_value = sum(a.estimated_value for a in gems)

        lines.append(f"Total Domains Analyzed: {len(analyses)}")
        lines.append(f"Gem Domains Found: {len(gems)}")
        lines.append(f"Total Estimated Value: ${total_value:,.2f}")
        lines.append("")

        # Top domains
        lines.append("TOP 10 DOMAINS BY SCORE:")
        lines.append("-" * 80)
        lines.append(
            f"{'Domain':<30} {'Score':>8} {'DA':>6} {'Brand':>7} {'Value':>12} {'Gem':>5}"
        )
        lines.append("-" * 80)

        for analysis in analyses[:10]:
            lines.append(
                f"{analysis.domain.name:<30} "
                f"{analysis.total_score:>8.2f} "
                f"{analysis.seo.domain_authority:>6} "
                f"{analysis.brandability.score:>7.1f} "
                f"${analysis.estimated_value:>11,.2f} "
                f"{'YES' if analysis.is_gem else 'NO':>5}"
            )

        lines.append("")

        # Detailed gem analysis
        if gems:
            lines.append("DETAILED GEM ANALYSIS:")
            lines.append("-" * 80)

            for i, gem in enumerate(gems[:5], 1):
                lines.append(f"\n{i}. {gem.domain.name}")
                lines.append(f"   TLD: .{gem.domain.tld}")
                lines.append(f"   Age: {gem.domain.age_years or 'Unknown'} years")
                lines.append(f"   Total Score: {gem.total_score:.2f}/100")
                lines.append(f"   SEO Score: {gem.seo.seo_score:.2f}/100")
                lines.append(f"   - Domain Authority: {gem.seo.domain_authority}")
                lines.append(f"   - Domain Rating: {gem.seo.domain_rating}")
                lines.append(f"   - Referring Domains: {gem.seo.referring_domains:,}")
                lines.append(f"   - Backlink Quality: {gem.seo.backlink_quality.value}")
                lines.append(f"   Brandability: {gem.brandability.score:.1f}/10")
                lines.append(f"   - Memorability: {gem.brandability.memorability:.1f}/10")
                lines.append(f"   - Pronounceability: {gem.brandability.pronounceability:.1f}/10")
                if gem.brandability.industry_fit:
                    lines.append(f"   - Industry Fit: {', '.join(gem.brandability.industry_fit[:3])}")
                lines.append(f"   Estimated Value: ${gem.estimated_value:,.2f}")
                lines.append(f"   Registration Cost: ${gem.registration_cost:.2f}")
                lines.append(f"   ROI: {gem.estimated_value / gem.registration_cost:.1f}x")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


async def run_snipe_session(max_domains: int = 100) -> dict:
    """Convenience function to run a complete sniping session."""
    orchestrator = Orchestrator()
    return await orchestrator.auto_snipe(max_scan=max_domains)


async def analyze_expiring(max_domains: int = 50) -> list[DomainAnalysis]:
    """Convenience function to scan and analyze expiring domains."""
    orchestrator = Orchestrator()
    return await orchestrator.scan_and_analyze(max_domains=max_domains)
