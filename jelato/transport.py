def send_envelope(envelope):
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


