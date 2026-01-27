"""Eurostat API Service for retrieving European statistics data.

This service can be used to fetch statistical data from Eurostat
to support RIA impact assessments with real data.
"""

import httpx
from typing import Dict, Any, Optional, List
import json


class EurostatService:
    """Service for querying Eurostat API."""
    
    BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0"
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize Eurostat service.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    async def get_data(
        self,
        dataset_code: str,
        filters: Optional[Dict[str, str]] = None,
        format: str = "JSON",
        lang: str = "EN"
    ) -> Optional[Dict[str, Any]]:
        """
        Get data from Eurostat API.
        
        Args:
            dataset_code: Eurostat dataset code (e.g., 'nama_10_gdp', 'une_rt_m')
            filters: Dictionary of filters (e.g., {'geo': 'BE', 'time': '2022'})
            format: Output format ('JSON', 'JSONSTAT', 'CSV')
            lang: Language ('EN', 'FR', 'DE')
        
        Returns:
            Dictionary with Eurostat data or None if error
        """
        url = f"{self.BASE_URL}/data/{dataset_code}"
        
        params = {
            "format": format,
            "lang": lang
        }
        
        # Add filters
        if filters:
            params.update(filters)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                if format.upper() == "JSON":
                    return response.json()
                else:
                    return {"content": response.text, "format": format}
                    
        except Exception as e:
            print(f"Error querying Eurostat API: {e}")
            return None
    
    async def get_belgium_data(
        self,
        dataset_code: str,
        time_period: Optional[str] = None,
        additional_filters: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get data for Belgium from Eurostat.
        
        Args:
            dataset_code: Eurostat dataset code
            time_period: Time period (e.g., '2022', '2023')
            additional_filters: Additional filters to apply
        
        Returns:
            Dictionary with Belgium data or None if error
        """
        filters = {"geo": "BE"}  # BE = Belgium
        
        if time_period:
            filters["time"] = time_period
        
        if additional_filters:
            filters.update(additional_filters)
        
        return await self.get_data(dataset_code, filters=filters)
    
    async def get_eu_data(
        self,
        dataset_code: str,
        time_period: Optional[str] = None,
        additional_filters: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get data for EU aggregate from Eurostat.
        
        Args:
            dataset_code: Eurostat dataset code
            time_period: Time period (e.g., '2022', '2023')
            additional_filters: Additional filters to apply
        
        Returns:
            Dictionary with EU data or None if error
        """
        filters = {"geo": "EU27_2020"}  # EU27 aggregate
        
        if time_period:
            filters["time"] = time_period
        
        if additional_filters:
            filters.update(additional_filters)
        
        return await self.get_data(dataset_code, filters=filters)
    
    async def search_datasets(
        self,
        query: str,
        lang: str = "EN"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for available datasets (if Eurostat provides this endpoint).
        
        Note: This may require a different endpoint or manual dataset lookup.
        
        Args:
            query: Search query
            lang: Language
        
        Returns:
            List of matching datasets or None
        """
        # Eurostat doesn't have a direct search API, but datasets are documented
        # Common datasets for RIA:
        common_datasets = {
            "gdp": "nama_10_gdp",
            "unemployment": "une_rt_m",
            "employment": "lfsi_emp_a",
            "population": "demo_pjan",
            "poverty": "ilc_li02",
            "health": "hlth_silc_01",
            "education": "educ_uoe_enr01",
            "environment": "env_air_gge"
        }
        
        results = []
        query_lower = query.lower()
        
        for key, code in common_datasets.items():
            if query_lower in key:
                results.append({
                    "code": code,
                    "name": key,
                    "description": f"Eurostat dataset: {code}"
                })
        
        return results if results else None


# Example usage functions
async def get_belgium_gdp(year: str = "2022") -> Optional[Dict[str, Any]]:
    """Get Belgium GDP data for a specific year."""
    service = EurostatService()
    return await service.get_belgium_data("nama_10_gdp", time_period=year)


async def get_belgium_unemployment(year: str = "2022") -> Optional[Dict[str, Any]]:
    """Get Belgium unemployment data for a specific year."""
    service = EurostatService()
    return await service.get_belgium_data("une_rt_m", time_period=year)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        service = EurostatService()
        
        # Test: Get Belgium GDP data
        print("Testing Eurostat API...")
        print("=" * 60)
        
        # Get Belgium GDP for 2022
        data = await service.get_belgium_data("nama_10_gdp", time_period="2022")
        if data:
            print("✅ Successfully retrieved Belgium GDP data")
            print(f"   Data keys: {list(data.keys())[:5]}")
        else:
            print("❌ Failed to retrieve data")
    
    asyncio.run(test())
