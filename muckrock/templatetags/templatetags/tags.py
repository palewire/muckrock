"""
General temaplate tags
"""

from django.template import Library, Node, TemplateSyntaxError
from django.template.defaultfilters import stringfilter

import re

from settings import STATIC_URL

register = Library()

@register.simple_tag
def active(request, pattern):
    """Check url against pattern to determine active css attribute"""
    pattern = pattern.replace('{{user}}', str(request.user))
    if re.search(pattern, request.path):
        return 'current-tab'
    return ''

def page_links_common(page_obj, option_dict):
    """Return page links for surrounding pages"""

    def make_link(num, skip):
        """Make a link to page num"""
        options = ''.join('&amp;%s=%s' % (k, v) for k, v in option_dict.iteritems() if v)
        if num != skip:
            return '<a href="?page=%d%s">%d</a>' % (num, options, num)
        else:
            return str(num)

    pages = range(max(page_obj.number - 3, 1),
                  min(page_obj.number + 3, page_obj.paginator.num_pages) + 1)
    links = '&nbsp;&nbsp;'.join(make_link(n, page_obj.number) for n in pages)

    if pages[0] != 1:
        links = '&hellip;&nbsp;' + links
    if pages[-1] != page_obj.paginator.num_pages:
        links += '&nbsp;&hellip;'

    return links

@register.simple_tag
def page_links(page_obj, order=None, field=None, per_page=None):
    """Page links for list displays"""
    return page_links_common(page_obj, {'order': order, 'field': field, 'per_page': per_page})

@register.simple_tag
def search_page_links(page_obj, query=None):
    """Page links for list displays"""
    return page_links_common(page_obj, {'q': query})

@register.filter
@stringfilter
def company_title(companies):
    """Format possibly multiple companies for the title"""
    if '\n' in companies:
        return companies.split('\n')[0] + ', et al'
    else:
        return companies

@register.filter
def foia_is_viewable(foia, user):
    """Make sure the FOIA is viewable before showing it to the user"""
    return foia.is_viewable(user)

class TableHeaderNode(Node):
    """Tag to create table headers"""

    def __init__(self, get, args):
        # pylint: disable=W0231
        self.get = get
        self.args = args

    def render(self, context):
        """Render the table headers"""

        get = self.get.resolve(context, True)

        def get_args(*args):
            """Append get args to url if they are present"""
            return ''.join('&amp;%s=%s' % (arg, get[arg]) for arg in args if arg in get)

        html = ''
        for width, field in self.args:
            field = field.resolve(context, True)
            html += '<th width="%s%%">' % width
            if field:
                if get.get('field') == field and get.get('order') == 'asc':
                    order = 'desc'
                    img = '&nbsp;<img src="%simg/down-arrow.png" />' % STATIC_URL
                elif get.get('field') == field and get.get('order') == 'desc':
                    order = 'asc'
                    img = '&nbsp;<img src="%simg/up-arrow.png" />' % STATIC_URL
                else:
                    order = 'asc'
                    img = ''
                html += '<a href="?order=%s&amp;field=%s%s">%s%s</a>' % \
                        (order, field, get_args('page', 'per_page'), field.capitalize(), img)
            html += '</th>'
        return html

@register.tag
def table_header(parser, token):
    """Tag to create table headers"""

    get = token.split_contents()[1]
    bits = token.split_contents()[2:]
    if len(bits) % 2 != 0:
        raise TemplateSyntaxError("'table_header' statement requires matching number "
                                  "of width and fields")
    bits = zip(*[bits[i::2] for i in range(2)])
    return TableHeaderNode(parser.compile_filter(get),
                           [(a, parser.compile_filter(b)) for a, b in bits])

@register.filter(name='abs')
def abs_filter(value):
    """Absolute value of a number"""
    return abs(value)
