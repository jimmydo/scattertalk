from datetime import datetime
import httplib2

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from jelato.models import ReceivedMessage
from jelato.models import UserInfo
import utils


def home(request):
    if request.user.is_authenticated():
        messages = _get_user_profile(request.user).received_messages \
                    .filter(reply_for='') \
                    .order_by('-time_sent')
        subscription_posts = fetch_subscription_posts(
            [s.uri for s in request.user.subscription_set.all()])
        return render_to_response(
            'jelato/home_auth.html',
            {
                'messages': messages,
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
    reply_for = request.META['HTTP_X_JELATO_REPLY_FOR']
    recipients = request.META['HTTP_X_JELATO_RECIPIENTS'].split(';')
    content = request.raw_post_data
    
    print 'Post office received this message:'
    print ' Recipients: ' + str(recipients)
    print ' UUID: ' + uuid
    print ' Content type: ' + content_type
    print ' Sender URI: ' + sender_uri
    print ' Reply for: ' + reply_for
    print ' Content: "%s"' % content
    
    received_message = ReceivedMessage.objects.create(
        content=content,
        uuid=uuid,
        content_type=content_type,
        sender_uri=sender_uri,
        time_sent=datetime.utcnow(),
        reply_for=reply_for)
    
    for recipient_username in recipients:
        try:
            user = User.objects.get(username=recipient_username)
        except User.DoesNotExist:
            print 'Could not find user: ' + recipient_username
        else:
            _get_user_profile(user).received_messages.add(received_message)
    return HttpResponse('TODO', status=201)

def public_messages(request, username):
    public_messages = User.objects.get(username=username).sentmessage_set.filter(is_public=True).order_by('-time_sent')
    server_and_port = request.META['SERVER_NAME'] + ':' + request.META['SERVER_PORT']
    return render_to_response(
        'jelato/feeds/public_messages.html',
        {
            'messages': public_messages,
            'username': username,
            'server_and_port': server_and_port
        },
        context_instance=RequestContext(request),
        mimetype='application/atom+xml')

@login_required
def send_message(request, is_public):
    if request.method == 'GET':
        return render_to_response(
            'jelato/send_message.html',
            { 'is_public': is_public },
            context_instance=RequestContext(request))
    
    content = request.POST['content']
    
    if is_public:
        recipients = None
    else:
        recipients = request.POST['recipients'].split(';')
    
    _send_message_real(request.user, request.META['SERVER_NAME'] + ':' + request.META['SERVER_PORT'], '', content, recipients)
    return HttpResponseRedirect('/')

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
def message_view(request, message_uuid):
    profile = request.user.get_profile()
    try:
        message = profile.received_messages.get(uuid=message_uuid)
    except ReceivedMessage.DoesNotExist:
        print 'Message does not exist for the user'
        return HttpResponseRedirect('/')
        
    messages = get_thread(message)
    
    message.is_read = True
    message.save()
    return render_to_response(
        'jelato/message_view.html',
        { 'messages': messages },
        context_instance=RequestContext(request))
        
@login_required
def message_reply(request, message_uuid):
    orig_message = ReceivedMessage.objects.get(uuid=message_uuid)
    if request.method == 'POST':
        reply_content = request.POST['reply_content']
        _send_message_real(request.user, request.META['SERVER_NAME'] + ':' + request.META['SERVER_PORT'], message_uuid, reply_content, [orig_message.sender_uri[7:]], False)
    
    return render_to_response(
        'jelato/message_reply.html',
        {
            'orig_message': orig_message
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
    
def get_thread(first_message):
    from models import SentMessage
    replies = ReceivedMessage.objects.filter(reply_for=first_message.uuid)
    replies2 = SentMessage.objects.filter(reply_for=first_message.uuid)
    both = []
    for r in replies:
        both.append(r)
    for r in replies2:
        both.append(r)
    if len(both) == 0:
        return [first_message]
    
    all_replies = [first_message]
    for reply in both:
        all_replies.extend(get_thread(reply))
        
    return all_replies
    
def _send_message_real(cur_user, server_port, reply_for_uuid, content, recipients):
    uuid = utils.uuid()
    print str(type(uuid))
    is_public = (recipients is None)
    sent_message = cur_user.sentmessage_set.create(
        uuid=uuid,
        content_type='placeholder',
        content=content,
        time_sent=datetime.utcnow(),
        reply_for='',
        is_public=is_public)
    
    if not is_public:
        server_map = {}
        
        # Each recipient is in server:port/username format.
        for recipient in recipients:
            print 'Recipient: ' + recipient
            (server, username) = recipient.split('/')
            if not server_map.has_key(server):
                server_map[server] = []
            server_map[server].append(username)
            
        for server in server_map.keys():
            recip_list = ';'.join(server_map[server])
            http = httplib2.Http()
            url = 'http://' + server + '/post-office/';
            
            sender_uri = 'http://' + server_port + \
                    '/' + cur_user.username
            print 'Send to server %s:' % server
            print ' UUID: ' + uuid
            print ' Sender URI: ' + sender_uri
            print ' Recipients: ' + recip_list
            print ' Content: "%s"' % content
            
            headers = {
                'Content-type': 'application/xml',
                'X-Jelato-UUID': uuid,
                'X-Jelato-Sender': sender_uri,
                'X-Jelato-Reply-For': reply_for_uuid,
                'X-Jelato-Recipients': recip_list
            }
            (response, content) = http.request(
                url,
                'POST',
                content,
                headers=headers)

def _get_user_profile(user):
    try:
        profile = user.get_profile()
    except UserInfo.DoesNotExist:
        return UserInfo.objects.create(
            user=user,
            public_key=utils.uuid(), # FIXME: Temporarily using UUID
            location='',
            comment='')
    else:
        return profile

