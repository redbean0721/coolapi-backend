from pydantic import EmailStr

# mask email address
def mask_email(email: EmailStr) -> str:
    """Mask email for privacy, e.g. abcdef@123456.com -> abc****@123****.com"""
    local, domain = email.split("@")
    domain_parts = domain.split(".", 1) # 分離主域名和頂級域名

    masked_local = local[:3] + "****" if len(local) > 3 else local + "****"
    masked_domain = domain_parts[0][:3] + "****" if len(domain_parts[0]) > 3 else domain_parts[0] + "****"

    if len(domain_parts) > 1:
        masked_domain += "." + domain_parts[1]
    
    return f"{masked_local}@{masked_domain}"