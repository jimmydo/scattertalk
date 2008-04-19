from django.db import models
from django.contrib.auth.models import User
from utils import summarize

UUID_LENGTH = 50
CONTACT_URI_LENGTH=1024
MAX_SUMMARY_LENGTH=50

# {{{ Single instance store for messages

class Datum(models.Model):
    """
    Datum should each be resources, e.g. http://foobar/data/1ef23...

    (Not all may be reachable for privacy reasons. We will use acls or
    capability methods to enforce this)

    The content may contain, say, an envelope, which itself may refer
    to other Datum.
    """
    uuid = models.CharField(max_length=UUID_LENGTH, unique=True)
    content_type = models.CharField(max_length=100)
    encoding = models.CharField(max_length=32)
    content = models.TextField()
    ctime = models.DateTimeField(auto_now_add = True)
    mtime = models.DateTimeField(auto_now = True)

    def __unicode__(self):
        return self.uuid
        
    def summary(self):
        return summarize(self.content, MAX_SUMMARY_LENGTH)
            
    class Admin:
        pass

# }}}

# {{{ underlying model(s) for transmitted metadata
class Envelope(models.Model):
    # these require reification: connections to other users (i.e. URI
    # and human-readable names) also could exist wrapped inside Datum.

    # One that that is for sure is we don't support aggregates.

    froms = models.TextField()
    tos = models.TextField()
    ccs = models.TextField()
    carries = models.CharField(max_length=UUID_LENGTH)

    # We may want to doubly link this information, or otherwise make
    # concessions for performance.

    replies_to = models.CharField(max_length=UUID_LENGTH)

# }}}

# {{{ uncategorized

class ReceivedMessage(models.Model):
    uuid = models.CharField(max_length=UUID_LENGTH, unique=True)
    content_type = models.CharField(max_length=100)
    content = models.TextField() # might need to allow binary? probably not
    time_sent = models.DateTimeField()
    sender_uri = models.CharField(max_length=CONTACT_URI_LENGTH)
    reply_for = models.CharField(max_length=UUID_LENGTH)
    is_public = models.BooleanField()
    is_read = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.uuid
        
    def summary(self):
        return summarize(self.content, MAX_SUMMARY_LENGTH)
            
    class Admin:
        pass
    
class SentMessage(models.Model):
    user = models.ForeignKey(User)
    uuid = models.CharField(max_length=UUID_LENGTH, unique=True)
    content_type = models.CharField(max_length=100)
    content = models.TextField()
    time_sent = models.DateTimeField()
    reply_for = models.CharField(max_length=UUID_LENGTH)
    is_public = models.BooleanField()
    
    class Admin:
        pass
    
class UserInfo(models.Model):
    user = models.ForeignKey(User, unique=True)
    public_key = models.CharField(max_length=5000, unique=True)
    location = models.CharField(max_length=200)
    comment = models.CharField(max_length=500)
    received_messages = models.ManyToManyField(ReceivedMessage)
    # others: interests, birthday, picture
    
    class Admin:
        pass
        
class Subscription(models.Model):
    user = models.ForeignKey(User)
    uri = models.CharField(max_length=CONTACT_URI_LENGTH)
    
    class Admin:
        pass
    
class Contact(models.Model):
    user = models.ForeignKey(User)
    contact_uri = models.CharField(max_length=CONTACT_URI_LENGTH, unique=True)
    name = models.CharField(max_length=200)
    time_added = models.DateTimeField()
    comments = models.TextField()
    
    class Admin:
        pass

class Group(models.Model):
    name = models.CharField(max_length=200, unique=True)
    contacts = models.ManyToManyField(Contact)
    
    class Admin:
        pass
# }}}
