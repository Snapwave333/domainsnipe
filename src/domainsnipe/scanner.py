"""Domain scanner for fetching expiring domain lists."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import AsyncIterator

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_config
from .models import DomainInfo, DomainStatus


class DomainSource(ABC):
    """Abstract base class for domain data sources."""

    @abstractmethod
    async def fetch_expiring_domains(self) -> AsyncIterator[DomainInfo]:
        """Fetch expiring domains from the source."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this source."""
        pass


class ExpiredDomainsNet(DomainSource):
    """Scraper for expireddomains.net pending delete lists."""

    BASE_URL = "https://www.expireddomains.net"

    def get_source_name(self) -> str:
        return "expireddomains.net"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _fetch_page(self, session: aiohttp.ClientSession, tld: str, page: int = 1) -> str:
        """Fetch a page of expiring domains."""
        # Note: This is a simulation - real implementation would need to handle
        # authentication and proper scraping of the actual site
        url = f"{self.BASE_URL}/deleted-domains/"
        params = {
            "ftlds[]": tld,
            "fstatus[]": "Pending Delete",
            "start": (page - 1) * 25,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DomainResearchBot/1.0)"
        }

        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                return await response.text()
            return ""

    def _parse_domain_row(self, row: BeautifulSoup) -> DomainInfo | None:
        """Parse a single domain row from the HTML."""
        try:
            cells = row.find_all("td")
            if len(cells) < 5:
                return None

            domain_cell = cells[0]
            domain_link = domain_cell.find("a")
            if not domain_link:
                return None

            domain_name = domain_link.text.strip()
            if not domain_name or "." not in domain_name:
                return None

            # Extract TLD
            parts = domain_name.rsplit(".", 1)
            if len(parts) != 2:
                return None

            base_name, tld = parts

            # Extract age if available
            age_years = None
            if len(cells) > 3:
                age_text = cells[3].text.strip()
                if age_text.isdigit():
                    age_years = int(age_text)

            # Extract drop date (usually within 5 days)
            drop_date = datetime.utcnow() + timedelta(days=5)

            return DomainInfo(
                name=domain_name,
                tld=tld,
                drop_date=drop_date,
                age_years=age_years,
                registrar="Unknown",
                status=DomainStatus.PENDING_DELETE,
            )
        except Exception:
            return None

    async def fetch_expiring_domains(self) -> AsyncIterator[DomainInfo]:
        """Fetch expiring domains from expireddomains.net."""
        config = get_config()
        tlds = config.scanner.tlds

        async with aiohttp.ClientSession() as session:
            for tld in tlds:
                try:
                    # Fetch first page for each TLD
                    html = await self._fetch_page(session, tld, page=1)
                    if not html:
                        continue

                    soup = BeautifulSoup(html, "html.parser")
                    table = soup.find("table", class_="base1")

                    if not table:
                        continue

                    rows = table.find_all("tr")[1:]  # Skip header
                    for row in rows:
                        domain = self._parse_domain_row(row)
                        if domain:
                            yield domain

                    # Rate limiting
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"Error fetching {tld} domains: {e}")
                    continue


class PendingDeleteAPI(DomainSource):
    """Simulated API source for pending delete domains."""

    def get_source_name(self) -> str:
        return "pending_delete_api"

    async def fetch_expiring_domains(self) -> AsyncIterator[DomainInfo]:
        """
        Fetch domains from pending delete API.

        This is a simulation - in production you would integrate with
        real APIs like:
        - Verisign CZDS for .com/.net
        - Public WHOIS databases
        - Commercial drop catching services
        """
        # Simulated high-quality expiring domains for demonstration
        sample_domains = [
            ("fastcar.com", "com", 15),
            ("cloudtech.io", "io", 8),
            ("greenleaf.net", "net", 12),
            ("swiftpay.co", "co", 5),
            ("dataflow.ai", "ai", 3),
            ("brightpath.org", "org", 10),
            ("nextstep.com", "com", 7),
            ("bluemoon.net", "net", 9),
            ("techwave.io", "io", 4),
            ("smartlink.com", "com", 11),
        ]

        for domain_name, tld, age in sample_domains:
            yield DomainInfo(
                name=domain_name,
                tld=tld,
                drop_date=datetime.utcnow() + timedelta(days=3),
                age_years=age,
                registrar="Various",
                status=DomainStatus.PENDING_DELETE,
            )
            await asyncio.sleep(0.1)  # Simulate API delay


class DomainScanner:
    """Main scanner that aggregates multiple domain sources."""

    def __init__(self):
        self.sources: list[DomainSource] = []
        self._setup_sources()

    def _setup_sources(self) -> None:
        """Initialize domain sources based on configuration."""
        config = get_config()
        source_map = {
            "expireddomains": ExpiredDomainsNet,
            "pending_delete_api": PendingDeleteAPI,
        }

        for source_name in config.scanner.sources:
            if source_name in source_map:
                self.sources.append(source_map[source_name]())

        # Always add the simulated API for demonstration
        if not any(isinstance(s, PendingDeleteAPI) for s in self.sources):
            self.sources.append(PendingDeleteAPI())

    def _filter_domain(self, domain: DomainInfo) -> bool:
        """Check if domain meets filtering criteria."""
        config = get_config()

        # Check TLD
        if domain.tld not in config.scanner.tlds:
            return False

        # Check length
        base_name = domain.base_name
        if len(base_name) < config.scanner.min_length:
            return False
        if len(base_name) > config.scanner.max_length:
            return False

        # Check age
        if domain.age_years is not None:
            if domain.age_years < config.scanner.min_domain_age:
                return False

        # Filter out obvious spam patterns
        spam_patterns = [
            "-online", "xxx", "porn", "casino", "poker",
            "viagra", "cialis", "pharmacy", "pills",
        ]
        lower_name = base_name.lower()
        if any(pattern in lower_name for pattern in spam_patterns):
            return False

        # Filter out domains with too many numbers
        digit_count = sum(c.isdigit() for c in base_name)
        if digit_count > len(base_name) * 0.3:  # More than 30% numbers
            return False

        # Filter out domains with too many hyphens
        if base_name.count("-") > 1:
            return False

        return True

    async def scan_all_sources(self) -> AsyncIterator[DomainInfo]:
        """Scan all configured sources for expiring domains."""
        seen_domains: set[str] = set()

        for source in self.sources:
            print(f"Scanning {source.get_source_name()}...")

            try:
                async for domain in source.fetch_expiring_domains():
                    # Deduplicate
                    if domain.name in seen_domains:
                        continue
                    seen_domains.add(domain.name)

                    # Apply filters
                    if self._filter_domain(domain):
                        yield domain

            except Exception as e:
                print(f"Error scanning {source.get_source_name()}: {e}")
                continue

    async def scan_batch(self, batch_size: int | None = None) -> list[DomainInfo]:
        """Scan and return a batch of domains."""
        if batch_size is None:
            batch_size = get_config().scanner.batch_size

        domains = []
        async for domain in self.scan_all_sources():
            domains.append(domain)
            if len(domains) >= batch_size:
                break

        return domains


async def scan_expiring_domains() -> list[DomainInfo]:
    """Convenience function to scan for expiring domains."""
    scanner = DomainScanner()
    return await scanner.scan_batch()
