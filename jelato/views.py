from datetime import datetime
import httplib2
import simplejson

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from jelato.models import Datum
from jelato.models import UserInfo
import utils


def home(request):
    if request.user.is_authenticated():
        envelopes = request.user.envelope_set \
                    .order_by('-ctime')
        subscription_posts = fetch_subscription_posts(
            [s.uri for s in request.user.subscription_set.all()])
        return render_to_response(
            'jelato/home_auth.html',
            {
                'conversations': [envelope.carries for envelope in envelopes],
                'subscription_posts': subscription_posts
            },
            context_instance=RequestContext(request))
    return render_to_response(
        'jelato/home.html',
        context_instance=RequestContext(request))
        
def public_message_view(request, username, message_uuid):
    user = User.objects.get(username=username)
    message = user.sentmessage_set.filter(is_public=True).get(uuid=message_uuid)
    return render_to_response(
        'jelato/public_message_view.html',
        { 'message': message },
        context_instance=RequestContext(request))
        
def user_profile(request, username):
    user = User.objects.get(username=username)
    messages = user.sentmessage_set.filter(is_public=True)
    subscriptions = user.subscription_set.all()
    return render_to_response(
        'jelato/profile.html',
        {
            'messages': messages,
            'subscriptions': subscriptions,
            'username': username
        },
        context_instance=RequestContext(request))

def post_office(request):
    uuid = request.META['HTTP_X_JELATO_UUID']
    content_type = request.META['CONTENT_TYPE']
    sender_uri = request.META['HTTP_X_JELATO_SENDER']
    replies_to = request.META['HTTP_X_JELATO_REPLIES_TO']
    recipients_to = request.META['HTTP_X_JELATO_RECIPIENTS_TO']
    recipients_cc = request.META['HTTP_X_JELATO_RECIPIENTS_CC']
    recipients_bcc = request.META['HTTP_X_JELATO_RECIPIENTS_BCC']
    content = request.raw_post_data
    
    print 'Post office received this message:'
    print ' Recipients To: ' + recipients_to
    print ' Recipients CC: ' + recipients_cc
    print ' Recipients BCC: ' + recipients_bcc
    print ' UUID: ' + uuid
    print ' Content type: ' + content_type
    print ' Sender URI: ' + sender_uri
    print ' Replies for: ' + replies_to
    print ' Content: "%s"' % content
    
    try:
        message = _make_message(
            content=content,
            content_type=content_type,
            encoding='utf-8',
            replies_to=replies_to,
            uuid=uuid)
        
        # FIXME: Do not hard code server name
        SERVER_NAME='localhost:8000'
        all_recipients = simplejson.loads(recipients_to) + simplejson.loads(recipients_cc) + simplejson.loads(recipients_bcc)
        all_addresses = [Address(recipient) for recipient in all_recipients]
        addresses_for_here = [addr for addr in all_addresses if addr.server == SERVER_NAME]
        usernames_for_here = [addr.username for addr in addresses_for_here]
        for recipient_username in usernames_for_here:
            try:
                user = User.objects.get(username=recipient_username)
            except User.DoesNotExist:
                continue
            envelope = _make_envelope(
                user,
                froms=Address(sender_uri),
                tos=[Address(addr) for addr in simplejson.loads(recipients_to)],
                ccs=[Address(addr) for addr in simplejson.loads(recipients_cc)],
                bccs=[Address(addr) for addr in simplejson.loads(recipients_bcc)], # FIXME: Keep only recipient address
                carries=message)
    except Exception, e:
        print 'Receive exception: ' + str(e)
    return HttpResponse('TODO', status=201)

def public_messages(request, username):
    public_messages = User.objects.get(username=username).sentmessage_set.filter(is_public=True).order_by('-time_sent')
    server_and_port = request.META['SERVER_NAME'] + ':' + request.META['server']
    return render_to_response(
        'jelato/feeds/public_messages.html',
        {
            'messages': public_messages,
            'username': username,
            'server_and_port': server_and_port
        },
        context_instance=RequestContext(request),
        mimetype='application/atom+xml')


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
    
