"""
Seed a curated demo scenario with 8 realistic educators who form compelling
match pairs. Run after ingest_nces and migrations.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --clear   (wipe previous demo users first)
"""
import uuid
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from allauth.account.models import EmailAddress
from apps.districts.models import District
from apps.matching.models import (
    Connection,
    ProblemStatement,
    UserProblemSelection,
)
from apps.messaging.models import Conversation, ConversationParticipant, Message
from apps.users.models import FerpaConsent, User

DOMAIN = "tributary-test.org"
PASSWORD = "TributaryDemo1!"

# Curated educators — each pair shares problems and district context
DEMO_USERS = [
    {
        "email": "maria.gutierrez@tributary-test.org",
        "first_name": "Maria",
        "last_name": "Gutierrez",
        "role": "MEMBER",
        "bio": "K-5 literacy coach in rural New Mexico. 9 years helping teachers transition to structured literacy. Passionate about serving multilingual learners in high-poverty districts — our kids deserve the same evidence-based instruction as anyone.",
        "district_search": "Taos",
        "district_state": "NM",
        "problems": [
            "Supporting multilingual learners (ELL/ESL) in literacy acquisition",
            "Teacher training and PD — moving staff to structured literacy",
            "Family and community engagement in at-home literacy practices",
        ],
    },
    {
        "email": "sara.begay@tributary-test.org",
        "first_name": "Sara",
        "last_name": "Begay",
        "role": "MEMBER",
        "bio": "Literacy director at Window Rock Unified on the Navajo Nation. Building our first structured literacy initiative from the ground up. Our ELL population is 55% and we need peers who understand what that means for phonics instruction.",
        "district_search": "Window Rock",
        "district_state": "AZ",
        "problems": [
            "Supporting multilingual learners (ELL/ESL) in literacy acquisition",
            "Family and community engagement in at-home literacy practices",
            "Curriculum adoption and implementation fidelity",
        ],
    },
    {
        "email": "david.oconnor@tributary-test.org",
        "first_name": "David",
        "last_name": "O'Connor",
        "role": "MEMBER",
        "bio": "Reading specialist in rural Oklahoma. 12 years in Title I schools. We just adopted UFLI Foundations and I'm coaching 14 teachers through the transition. Looking for anyone who's been through this shift.",
        "district_search": "McAlester",
        "district_state": "OK",
        "problems": [
            "Teacher training and PD — moving staff to structured literacy",
            "Phonics and decodable text — moving away from leveled readers",
            "Building a sustainable literacy coaching model at scale",
        ],
    },
    {
        "email": "tameka.washington@tributary-test.org",
        "first_name": "Tameka",
        "last_name": "Washington",
        "role": "MEMBER",
        "bio": "District curriculum coordinator in rural Mississippi. Leading our county's first science-of-reading mandate. 78% FRL, limited PD budget — need to find coaches who've done this without a big consultancy contract.",
        "district_search": "Yazoo",
        "district_state": "MS",
        "problems": [
            "Teacher training and PD — moving staff to structured literacy",
            "Funding and resource allocation — making the internal case",
            "Phonics and decodable text — moving away from leveled readers",
        ],
    },
    {
        "email": "jennifer.chen@tributary-test.org",
        "first_name": "Jennifer",
        "last_name": "Chen",
        "role": "MEMBER",
        "bio": "K-2 dyslexia specialist in suburban Denver. Trained in Orton-Gillingham and Wilson Reading. Building early identification protocols for our 12,000-student district. Screening tool selection has been our biggest debate.",
        "district_search": "Cherry Creek",
        "district_state": "CO",
        "problems": [
            "Dyslexia identification and evidence-based support protocols",
            "Screening tool selection — DIBELS, mCLASS, iReady, etc.",
            "Early identification of struggling readers — screening and tiering",
        ],
    },
    {
        "email": "marcus.powell@tributary-test.org",
        "first_name": "Marcus",
        "last_name": "Powell",
        "role": "MEMBER",
        "bio": "School psychologist and reading intervention lead in suburban Atlanta. We're piloting MTSS for reading across 9 elementary schools. Trying to get the screening-to-intervention pipeline right before we scale district-wide.",
        "district_search": "DeKalb",
        "district_state": "GA",
        "problems": [
            "Early identification of struggling readers — screening and tiering",
            "Screening tool selection — DIBELS, mCLASS, iReady, etc.",
            "Dyslexia identification and evidence-based support protocols",
        ],
    },
    {
        "email": "rachel.hoffman@tributary-test.org",
        "first_name": "Rachel",
        "last_name": "Hoffman",
        "role": "MEMBER",
        "bio": "5th grade ELA teacher in small-town Vermont. My students come in reading at a 2nd grade level and I have 180 days to close the gap. I need strategies for the 3-4 transition that actually work in a one-teacher classroom.",
        "district_search": "Rutland",
        "district_state": "VT",
        "problems": [
            "The Grade 3-4 transition — learning-to-read to reading-to-learn",
            "Progress monitoring and data literacy — data-driven instruction",
            "Chronic absenteeism and its impact on reading development",
        ],
    },
    {
        "email": "brian.torres@tributary-test.org",
        "first_name": "Brian",
        "last_name": "Torres",
        "role": "MEMBER",
        "bio": "Middle school reading intervention teacher in rural Maine. Half my 6th graders can't decode multisyllabic words. Building a bridge program between elementary phonics and content-area reading. Absenteeism makes everything harder.",
        "district_search": "Lewiston",
        "district_state": "ME",
        "problems": [
            "The Grade 3-4 transition — learning-to-read to reading-to-learn",
            "Chronic absenteeism and its impact on reading development",
            "Supporting students with IEPs in general literacy instruction",
        ],
    },
]

