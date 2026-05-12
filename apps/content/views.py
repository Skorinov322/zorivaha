"""
content/views.py

Public views for content pages.
"""

from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .models import FAQ, LegalPage


class FAQListView(ListView):
    """
    Display all active FAQs grouped by category.
    """
    model = FAQ
    template_name = "content/faq.html"
    context_object_name = "faqs"
    
    def get_queryset(self):
        """Return only active FAQs ordered by category and sort_order."""
        return FAQ.objects.filter(is_active=True).order_by("category", "sort_order")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Group FAQs by category
        faqs_by_category = {}
        for faq in context["faqs"]:
            category = faq.get_category_display()
            if category not in faqs_by_category:
                faqs_by_category[category] = []
            faqs_by_category[category].append(faq)
        
        context["faqs_by_category"] = faqs_by_category
        return context


def legal_page(request, page_type):
    """
    Render a legal page by its page_type.
    Allowed types: terms, privacy, accommodation.
    """
    valid_types = [choice[0] for choice in LegalPage.PageType.choices]
    if page_type not in valid_types:
        raise Http404("Страница не найдена")
    
    page = get_object_or_404(LegalPage, page_type=page_type, is_active=True)
    return render(request, "content/legal_page.html", {"page": page})
