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

from utils import summarize
import uuid


def home(request):
    if request.user.is_authenticated():
        try:
            profile = request.user.get_profile()
        except UserInfo.DoesNotExist:
            print 'User "%s" does not have a profile. Ignoring.' % request.user.username
            messages = []
        else:
            messages = profile.received_messages.filter(reply_for='').order_by('-time_sent')
        subscription_posts = fetch_subscription_posts([s.uri for s in request.user.subscription_set.all()])
        return render_to_response(
            'jelato/home_auth.html',
            {
                'messages': messages,
                'subscription_posts': subscription_posts
            },
            context_instance=RequestContext(request))
    return render_to_response('jelato/home.html')

def post_office(request):
    guid = request.META['HTTP_X_JELATO_GUID']
    content_type = request.META['CONTENT_TYPE']
    sender_uri = request.META['HTTP_X_JELATO_SENDER']
    reply_for = request.META['HTTP_X_JELATO_REPLY_FOR']
    recipients = request.META['HTTP_X_JELATO_RECIPIENTS'].split(';')
    content = request.raw_post_data
    
    print 'Post office received this message:'
    print ' Recipients: ' + str(recipients)
    print ' GUID: ' + guid
    print ' Content type: ' + content_type
    print ' Sender URI: ' + sender_uri
    print ' Reply for: ' + reply_for
    print ' Content: "%s"' % content
    
    received_message = ReceivedMessage.objects.create(
        content=content,
        guid=guid,
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
            try:
                profile = user.get_profile()
            except UserInfo.DoesNotExist:
                print 'User "%s" does not have profile. Creating one.' \
                    % recipient_username
                profile = UserInfo.objects.create(
                    user=user,
                    public_key=uuid.uuid(), # FIXME: Temporarily using GUID
                    location='placeholder location',
                    comment='placeholder comment')
                print 'Created profile.'
            profile.received_messages.add(received_message)
            print 'Added received message to profile'
    return HttpResponse('TODO', status=201)

@login_required
def send_message(request):
    if request.method == 'GET':
        return render_to_response(
            'jelato/send_message.html',
            { 'username': request.user.username },
            context_instance=RequestContext(request))
    
    content = request.POST['content']
    recipients = request.POST['recipients'].split(';')
    is_public = request.POST.has_key('is_public')
    
    guid = uuid.uuid()
    sent_message = request.user.sentmessage_set.create(
        guid=guid,
        content_type='placeholder',
        content=content,
        time_sent=datetime.utcnow(),
        reply_for='',
        is_public=is_public)
    
    if not is_public:
        server_map = {}
        
        # Each recipient is in server:port/username format.
        for recipient in recipients:
            (server, username) = recipient.split('/')
            if not server_map.has_key(server):
                server_map[server] = []
            server_map[server].append(username)
            
        for server in server_map.keys():
            recip_list = ';'.join(server_map[server])
            http = httplib2.Http()
            url = 'http://' + server + '/post-office/';
            
            sender_uri = 'http://' + request.META['SERVER_NAME'] + \
                    '/' + request.user.username
            print 'Send to server %s:' % server
            print ' GUID: ' + guid
            print ' Sender URI: ' + sender_uri
            print ' Recipients: ' + recip_list
            print ' Content: "%s"' % content
            
            headers = {
                'Content-type': 'application/xml',
                'X-Jelato-GUID': guid,
                'X-Jelato-Sender': sender_uri,
                'X-Jelato-Reply-For': '',
                'X-Jelato-Recipients': recip_list
            }
            (response, content) = http.request(
                url,
                'POST',
                content,
                headers=headers)
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

def public_messages(request, username):
    public_messages = User.objects.get(username=username).sentmessage_set.filter(is_public=True).order_by('-time_sent')
    return render_to_response(
        'jelato/public_messages.html',
        {
            'messages': public_messages,
            'username': username
        },
        context_instance=RequestContext(request),
        mimetype='application/atom+xml')

class PublicPost(object):
    def __init__(self, time_sent, content):
        self.time_sent = time_sent
        self.content = content
        
    def summary(self):
        return summarize(self.content, 50)

def fetch_subscription_posts(uri_list):
    import feedparser
    posts = []
    for uri in uri_list:
        d = feedparser.parse('http://' + uri + '/public-messages')
        for entry in d.entries:
            post = PublicPost(entry['updated'], entry['summary'])
            posts.append(post)
    return posts
    
@login_required
def message_view(request, message_guid):
    profile = request.user.get_profile()
    try:
        message = profile.received_messages.get(guid=message_guid)
    except ReceivedMessage.DoesNotExist:
        print 'Message does not exist for the user'
        return HttpResponseRedirect('/')
    
    message.is_read = True
    message.save()
    return render_to_response(
        'jelato/message_view.html',
        { 'message': message },
        context_instance=RequestContext(request))
