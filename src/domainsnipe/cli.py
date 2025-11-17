"""Command-line interface for DomainSnipe."""

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import Config, get_config, set_config
from .orchestrator import Orchestrator

console = Console()


@click.group()
@click.option("--config", "-c", type=click.Path(exists=False), help="Path to config file")
@click.pass_context
def main(ctx: click.Context, config: str | None):
    """DomainSnipe - Expiring Domain Sniper Bot

    Automatically find and register valuable expiring domains.
    """
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        config_path = Path(config)
        cfg = Config.load_from_file(config_path)
    else:
        cfg = Config.from_env()

    set_config(cfg)
    ctx.obj["config"] = cfg


@main.command()
@click.option("--count", "-n", default=50, help="Number of domains to scan")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
def scan(count: int, output: str | None):
    """Scan for expiring domains and display results."""

    async def _scan():
        orchestrator = Orchestrator()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Scanning and analyzing domains...", total=None)
            analyses = await orchestrator.scan_and_analyze(max_domains=count)

        if not analyses:
            console.print("[yellow]No domains found matching criteria.[/yellow]")
            return

        # Display table
        table = Table(title=f"Top {min(20, len(analyses))} Expiring Domains")
        table.add_column("Domain", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("DA", justify="right")
        table.add_column("Brand", justify="right")
        table.add_column("Est. Value", justify="right", style="green")
        table.add_column("Gem", justify="center")

        for analysis in analyses[:20]:
            gem_indicator = "[bold green]★[/bold green]" if analysis.is_gem else ""
            table.add_row(
                analysis.domain.name,
                f"{analysis.total_score:.1f}",
                str(analysis.seo.domain_authority),
                f"{analysis.brandability.score:.1f}",
                f"${analysis.estimated_value:,.0f}",
                gem_indicator,
            )

        console.print(table)

        # Summary
        gems = [a for a in analyses if a.is_gem]
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"Total analyzed: {len(analyses)}")
        console.print(f"Gems found: {len(gems)}")
        console.print(f"Total estimated value: ${sum(a.estimated_value for a in gems):,.2f}")

        # Save to file if requested
        if output:
            output_path = Path(output)
            data = {
                "domains": [
                    {
                        "name": a.domain.name,
                        "score": a.total_score,
                        "da": a.seo.domain_authority,
                        "brandability": a.brandability.score,
                        "estimated_value": a.estimated_value,
                        "is_gem": a.is_gem,
                    }
                    for a in analyses
                ]
            }
            output_path.write_text(json.dumps(data, indent=2))
            console.print(f"\nResults saved to {output_path}")

    asyncio.run(_scan())


@main.command()
@click.option("--count", "-n", default=100, help="Number of domains to scan")
def gems(count: int):
    """Find gem domains (high-value opportunities)."""

    async def _find_gems():
        orchestrator = Orchestrator()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Searching for gem domains...", total=None)
            gem_domains = await orchestrator.find_gems(max_scan=count)

        if not gem_domains:
            console.print("[yellow]No gem domains found.[/yellow]")
            return

        console.print(f"\n[bold green]Found {len(gem_domains)} Gem Domains![/bold green]\n")

        # Detailed display
        for i, gem in enumerate(gem_domains[:10], 1):
            console.print(f"[bold cyan]{i}. {gem.domain.name}[/bold cyan]")
            console.print(f"   Score: {gem.total_score:.1f}/100")
            console.print(f"   Domain Authority: {gem.seo.domain_authority}")
            console.print(f"   Brandability: {gem.brandability.score:.1f}/10")
            console.print(f"   [green]Estimated Value: ${gem.estimated_value:,.2f}[/green]")
            console.print(f"   [yellow]Registration Cost: ${gem.registration_cost:.2f}[/yellow]")
            console.print(f"   [bold]ROI: {gem.estimated_value / gem.registration_cost:.1f}x[/bold]")
            console.print()

    asyncio.run(_find_gems())