def _make_address(server_name, server_port, username):
    return Address(server_name + ':' + server_port + '/' + username)

def _make_message(content, content_type, encoding, replies_to=None, uuid=None):
    if uuid is None:
        uuid=utils.uuid()
    if replies_to is None:
        replies_to = ''
    
    try:    
        datum = Datum.objects.get(uuid=uuid)
    except Datum.DoesNotExist:
        datum = Datum.objects.create(
            uuid=uuid,
            content=content,
            content_type=content_type,
            encoding=encoding,
            replies_to=replies_to)
    
    return datum

def _make_envelope(user, froms, tos, ccs, bccs, carries):
    return user.envelope_set.create(
        froms=str(froms),
        tos=simplejson.dumps([str(addr) for addr in tos]),
        ccs=simplejson.dumps([str(addr) for addr in ccs]),
        bccs=simplejson.dumps([str(addr) for addr in bccs]),
        carries=carries)

@login_required
def send_message(request, is_public):
    if request.method == 'POST':
        content = request.POST['content']
        if is_public:
            recipients_to = []
            recipients_cc = []
            recipients_bcc = []
        else:
            print 'to: ' + str(request.POST['recipients_to'])
            recipients_to = addresses_as_tuple(request.POST['recipients_to'])
            recipients_cc = addresses_as_tuple(request.POST['recipients_cc'])
            recipients_bcc = addresses_as_tuple(request.POST['recipients_bcc'])
            
        sender_address = _make_address(
            server_name=request.META['SERVER_NAME'],
            server_port=request.META['SERVER_PORT'],
            username=request.user.username)
        message = _make_message(
            content=content,
            content_type='text/html',
            encoding='utf-8')
        envelope = _make_envelope(
            request.user,
            froms=sender_address,
            tos=recipients_to,
            ccs=recipients_cc,
            bccs=recipients_bcc,
            carries=message)
        _send_envelope(envelope)
        return HttpResponseRedirect('/')
    return render_to_response(
        'jelato/send_message.html',
        { 'is_public': is_public },
        context_instance=RequestContext(request))

@login_required
def sent_messages(request):
    messages = request.user.sentmessage_set.all()
    return render_to_response(
        'jelato/sent_messages.html',
        { 'messages': messages },
        context_instance=RequestContext(request))

@login_required
def subscriptions(request):
    if request.method == 'POST':
        subscription_uri = request.POST['subscription_uri']
        request.user.subscription_set.create(uri=subscription_uri)
        return HttpResponseRedirect('/subscriptions')

    subscriptions = request.user.subscription_set.all()
    return render_to_response(
        'jelato/subscriptions.html',
        { 'subscriptions': subscriptions },
        context_instance=RequestContext(request))

@login_required
def contacts(request):
    if request.method == 'POST':
        contact_uri = request.POST['contact_uri']
        name = request.POST['contact_name']
        request.user.contact_set.create(
            contact_uri=contact_uri,
            name=name,
            time_added=datetime.utcnow(),
            comments='')
        return HttpResponseRedirect('/contacts')

    contacts = request.user.contact_set.all()
    return render_to_response(
        'jelato/contacts.html',
        { 'contacts': contacts },
        context_instance=RequestContext(request))
    
@login_required
def conversation_view(request, message_uuid):
    envelope = request.user.envelope_set.get(carries__uuid=message_uuid)
    envelope_list = get_conversation_list(request.user, envelope)
    print len(envelope_list)
    #TODO: sort messages
    messages = [e.carries for e in envelope_list]
    
    # TODO: mark as read
    #envelope.is_read = True
    #envelope.save()
    return render_to_response(
        'jelato/conversation_view.html',
        { 'messages': messages },
        context_instance=RequestContext(request))



