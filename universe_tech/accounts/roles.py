"""Least-privilege staff roles. Give each team member ONLY the group(s) they need (Admin > Users > Groups).
Superuser should be limited to one or two owners. Nobody gets 'delete' on legal/financial records."""
from django.contrib.auth.models import Group, Permission

V, A, C, D = "view", "add", "change", "delete"
FULL = (V, A, C, D)
EDIT = (V, A, C)            # no delete

ROLES = {
    "Sales": {
        "quotes": {"quoterequest": FULL, "leadnote": FULL, "quotation": EDIT, "quotationitem": EDIT},
        "proposals": {"proposal": EDIT, "proposalphase": FULL},
        "services": {"service": (V,), "servicecategory": (V,)},
        "contracts": {"contract": (V,)},
    },
    "Project Manager": {
        "projects": {"project": EDIT, "milestone": EDIT, "deliverable": FULL, "projectupdate": EDIT},
        "contracts": {"contract": EDIT},
        "proposals": {"proposal": (V,), "proposalphase": (V,)},
        "support": {"ticket": EDIT, "ticketmessage": EDIT},
        "billing": {"invoice": (V,), "invoiceitem": (V,)},
    },
    "Finance": {
        "billing": {"invoice": EDIT, "invoiceitem": FULL},
        "contracts": {"contract": (V,)},
        "projects": {"project": (V,), "milestone": (V,)},
        "proposals": {"proposal": (V,), "proposalphase": (V,)},
    },
    "Support": {
        "support": {"ticket": EDIT, "ticketmessage": EDIT},
        "projects": {"project": (V,), "milestone": (V,), "projectupdate": (V,)},
    },
    "Content Editor": {
        "services": {"service": EDIT, "servicecategory": EDIT},
        "portfolio": {"casestudy": EDIT},
        "trust": {"testimonial": EDIT, "clientlogo": EDIT, "faqitem": EDIT, "pricingpackage": EDIT},
    },
}


def sync_roles():
    """Create/refresh the groups. Safe to run repeatedly; silently skips permissions that do not exist yet."""
    try:
        for name, apps in ROLES.items():
            group, _ = Group.objects.get_or_create(name=name)
            wanted = []
            for app_label, models in apps.items():
                for model, actions in models.items():
                    for act in actions:
                        wanted.append(f"{act}_{model}|{app_label}")
            perms = []
            for w in wanted:
                code, app_label = w.split("|")
                p = Permission.objects.filter(codename=code, content_type__app_label=app_label).first()
                if p:
                    perms.append(p)
            group.permissions.set(perms)
    except Exception:       # e.g. tables not created yet during the very first migrate
        pass
