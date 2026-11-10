from django.shortcuts import render, get_object_or_404
from services.models import ServiceCategory
from .models import CaseStudy


def _published():
    return CaseStudy.objects.filter(is_published=True).select_related("category")


def case_list(request):
    qs = _published()
    categories = ServiceCategory.objects.filter(casestudy__is_published=True).distinct()
    active = request.GET.get("category", "")
    total = qs.count()
    if active:
        qs = qs.filter(category__slug=active)
    return render(request, "portfolio/list.html", {
        "cases": qs, "categories": categories, "active": active, "total": total})


def case_detail(request, slug):
    c = get_object_or_404(_published(), slug=slug)
    ids = list(_published().values_list("pk", flat=True))
    i = ids.index(c.pk)
    prev_case = _published().filter(pk=ids[i - 1]).first() if i > 0 else None
    next_case = _published().filter(pk=ids[i + 1]).first() if i < len(ids) - 1 else None
    # Related: same category first, then fill with the most recent others.
    related = list(_published().filter(category=c.category).exclude(pk=c.pk)[:3]) if c.category_id else []
    if len(related) < 3:
        extra = _published().exclude(pk__in=[c.pk] + [r.pk for r in related])[: 3 - len(related)]
        related += list(extra)
    return render(request, "portfolio/detail.html", {
        "c": c, "related": related, "prev_case": prev_case, "next_case": next_case})