@login_required
def message_reply(request, message_uuid):
    orig_envelope = request.user.envelope_set.get(carries__uuid=message_uuid)
    if request.method == 'POST':
        reply_content = request.POST['reply_content']
        
        sender_address = _make_address(
            server_name=request.META['SERVER_NAME'],
            server_port=request.META['SERVER_PORT'],
            username=request.user.username)
            
        orig_tos=simplejson.loads(orig_envelope.tos)
        if sender_address.uri_format() in orig_tos:
            orig_tos.remove(sender_address.uri_format())
        orig_ccs=simplejson.loads(orig_envelope.ccs)
        if sender_address.uri_format() in orig_ccs:
            orig_ccs.remove(sender_address.uri_format())
        orig_tos.append(orig_envelope.froms)
        orig_tos = [Address(addr) for addr in orig_tos]
        orig_ccs = [Address(addr) for addr in orig_ccs]
        
        message = _make_message(
            content=reply_content,
            content_type='text/html',
            encoding='utf-8',
            replies_to=message_uuid)
        envelope = _make_envelope(
            request.user,
            froms=sender_address,
            tos=orig_tos,
            ccs=orig_ccs,
            bccs=[],
            carries=message)
        _send_envelope(envelope)
        return HttpResponseRedirect('/')
    return render_to_response(
        'jelato/message_reply.html',
        {
            'envelope': orig_envelope
        },
        context_instance=RequestContext(request))
    
@login_required
def message_forward(request, message_uuid):
    return render_to_response(
        'jelato/message_forward.html',
        context_instance=RequestContext(request))
   
class PublicPost(object):
    def __init__(self, time_sent, content, link):
        self.time_sent = time_sent
        self.content = content
        self.link = link
        
    def summary(self):
        return utils.summarize(self.content, 50)
             
def fetch_subscription_posts(uri_list):
    import feedparser
    posts = []
    for uri in uri_list:
        d = feedparser.parse('http://' + uri + '/feeds/public-messages')
        for entry in d.entries:
            post = PublicPost(entry['updated'], entry['summary'], entry['link'])
            posts.append(post)
    return posts


def get_conversation_list(user, root_envelope):
    envelope_list = [root_envelope]
    children = user.envelope_set.filter(carries__replies_to=root_envelope.carries.uuid).distinct()
    for child in children:
        envelope_list.extend(get_conversation_list(user, child))
    return envelope_list

class DestinationRecord(object):
    def __init__(self):
        self.to = []
        self.cc = []
        self.bcc = []

def _send_envelope(envelope):
    can_send = (envelope.tos or envelope.ccs or envelope.bccs)
    if can_send:
        servers = set()
        all_addresses = simplejson.loads(envelope.tos) + simplejson.loads(envelope.ccs) + simplejson.loads(envelope.bccs)
        all_addresses = [Address(addr) for addr in all_addresses]
        for recipient in all_addresses:
            servers.add(recipient.server)

        for server in servers:
            print 'Send to server %s:' % server
            print ' UUID: ' + envelope.carries.uuid
            print ' Sender URI: ' + envelope.froms
            print ' To: ' + envelope.tos
            print ' CC: ' + envelope.ccs
            print ' BCC: ' + envelope.bccs
            print ' Content: "%s"' % envelope.carries.content
            
            headers = {
                'Content-type': 'application/xml',
                'X-Jelato-UUID': envelope.carries.uuid,
                'X-Jelato-Sender': envelope.froms,
                'X-Jelato-Replies-To': envelope.carries.replies_to,
                'X-Jelato-Recipients-To': envelope.tos,
                'X-Jelato-Recipients-CC': envelope.ccs,
                'X-Jelato-Recipients-BCC': envelope.bccs, # TODO: maybe restrict to per-server
            }
            
            http = httplib2.Http()
            post_office_url = 'http://' + server + '/post-office/';
            (response, content) = http.request(
                post_office_url,
                'POST',
                envelope.carries.content,
                headers=headers)


