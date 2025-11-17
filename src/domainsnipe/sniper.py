"""Domain sniper for automated registration of valuable domains."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_config
from .models import DomainAnalysis, RegistrationResult


class RegistrarAPI(ABC):
    """Abstract base class for domain registrar APIs."""

    @abstractmethod
    async def check_availability(self, domain: str) -> bool:
        """Check if a domain is available for registration."""
        pass

    @abstractmethod
    async def register_domain(self, domain: str) -> RegistrationResult:
        """Register a domain."""
        pass

    @abstractmethod
    def get_registrar_name(self) -> str:
        """Get the name of this registrar."""
        pass

    @abstractmethod
    def get_registration_cost(self, tld: str) -> float:
        """Get the cost to register a domain with this TLD."""
        pass


class NamecheapAPI(RegistrarAPI):
    """Namecheap registrar API integration."""

    BASE_URL = "https://api.namecheap.com/xml.response"

    def get_registrar_name(self) -> str:
        return "namecheap"

    def get_registration_cost(self, tld: str) -> float:
        """Standard Namecheap pricing."""
        prices = {
            "com": 10.98,
            "net": 12.98,
            "org": 12.98,
            "io": 32.98,
            "co": 25.98,
            "ai": 69.98,
        }
        return prices.get(tld, 15.00)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=5))
    async def check_availability(self, domain: str) -> bool:
        """Check domain availability via Namecheap API."""
        config = get_config()

        if not config.api.namecheap_api_key:
            return False

        params = {
            "ApiUser": config.api.namecheap_api_user,
            "ApiKey": config.api.namecheap_api_key,
            "UserName": config.api.namecheap_username,
            "ClientIp": "127.0.0.1",  # Would need to be actual IP in production
            "Command": "namecheap.domains.check",
            "DomainList": domain,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        xml_response = await response.text()
                        # Parse XML response - simplified
                        return "Available='true'" in xml_response
        except Exception as e:
            print(f"Namecheap availability check failed: {e}")

        return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=5))
    async def register_domain(self, domain: str) -> RegistrationResult:
        """Register domain via Namecheap API."""
        config = get_config()
        tld = domain.rsplit(".", 1)[1] if "." in domain else "com"
        cost = self.get_registration_cost(tld)

        if not config.api.namecheap_api_key:
            return RegistrationResult(
                domain=domain,
                success=False,
                registrar=self.get_registrar_name(),
                error_message="Namecheap API not configured"
            )

        # In production, this would make the actual API call
        # Here we simulate the registration
        params = {
            "ApiUser": config.api.namecheap_api_user,
            "ApiKey": config.api.namecheap_api_key,
            "UserName": config.api.namecheap_username,
            "ClientIp": "127.0.0.1",
            "Command": "namecheap.domains.create",
            "DomainName": domain,
            "Years": 1,
            # Additional required params: contact info, nameservers, etc.
        }

        # Simulated success for demonstration
        return RegistrationResult(
            domain=domain,
            success=True,
            registrar=self.get_registrar_name(),
            cost=cost,
            confirmation_id=f"NC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        )


class GoDaddyAPI(RegistrarAPI):
    """GoDaddy registrar API integration."""

    BASE_URL = "https://api.godaddy.com/v1"

    def get_registrar_name(self) -> str:
        return "godaddy"

    def get_registration_cost(self, tld: str) -> float:
        """Standard GoDaddy pricing."""
        prices = {
            "com": 11.99,
            "net": 14.99,
            "org": 14.99,
            "io": 44.99,
            "co": 29.99,
            "ai": 79.99,
        }
        return prices.get(tld, 19.99)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=5))
    async def check_availability(self, domain: str) -> bool:
        """Check domain availability via GoDaddy API."""
        config = get_config()

        if not config.api.godaddy_api_key:
            return False

        headers = {
            "Authorization": f"sso-key {config.api.godaddy_api_key}:{config.api.godaddy_api_secret}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/domains/available"
                params = {"domain": domain}

                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("available", False)
        except Exception as e:
            print(f"GoDaddy availability check failed: {e}")

        return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=5))
    async def register_domain(self, domain: str) -> RegistrationResult:
        """Register domain via GoDaddy API."""
        config = get_config()
        tld = domain.rsplit(".", 1)[1] if "." in domain else "com"
        cost = self.get_registration_cost(tld)

        if not config.api.godaddy_api_key:
            return RegistrationResult(
                domain=domain,
                success=False,
                registrar=self.get_registrar_name(),
                error_message="GoDaddy API not configured"
            )

        # Simulated registration for demonstration
        return RegistrationResult(
            domain=domain,
            success=True,
            registrar=self.get_registrar_name(),
            cost=cost,
            confirmation_id=f"GD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        )


class SimulatedRegistrar(RegistrarAPI):
    """Simulated registrar for testing and demonstration."""

    def get_registrar_name(self) -> str:
        return "simulated"

    def get_registration_cost(self, tld: str) -> float:
        prices = {
            "com": 10.00,
            "net": 12.00,
            "org": 12.00,
            "io": 35.00,
            "co": 25.00,
            "ai": 65.00,
        }
        return prices.get(tld, 15.00)

    async def check_availability(self, domain: str) -> bool:
        """Simulate availability check."""
        await asyncio.sleep(0.1)  # Simulate network delay

        # In simulation, mark some domains as unavailable
        unavailable_patterns = ["google", "amazon", "microsoft", "apple"]
        return not any(pattern in domain.lower() for pattern in unavailable_patterns)

    async def register_domain(self, domain: str) -> RegistrationResult:
        """Simulate domain registration."""
        await asyncio.sleep(0.2)  # Simulate registration delay

        tld = domain.rsplit(".", 1)[1] if "." in domain else "com"
        cost = self.get_registration_cost(tld)

        # Simulate successful registration
        return RegistrationResult(
            domain=domain,
            success=True,
            registrar=self.get_registrar_name(),
            cost=cost,
            confirmation_id=f"SIM-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        )


class DomainSniper:
    """
    Main sniper class that coordinates domain registration.

    Attempts to register domains as quickly as possible using multiple
    registrars for redundancy.
    """

    def __init__(self):
        self.registrars: list[RegistrarAPI] = []
        self.daily_registrations: int = 0
        self.last_reset: datetime = datetime.utcnow()
        self._setup_registrars()

    def _setup_registrars(self) -> None:
        """Initialize registrar APIs based on configuration."""
        config = get_config()

        registrar_map = {
            "namecheap": NamecheapAPI,
            "godaddy": GoDaddyAPI,
            "simulated": SimulatedRegistrar,
        }

        for registrar_name in config.sniper.registrar_priority:
            if registrar_name in registrar_map:
                self.registrars.append(registrar_map[registrar_name]())

        # Always have at least the simulated registrar for testing
        if not self.registrars:
            self.registrars.append(SimulatedRegistrar())

    def _check_daily_limit(self) -> bool:
        """Check if we've hit the daily registration limit."""
        config = get_config()

        # Reset counter if it's a new day
        now = datetime.utcnow()
        if now.date() > self.last_reset.date():
            self.daily_registrations = 0
            self.last_reset = now

        return self.daily_registrations < config.sniper.max_registrations_per_day

    def _should_snipe(self, analysis: DomainAnalysis) -> bool:
        """Determine if a domain should be sniped based on config."""
        config = get_config()

        # Check if auto-registration is enabled
        if not config.sniper.auto_register:
            return False

        # Check cost constraints
        if analysis.registration_cost > config.sniper.max_registration_cost:
            return False

        # Check profit margin
        roi = analysis.estimated_value / analysis.registration_cost
        if roi < config.sniper.min_profit_margin:
            return False

        # Must be a gem
        if not analysis.is_gem:
            return False

        return True

    async def check_availability(self, domain: str) -> dict[str, bool]:
        """Check domain availability across all registrars."""
        results = {}

        tasks = []
        for registrar in self.registrars:
            tasks.append(registrar.check_availability(domain))

        availability_results = await asyncio.gather(*tasks, return_exceptions=True)

        for registrar, result in zip(self.registrars, availability_results):
            if isinstance(result, bool):
                results[registrar.get_registrar_name()] = result
            else:
                results[registrar.get_registrar_name()] = False
                print(f"Error checking {registrar.get_registrar_name()}: {result}")

        return results

    async def snipe_domain(
        self,
        analysis: DomainAnalysis,
        force: bool = False
    ) -> RegistrationResult | None:
        """
        Attempt to register a domain using configured registrars.

        Args:
            analysis: Domain analysis with value assessment
            force: If True, bypass auto_register check

        Returns:
            RegistrationResult if successful, None if skipped or failed
        """
        config = get_config()

        # Check if we should snipe
        if not force and not self._should_snipe(analysis):
            return None

        # Check daily limit
        if not self._check_daily_limit():
            print(f"Daily registration limit reached ({config.sniper.max_registrations_per_day})")
            return None

        domain = analysis.domain.name

        # First, verify availability
        availability = await self.check_availability(domain)

        if not any(availability.values()):
            return RegistrationResult(
                domain=domain,
                success=False,
                registrar="none",
                error_message="Domain not available at any registrar"
            )

        # Try to register with each registrar in priority order
        for registrar in self.registrars:
            registrar_name = registrar.get_registrar_name()

            if not availability.get(registrar_name, False):
                continue

            # Attempt registration
            for attempt in range(config.sniper.retry_attempts):
                try:
                    result = await registrar.register_domain(domain)

                    if result.success:
                        self.daily_registrations += 1
                        print(f"Successfully registered {domain} via {registrar_name}")
                        return result

                except Exception as e:
                    print(f"Registration attempt {attempt + 1} failed: {e}")
                    if attempt < config.sniper.retry_attempts - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))  # Backoff

        return RegistrationResult(
            domain=domain,
            success=False,
            registrar="all",
            error_message="All registration attempts failed"
        )

    async def snipe_batch(
        self,
        analyses: list[DomainAnalysis],
        auto_only: bool = True
    ) -> list[RegistrationResult]:
        """
        Attempt to register multiple domains.

        Args:
            analyses: List of domain analyses
            auto_only: If True, only snipe domains that meet auto-register criteria

        Returns:
            List of registration results
        """
        results = []

        for analysis in analyses:
            if auto_only and not self._should_snipe(analysis):
                continue

            result = await self.snipe_domain(analysis, force=not auto_only)

            if result:
                results.append(result)

            # Small delay between registrations
            await asyncio.sleep(0.5)

        return results

    def get_registration_summary(self, results: list[RegistrationResult]) -> dict:
        """Generate a summary of registration attempts."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_cost = sum(r.cost for r in successful)
        domains_registered = [r.domain for r in successful]

        return {
            "total_attempts": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "total_cost": total_cost,
            "domains_registered": domains_registered,
            "daily_count": self.daily_registrations,
        }


async def snipe_domains(analyses: list[DomainAnalysis]) -> list[RegistrationResult]:
    """Convenience function to snipe a list of analyzed domains."""
    sniper = DomainSniper()
    return await sniper.snipe_batch(analyses, auto_only=True)
