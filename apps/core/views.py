"""
Core views for error handling and other common functionality.
"""

from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError


def custom_404(request, exception=None):
    """
    Custom 404 error handler.
    
    Args:
        request: The HTTP request object
        exception: The exception that caused the 404 (optional)
    
    Returns:
        HttpResponseNotFound with custom 404 template
    """
    return render(
        request, 
        '404.html', 
        status=404,
        context={
            'request_path': request.path,
        }
    )


def custom_500(request):
    """
    Custom 500 error handler.
    
    Args:
        request: The HTTP request object
    
    Returns:
        HttpResponseServerError with custom 500 template
    """
    return render(
        request, 
        '500.html', 
        status=500,
        context={
            'request_path': request.path,
        }
    )


def custom_403(request, exception=None):
    """
    Custom 403 error handler.
    
    Args:
        request: The HTTP request object
        exception: The exception that caused the 403 (optional)
    
    Returns:
        HttpResponseForbidden with custom 403 template
    """
    return render(
        request, 
        '403.html', 
        status=403,
        context={
            'request_path': request.path,
        }
    )