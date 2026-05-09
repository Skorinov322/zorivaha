"""
Test URLs for error pages (development only).
"""

from django.http import Http404, HttpResponseForbidden, HttpResponseServerError
from django.shortcuts import render
from django.urls import path


def test_404(request):
    """Test 404 error page."""
    raise Http404("Тестовая страница 404")


def test_403(request):
    """Test 403 error page."""
    return render(request, '403.html', status=403)


def test_500(request):
    """Test 500 error page."""
    return render(request, '500.html', status=500)


# Test URLs (only for development)
urlpatterns = [
    path('test-404/', test_404, name='test_404'),
    path('test-403/', test_403, name='test_403'),
    path('test-500/', test_500, name='test_500'),
]