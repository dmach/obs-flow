from django import template

register = template.Library()


@register.simple_tag
def pr_url(pr, route):
    return pr.url_for(route)