@main.command()
@click.argument("domain")
def analyze(domain: str):
    """Analyze a specific domain's value."""

    async def _analyze():
        from .analyzer import DomainAnalyzer
        from .models import DomainInfo

        parts = domain.rsplit(".", 1)
        if len(parts) != 2:
            console.print(f"[red]Invalid domain: {domain}[/red]")
            return

        base_name, tld = parts

        domain_info = DomainInfo(
            name=domain,
            tld=tld,
            drop_date=None,
            age_years=None,
            registrar="manual",
        )

        analyzer = DomainAnalyzer()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Analyzing {domain}...", total=None)
            analysis = await analyzer.analyze_domain(domain_info)

        console.print(f"\n[bold]Analysis for {domain}[/bold]\n")
        console.print(f"Total Score: [bold]{analysis.total_score:.2f}[/bold]/100")
        console.print(f"Is Gem: {'[green]YES[/green]' if analysis.is_gem else '[red]NO[/red]'}")
        console.print()

        console.print("[bold]SEO Metrics:[/bold]")
        console.print(f"  Domain Authority: {analysis.seo.domain_authority}")
        console.print(f"  Domain Rating: {analysis.seo.domain_rating}")
        console.print(f"  Referring Domains: {analysis.seo.referring_domains:,}")
        console.print(f"  Backlink Count: {analysis.seo.backlink_count:,}")
        console.print(f"  Backlink Quality: {analysis.seo.backlink_quality.value}")
        console.print(f"  SEO Score: {analysis.seo.seo_score:.2f}/100")
        console.print()

        console.print("[bold]Brandability:[/bold]")
        console.print(f"  Overall Score: {analysis.brandability.score:.1f}/10")
        console.print(f"  Length Score: {analysis.brandability.length_score:.1f}/10")
        console.print(f"  Memorability: {analysis.brandability.memorability:.1f}/10")
        console.print(f"  Pronounceability: {analysis.brandability.pronounceability:.1f}/10")
        if analysis.brandability.industry_fit:
            console.print(f"  Industry Fit: {', '.join(analysis.brandability.industry_fit)}")
        if analysis.brandability.reasoning:
            console.print(f"  Analysis: {analysis.brandability.reasoning}")
        console.print()

        console.print("[bold]Value Assessment:[/bold]")
        console.print(f"  Estimated Value: [green]${analysis.estimated_value:,.2f}[/green]")
        console.print(f"  Registration Cost: ${analysis.registration_cost:.2f}")
        console.print(f"  Potential ROI: [bold]{analysis.estimated_value / analysis.registration_cost:.1f}x[/bold]")

    asyncio.run(_analyze())


@main.command()
@click.argument("domain")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def register(domain: str, force: bool):
    """Attempt to register a specific domain."""

    async def _register():
        orchestrator = Orchestrator()

        if not force:
            if not click.confirm(f"Attempt to register {domain}?"):
                console.print("[yellow]Cancelled.[/yellow]")
                return

        console.print(f"[bold]Attempting to register {domain}...[/bold]")

        result = await orchestrator.manual_snipe(domain)

        if result is None:
            console.print("[red]Registration failed - invalid domain[/red]")
            return

        if result.success:
            console.print(f"\n[bold green]SUCCESS![/bold green]")
            console.print(f"Domain: {result.domain}")
            console.print(f"Registrar: {result.registrar}")
            console.print(f"Cost: ${result.cost:.2f}")
            console.print(f"Confirmation ID: {result.confirmation_id}")
        else:
            console.print(f"\n[bold red]FAILED[/bold red]")
            console.print(f"Domain: {result.domain}")
            console.print(f"Error: {result.error_message}")

    asyncio.run(_register())


