from src.database.mariadb import query_in_mariadb

def verify_api_key(api_key: str) -> bool:
    query = "SELECT COUNT(*) FROM api_keys WHERE api_key = ?"
    values = (api_key,)
    result = query_in_mariadb(query, values)
    return result[0][0] > 0

def permission_check(api_key: str, required_permission: str) -> bool:
    query = "SELECT permissions FROM api_keys WHERE api_key = ?"
    values = (api_key,)
    result = query_in_mariadb(query, values)
    if result:
        permissions = result[0][0]
        if "global" in permissions.split(","):
            return True
        else:
            return required_permission in permissions.split(",")
    else:
        return False
