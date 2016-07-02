"""Atom syndication."""
import binascii
import datetime
import flask
import werkzeug.contrib.atom

from dnstwister import app, repository
import dnstwister.tools


@app.route('/atom/<hexdomain>')
def view(hexdomain):
    """Return new atom items for changes in resolved domains."""
    # Parse out the requested domain
    domain = dnstwister.tools.parse_domain(hexdomain)
    if domain is None:
        flask.abort(400, 'Malformed domain or domain not represented in hexadecimal format.')

    # Prepare a feed
    feed = werkzeug.contrib.atom.AtomFeed(
        title='dnstwister report for {}'.format(domain),
        feed_url='{}atom/{}'.format(flask.request.url_root, hexdomain),
        url='{}search/{}'.format(flask.request.url_root, hexdomain),
    )

    # The publish/update date for the placeholder is locked to 00:00:00.000
    # (midnight UTC) on the current day.
    today = datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Ensure the domain is registered.
    if not repository.is_domain_registered(domain):
        repository.register_domain(domain)

    # Retrieve the delta report
    delta_report = repository.get_delta_report(domain)

    # If we don't have a delta report yet, show the placeholder.
    if delta_report is None:
        feed.add(
            title='No report yet for {}'.format(domain),
            title_type='text',
            content=flask.render_template(
                'syndication/atom/placeholder.html', domain=domain
            ),
            content_type='html',
            author='dnstwister',
            updated=today,
            published=today,
            id='waiting:{}'.format(domain),
            url=feed.url,
        )

    else:

        # If there is a delta report, generate the feed and return it. We use
        # the actual date of generation here.
        updated = repository.delta_report_updated(domain)
        if updated is None:
            updated = today

        # Setting the ID to be epoch seconds, floored per 24 hours, ensure the
        # updates are only every 24 hours max.
        id_24hr = (updated - datetime.datetime(1970, 1, 1)).total_seconds()

        common_kwargs = {
            'title_type': 'text',
            'content_type': 'html',
            'author': 'dnstwister',
            'updated': updated,
            'published': updated,
            'url': feed.url,
        }

        for (dom, ip) in delta_report['new']:
            feed.add(
                title='NEW: {}'.format(dom),
                content=flask.render_template(
                    'syndication/atom/new.html',
                    ip=ip, hexdomain=binascii.hexlify(dom)
                ),
                id='new:{}:{}:{}'.format(dom, ip, id_24hr),
                **common_kwargs
            )

        for (dom, old_ip, new_ip) in delta_report['updated']:
            feed.add(
                title='UPDATED: {}'.format(dom),
                content=flask.render_template(
                    'syndication/atom/updated.html',
                    new_ip=new_ip, old_ip=old_ip,
                    hexdomain=binascii.hexlify(dom),
                ),
                id='updated:{}:{}:{}:{}'.format(dom, old_ip, new_ip, id_24hr),
                **common_kwargs
            )

        for dom in delta_report['deleted']:
            feed.add(
                title='DELETED: {}'.format(dom),
                content=flask.render_template(
                    'syndication/atom/deleted.html',
                ),
                id='deleted:{}:{}'.format(dom, id_24hr),
                **common_kwargs
            )

    feed_response = feed.get_response()

    repository.mark_delta_report_as_read(domain)

    return feed_response