@main.command()
@click.option("--count", "-n", default=100, help="Number of domains to scan")
@click.option("--dry-run", is_flag=True, help="Show what would be registered without registering")
def autosnipe(count: int, dry_run: bool):
    """Automatically find and register valuable domains."""
    config = get_config()

    if not config.sniper.auto_register and not dry_run:
        console.print("[red]Auto-registration is disabled in configuration.[/red]")
        console.print("Set auto_register=True in config or use --dry-run flag.")
        return

    async def _autosnipe():
        orchestrator = Orchestrator()

        if dry_run:
            console.print("[bold]DRY RUN MODE - No domains will be registered[/bold]\n")
            gems = await orchestrator.find_gems(max_scan=count)

            if gems:
                console.print(f"[green]Would attempt to register {len(gems)} domains:[/green]")
                for gem in gems[:10]:
                    console.print(f"  - {gem.domain.name} (Score: {gem.total_score:.1f}, Value: ${gem.estimated_value:,.0f})")
            else:
                console.print("[yellow]No gems found to register.[/yellow]")
        else:
            console.print("[bold red]AUTO-SNIPE MODE - Domains will be registered![/bold red]")
            if not click.confirm("Continue?"):
                console.print("[yellow]Cancelled.[/yellow]")
                return

            summary = await orchestrator.auto_snipe(max_scan=count)

            console.print("\n[bold]Session Summary:[/bold]")
            console.print(f"Domains scanned: {count}")
            console.print(f"Gems found: {summary.get('gems_found', 0)}")
            console.print(f"Registration attempts: {summary.get('total_attempts', 0)}")
            console.print(f"Successful: [green]{summary.get('successful', 0)}[/green]")
            console.print(f"Failed: [red]{summary.get('failed', 0)}[/red]")
            console.print(f"Total cost: ${summary.get('total_cost', 0):.2f}")

    asyncio.run(_autosnipe())


@main.command()
def report():
    """Generate a comprehensive analysis report."""

    async def _report():
        orchestrator = Orchestrator()

        console.print("[bold]Generating comprehensive report...[/bold]\n")

        analyses = await orchestrator.scan_and_analyze(max_domains=50)

        if not analyses:
            console.print("[yellow]No domains to report on.[/yellow]")
            return

        report_text = orchestrator.generate_report(analyses)
        console.print(report_text)

        # Save report
        config = get_config()
        config.data_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        report_file = config.data_dir / f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.write_text(report_text)
        console.print(f"\nReport saved to {report_file}")

    asyncio.run(_report())


@main.command()
def config_info():
    """Display current configuration."""
    cfg = get_config()

    console.print("[bold]Current Configuration:[/bold]\n")

    console.print("[bold]Scanner Settings:[/bold]")
    console.print(f"  TLDs: {', '.join(cfg.scanner.tlds)}")
    console.print(f"  Min domain age: {cfg.scanner.min_domain_age} years")
    console.print(f"  Domain length: {cfg.scanner.min_length}-{cfg.scanner.max_length} chars")
    console.print(f"  Batch size: {cfg.scanner.batch_size}")
    console.print()

    console.print("[bold]Analyzer Settings:[/bold]")
    console.print(f"  Min DA score: {cfg.analyzer.min_da_score}")
    console.print(f"  Min brandability: {cfg.analyzer.min_brandability}")
    console.print(f"  Gem threshold: {cfg.analyzer.gem_threshold}")
    console.print(f"  Use LLM: {cfg.analyzer.use_llm_analysis}")
    console.print()

    console.print("[bold]Sniper Settings:[/bold]")
    console.print(f"  Auto-register: {'[green]ENABLED[/green]' if cfg.sniper.auto_register else '[red]DISABLED[/red]'}")
    console.print(f"  Max registration cost: ${cfg.sniper.max_registration_cost}")
    console.print(f"  Min profit margin: {cfg.sniper.min_profit_margin}x")
    console.print(f"  Max daily registrations: {cfg.sniper.max_registrations_per_day}")
    console.print(f"  Registrar priority: {', '.join(cfg.sniper.registrar_priority)}")
    console.print()

    console.print("[bold]API Keys Configured:[/bold]")
    console.print(f"  Moz: {'[green]Yes[/green]' if cfg.api.moz_access_id else '[red]No[/red]'}")
    console.print(f"  Ahrefs: {'[green]Yes[/green]' if cfg.api.ahrefs_api_key else '[red]No[/red]'}")
    console.print(f"  Anthropic: {'[green]Yes[/green]' if cfg.api.anthropic_api_key else '[red]No[/red]'}")
    console.print(f"  GoDaddy: {'[green]Yes[/green]' if cfg.api.godaddy_api_key else '[red]No[/red]'}")
    console.print(f"  Namecheap: {'[green]Yes[/green]' if cfg.api.namecheap_api_key else '[red]No[/red]'}")


if __name__ == "__main__":
    main()
