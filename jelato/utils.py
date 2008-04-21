from uuid import uuid4

def uuid():
    return str(uuid4()).replace('-', '')

def summarize(text, max_length):
    if len(text) <= max_length:
        return text
    else:
        return text[0:max_length].strip() + '...'

class Address(object):
    def __init__(self, address):
        (self.server, self.username) = normalized_address(address).split('/')
        
    def __str__(self):
        return self.uri_format()
        
    def uri_format(self):
        return self.server + '/' + self.username
        
    def email_format(self):
        return self.username + '@' + self.server

def normalized_address(address):
    """
    Normalize an address to be in someserver.com/username format.
    
    The input address may be in either of these formats:
    someserver.com/username
    username@someserver.com
    
    """
    if '@' not in address:
        return address
    
    (username, server) = address.split('@')
    return server + '/' + username

def addresses_as_tuple(addresses_string):
    """
    Parse a string of addresses into a tuple of Address objects.
    
    The addresses are separated by semicolons, and each address can be in
    either of these formats:
    someserver.com/username
    username@someserver.com
    
    """
    if addresses_string:
        addresses_string = addresses_string.strip()
    if not addresses_string:
        return ()
    
    addresses = [addr.strip() for addr in addresses_string.split(';')]
    return tuple([Address(addr) for addr in addresses])
    
def make_address(request, user):
    return Address(
        request.META['SERVER_NAME'] + ':' + request.META['SERVER_PORT'] + '/' + user.username)

