def unread(request):
    u = getattr(request, "user", None)
    if u and u.is_authenticated:
        return {"unread_count": u.notifications.filter(is_read=False).count()}
    return {}
