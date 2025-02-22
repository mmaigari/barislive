from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

@register.filter(name='currency')
def currency(value):
    """Format amount with Naira symbol and thousand separators"""
    try:
        formatted = floatformat(value, 2)
        # Add thousand separators
        parts = str(formatted).split('.')
        parts[0] = "{:,}".format(int(parts[0]))
        formatted = '.'.join(parts)
        return f"₦{formatted}"
    except (ValueError, TypeError):
        return "₦0.00"