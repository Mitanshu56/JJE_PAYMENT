"""
FY (Financial Year) filter utility for admin-only filtering.
Ensures secure role-based FY filtering in backend.
"""


def apply_fy_filter(query_dict, fy_value):
    """
    Apply FY filter to a query dictionary.
    
    Args:
        query_dict: MongoDB query dictionary
        fy_value: Financial year value (only applied if provided and not None)
    
    Returns:
        Modified query dictionary with FY filter applied if applicable
    """
    if not fy_value:
        return query_dict
    
    # Create new query with FY filter
    result = dict(query_dict) if query_dict else {}
    result['financialYear'] = fy_value
    return result


def get_admin_fy_from_request(request_state) -> str:
    """
    Extract admin-selected FY from request state.
    
    Args:
        request_state: FastAPI request state object
    
    Returns:
        Financial year string if admin and FY provided, None otherwise
    """
    if not hasattr(request_state, 'role') or request_state.role != 'admin':
        return None
    
    if hasattr(request_state, 'fiscal_year'):
        return request_state.fiscal_year
    
    return None
