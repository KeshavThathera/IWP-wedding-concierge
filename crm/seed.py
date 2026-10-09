from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import transaction
from django.utils import timezone

from concierge.engine import Department

from .models import Conversation, Lead, Message

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@iwp.local"
DEMO_PASSWORD = "demo123"  # shown on the login page

C, P, S = Conversation, Conversation.Priority, Conversation.Status

# (ticket, customer, department, status, priority, summary, minutes ago, [(role, text), ...])
CONVERSATIONS = [
    (
        "IWP-1037",
        "Aanya Mehra",
        Department.WEDDING_SALES,
        S.OPEN,
        P.HIGH,
        "December Jaipur wedding for 250 guests; ₹1.5-2 Cr budget; palace venue preferred.",
        4,
        [
            ("visitor", "We are planning a Jaipur wedding for 250 guests in December."),
            ("assistant", "Wonderful. Do you have a working budget range?"),
            ("visitor", "Around ₹1.5-2 Cr, and we love palace venues."),
        ],
    ),
    (
        "IWP-1036",
        "Rohan & Mira",
        Department.WEDDING_SALES,
        S.WAITING,
        P.MEDIUM,
        "Exploring a 180-guest beach wedding in Goa; date flexible in February.",
        18,
        [
            ("visitor", "Could you share ideas for a Goa beach wedding?"),
            ("assistant", "Absolutely. About how many guests are you expecting?"),
            ("visitor", "Around 180, likely in February."),
        ],
    ),
    (
        "IWP-1034",
        "Kabir Sethi",
        Department.WEDDING_SALES,
        S.OPEN,
        P.MEDIUM,
        "Udaipur celebration for 90 guests; intimate lakeside venue; November 2027.",
        36,
        [
            ("visitor", "We want Udaipur, intimate and elegant, for about 90 guests."),
            ("assistant", "A lakeside celebration could be beautiful. When are you planning it?"),
            ("visitor", "November 2027."),
        ],
    ),
    (
        "IWP-1032",
        "Nisha Kapoor",
        Department.HR_CAREERS,
        S.OPEN,
        P.LOW,
        "Event producer with four years' experience asking about career opportunities.",
        60,
        [
            ("visitor", "I would like to apply for a role in wedding production."),
            ("assistant", "I've routed your enquiry to HR and Careers. Please share your preferred contact email."),
        ],
    ),
    (
        "IWP-1029",
        "Arjun Rao",
        Department.HR_CAREERS,
        S.RESOLVED,
        P.LOW,
        "Hospitality student enquiring about summer internships.",
        180,
        [
            ("visitor", "Is there an internship program for hospitality students?"),
            ("assistant", "I can prepare this for our HR and Careers team."),
        ],
    ),
    (
        "IWP-1027",
        "Studio Northstar",
        Department.VENDORS,
        S.WAITING,
        P.MEDIUM,
        "Fictional wedding photography studio proposing a vendor collaboration.",
        60 * 26,
        [
            ("visitor", "I'm a photographer and we would love to collaborate."),
            ("assistant", "Thank you. I'll route your portfolio enquiry to Vendors and Partnerships."),
        ],
    ),
    (
        "IWP-1025",
        "Devika Shah",
        Department.CLIENT_SERVICING,
        S.OPEN,
        P.HIGH,
        "Existing client needs urgent assistance with a guest airport transfer.",
        60 * 28,
        [
            ("visitor", "I'm already a client and need urgent help with tomorrow's airport transfer."),
            ("assistant", "I'm prioritising this for Client Servicing now."),
        ],
    ),
    (
        "IWP-1021",
        "Vivan Malhotra",
        Department.FINANCE,
        S.WAITING,
        P.MEDIUM,
        "Existing enquiry requesting a copy of a demo invoice.",
        60 * 50,
        [("visitor", "I need an invoice copy, please."), ("assistant", "I've routed this to Finance for follow-up.")],
    ),
]

L = Lead.Stage
# (name, contact, destination, guests, budget, date, style, method, stage, score, days ago)
LEADS = [
    ("Aanya Mehra", "aanya@example.com", "Jaipur", 250, "₹1.5-2 Cr", "December 2027", "Heritage palace", "WhatsApp", L.QUALIFIED, 92, 0),
    ("Rohan & Mira", "+91 90000 01002", "Goa", 180, "₹80L-1.2 Cr", "February 2028", "Beach resort", "Phone", L.NEW, 78, 0),
    ("Kabir Sethi", "kabir@example.com", "Udaipur", 90, "₹50-80L", "November 2027", "Lakeside", "Email", L.CONTACTED, 84, 1),
    ("Tara Anand", "tara@example.com", "Jodhpur", 320, "₹2 Cr+", "January 2028", "Fort", "WhatsApp", L.CONSULTATION, 96, 3),
    ("Neil Batra", "+91 90000 01005", "Kerala", 140, "₹80L-1.2 Cr", "March 2028", "Backwater resort", "Phone", L.PROPOSAL, 88, 5),
    ("Ira & Veer", "ira.veer@example.com", "Udaipur", 120, "₹1.2-1.5 Cr", "October 2027", "Palace", "Email", L.CONVERTED, 98, 8),
]


def ensure_demo_user():
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=DEMO_USERNAME, defaults={"email": DEMO_EMAIL})
    user.email, user.first_name, user.last_name = DEMO_EMAIL, "Demo", "Manager"
    user.is_staff = True
    user.set_password(DEMO_PASSWORD)
    user.save()
    user.user_permissions.set(Permission.objects.filter(content_type__app_label="crm"))
    return user


@transaction.atomic
def seed_demo() -> None:
    Lead.objects.all().delete()
    Conversation.objects.all().delete()
    ensure_demo_user()
    now = timezone.now()
    for ticket, customer, department, status, priority, summary, minutes, messages in CONVERSATIONS:
        updated = now - timedelta(minutes=minutes)
        conversation = Conversation.objects.create(
            ticket=ticket,
            customer=customer,
            department=department,
            status=status,
            priority=priority,
            summary=summary,
            created_at=updated - timedelta(minutes=6),
            updated_at=updated,
        )
        for i, (role, text) in enumerate(messages):
            Message.objects.create(
                conversation=conversation, role=role, text=text, created_at=updated - timedelta(minutes=len(messages) - i)
            )
    for name, contact, destination, guests, budget, date, style, method, stage, score, days in LEADS:
        Lead.objects.create(
            name=name,
            contact=contact,
            destination=destination,
            guests=guests,
            budget=budget,
            event_date=date,
            venue_style=style,
            contact_method=method,
            stage=stage,
            score=score,
            conversation=Conversation.objects.filter(customer=name).first(),
            created_at=now - timedelta(days=days),
        )
