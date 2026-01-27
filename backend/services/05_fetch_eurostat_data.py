"""Service: Fetch Eurostat statistical data."""

from ..state.ria_state import RIAState
from ..eurostat_service import EurostatService


# Global Eurostat service instance (initialized once)
_eurostat_service = None


def _get_eurostat_service() -> EurostatService:
    """Get or initialize Eurostat service instance."""
    global _eurostat_service
    if _eurostat_service is None:
        try:
            _eurostat_service = EurostatService()
            print(f"✅ Eurostat service initialized")
        except Exception as e:
            print(f"⚠️  Could not initialize Eurostat service: {e}")
            _eurostat_service = None
    return _eurostat_service


async def fetch_eurostat_data_node(state: RIAState) -> RIAState:
    """
    Fetches baseline Eurostat data for all 21 themes.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with 'eurostat_data'
    """
    try:
        eurostat_service = _get_eurostat_service()
        if not eurostat_service:
            state["eurostat_data"] = {}
            return state
        
        # Fetch baseline data for all 21 themes
        # This would use the existing _fetch_baseline_eurostat_data pattern
        # For now, return empty dict
        state["eurostat_data"] = {}
        
        print(f"✅ Fetched Eurostat data for {len(state['eurostat_data'])} themes")
        
    except Exception as e:
        error_msg = f"Eurostat data fetch failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["eurostat_data"] = {}
    
    return state
