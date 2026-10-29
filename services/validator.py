"""Syntax and domain checks; MX does not establish mailbox deliverability."""
import dns.resolver
from email_validator import EmailNotValidError, validate_email


def validate_business_email(value):
    try:
        normalized = validate_email(value, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return value, False, False, 'invalid'
    domain = normalized.rsplit('@', 1)[1]
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=3)
        mx = any(str(record.exchange) != '.' for record in answers)
    except (dns.exception.DNSException, OSError):
        mx = False
    return normalized, True, mx, 'unverified_mailbox' if mx else 'syntax_valid'
