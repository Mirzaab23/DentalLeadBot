from extractors.emails import extract_emails
from extractors.social import extract_social

def test_extract_email():
    assert extract_emails('<a href="mailto:Office@dentalclinic.com">Email</a>') == ['office@dentalclinic.com']

def test_obfuscated_email():
    assert extract_emails('<p>office [at] dentalclinic.com</p>') == ['office@dentalclinic.com']

def test_social_and_shares():
    assert extract_social('<a href="https://www.instagram.com/clinic/?utm_source=x">Profile</a><a href="https://facebook.com/sharer/sharer.php">Share</a>') == [('instagram', 'https://instagram.com/clinic')]