# Pairs that should have accepted connections with messages
DEMO_CONVERSATIONS = [
    {
        "users": ("maria.gutierrez@tributary-test.org", "sara.begay@tributary-test.org"),
        "intro": "Your district sounds a lot like ours. Would love to compare notes on ELL phonics.",
        "messages": [
            ("maria.gutierrez@tributary-test.org", "Hi Sara! I saw we're both working with high ELL populations in rural districts. How are you handling the phonics instruction with students whose L1 doesn't share English phonemes?"),
            ("sara.begay@tributary-test.org", "That's exactly our challenge. Navajo has very different sound patterns. We've been adapting Heggerty for our population — adding a contrastive analysis component. It's early but teachers are seeing results."),
            ("maria.gutierrez@tributary-test.org", "We're doing something similar with Spanish speakers! The transfer skills are different but the approach is the same. Can I share our adaptation guide with you?"),
            ("sara.begay@tributary-test.org", "Please do! And I'll send you our family engagement materials — we translated everything into Navajo and it made a huge difference in parent participation."),
        ],
    },
    {
        "users": ("david.oconnor@tributary-test.org", "tameka.washington@tributary-test.org"),
        "intro": "Saw you're also doing the structured literacy transition in a rural Title I district. We should talk.",
        "messages": [
            ("david.oconnor@tributary-test.org", "Hey Tameka — how far along are you in the transition? We're in year 2 with UFLI and I've learned a lot about what NOT to do."),
            ("tameka.washington@tributary-test.org", "We're just starting. Honestly the budget is my biggest worry. How did you fund the materials and training?"),
            ("david.oconnor@tributary-test.org", "Title II funds covered most of the PD. For materials, we started with the free UFLI resources and only bought the full kit for grades K-2. Phased the rest in year 2."),
            ("tameka.washington@tributary-test.org", "That's really helpful. Our board keeps asking for ROI data. Do you track any metrics that convinced your leadership?"),
            ("david.oconnor@tributary-test.org", "DIBELS composite scores — that's what sold our superintendent. We went from 38% at benchmark to 54% in one year. I can send you our board presentation if you want."),
        ],
    },
    {
        "users": ("jennifer.chen@tributary-test.org", "marcus.powell@tributary-test.org"),
        "intro": "I see you're working on screening-to-intervention pipelines. That's exactly where we are. Let's connect.",
        "messages": [
            ("jennifer.chen@tributary-test.org", "Marcus, which screening tool did you end up going with? We've been going back and forth between DIBELS 8th and Acadience for months."),
            ("marcus.powell@tributary-test.org", "We went with DIBELS 8th Edition. The benchmarks are more current and the data integrates with our SIS. But honestly, the tool matters less than what you do with the data."),
            ("jennifer.chen@tributary-test.org", "That's what I keep telling our team! We have teachers who screen but then don't change their instruction based on the results."),
            ("marcus.powell@tributary-test.org", "Same problem here. We built a simple decision tree — if a kid scores X, they go to tier Y with Z intervention. Took the guesswork out. Happy to share our protocol."),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed a curated demo scenario with 8 educators and realistic conversations."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear previous demo users first")

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = User.objects.filter(email__endswith=f"@{DOMAIN}").delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} objects from @{DOMAIN}"))

        hashed_pw = make_password(PASSWORD)
        now = timezone.now()
        problem_map = {p.title: p for p in ProblemStatement.objects.filter(is_active=True)}

        created_users = {}

        for u in DEMO_USERS:
            # Skip if already exists
            if User.objects.filter(email=u["email"]).exists():
                created_users[u["email"]] = User.objects.get(email=u["email"])
                self.stdout.write(f"  Skipping {u['email']} (already exists)")
                continue

            # Find district
            district = District.objects.filter(
                name__icontains=u["district_search"],
                state=u["district_state"],
            ).first()
            if not district:
                self.stdout.write(self.style.WARNING(
                    f"  District not found: {u['district_search']}, {u['district_state']} — skipping user"
                ))
                continue

            user = User.objects.create(
                id=uuid.uuid4(),
                email=u["email"],
                password=hashed_pw,
                first_name=u["first_name"],
                last_name=u["last_name"],
                role=u["role"],
                is_active=True,
                bio=u["bio"],
                district=district,
                date_joined=now - timedelta(days=14),
            )
            created_users[u["email"]] = user

            # Email verification
            EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)

            # FERPA consent
            FerpaConsent.objects.create(user=user, ip_address="127.0.0.1", consent_text_version="1.0")

            # Problem selections
            for title in u["problems"]:
                ps = problem_map.get(title)
                if ps:
                    UserProblemSelection.objects.create(user=user, problem_statement=ps)

            self.stdout.write(self.style.SUCCESS(f"  Created {user.first_name} {user.last_name} ({district.name}, {district.state})"))

        # Create conversations
        for convo_data in DEMO_CONVERSATIONS:
            email_a, email_b = convo_data["users"]
            user_a = created_users.get(email_a)
            user_b = created_users.get(email_b)
            if not user_a or not user_b:
                continue

            # Connection
            if not Connection.objects.filter(requester=user_a, recipient=user_b).exists() and \
               not Connection.objects.filter(requester=user_b, recipient=user_a).exists():
                Connection.objects.create(
                    requester=user_a,
                    recipient=user_b,
                    status=Connection.ACCEPTED,
                    intro_message=convo_data["intro"],
                )

            # Conversation
            convo = Conversation.objects.create(id=uuid.uuid4())
            ConversationParticipant.objects.create(conversation=convo, user=user_a)
            ConversationParticipant.objects.create(conversation=convo, user=user_b)

            for i, (sender_email, body) in enumerate(convo_data["messages"]):
                sender = created_users[sender_email]
                Message.objects.create(
                    conversation=convo,
                    sender=sender,
                    body=body,
                    sent_at=now - timedelta(hours=len(convo_data["messages"]) - i),
                )

            self.stdout.write(self.style.SUCCESS(
                f"  Conversation: {user_a.first_name} <-> {user_b.first_name} ({len(convo_data['messages'])} messages)"
            ))

        # Compute match scores
        self.stdout.write("  Computing match scores...")
        from apps.matching.tasks import compute_all_match_scores
        compute_all_match_scores()

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("DEMO SEED COMPLETE"))
        self.stdout.write(f"  Password: {PASSWORD}")
        self.stdout.write(f"  Users:    {len(created_users)}")
        self.stdout.write("")
        self.stdout.write("  DEMO ACCOUNTS:")
        self.stdout.write("  " + "-" * 50)
        for u in DEMO_USERS:
            self.stdout.write(f"    {u['email']}")
        self.stdout.write("  " + "-" * 50)
        self.stdout.write("")
        self.stdout.write("  MATCH PAIRS (high scores):")
        self.stdout.write("    Maria & Sara — rural, high-ELL, multilingual literacy")
        self.stdout.write("    David & Tameka — rural Title I, structured literacy transition")
        self.stdout.write("    Jennifer & Marcus — suburban, screening/dyslexia pipeline")
        self.stdout.write("    Rachel & Brian — small-town, upper elementary reading gap")
        self.stdout.write("=" * 50)
