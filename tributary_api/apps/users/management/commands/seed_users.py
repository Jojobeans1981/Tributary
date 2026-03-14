"""
Seed test users with realistic data for manual QA and demos.
Uses bulk_create for fast batch inserts instead of one-at-a-time.

Usage:
    python manage.py seed_users --count 20
    python manage.py seed_users --count 500 --domain testschool.org --password DemoPass123
    python manage.py seed_users --count 100 --connections --messages
"""
import random
import uuid
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from allauth.account.models import EmailAddress

from apps.districts.models import District
from apps.matching.models import (
    Connection,
    ProblemStatement,
    UserProblemSelection,
)
from apps.messaging.models import (
    Conversation,
    ConversationParticipant,
    Message,
)
from apps.users.models import FerpaConsent, User

FIRST_NAMES = [
    "Sarah", "Michael", "Jessica", "David", "Emily", "James", "Ashley",
    "Robert", "Amanda", "Christopher", "Stephanie", "Daniel", "Jennifer",
    "Matthew", "Nicole", "Andrew", "Elizabeth", "Joshua", "Megan", "Ryan",
    "Lauren", "Brandon", "Rachel", "Justin", "Samantha", "Tyler", "Heather",
    "Kevin", "Michelle", "Brian", "Tiffany", "Mark", "Christina", "Jason",
    "Amber", "Timothy", "Rebecca", "Nathan", "Laura", "Adam", "Kelly",
    "Patrick", "Maria", "Thomas", "Andrea", "Jonathan", "Kimberly",
    "Anthony", "Lisa", "Steven", "Angela", "Benjamin", "Karen", "Gregory",
    "Sandra", "Eric", "Susan", "Scott", "Catherine", "Travis", "Patricia",
]

LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Hernandez",
    "Moore", "Martin", "Jackson", "Thompson", "White", "Lopez", "Lee",
    "Gonzalez", "Harris", "Clark", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
    "Campbell", "Mitchell", "Carter", "Roberts", "Gomez", "Phillips",
    "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins",
    "Reyes", "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers",
]

BIOS = [
    "K-5 literacy coach focused on structured literacy implementation across our district.",
    "Reading specialist with 12 years of experience in Title I schools.",
    "District curriculum coordinator leading our phonics-first transition.",
    "Special education teacher passionate about evidence-based reading intervention.",
    "Elementary principal working to align our school's literacy approach with the science of reading.",
    "Instructional coach supporting teachers in implementing DIBELS progress monitoring.",
    "3rd grade teacher navigating the shift from balanced literacy to structured literacy.",
    "ELL coordinator developing phonics supports for multilingual learners.",
    "District assessment lead implementing universal screening for early reading difficulties.",
    "Literacy interventionist using Orton-Gillingham methods with struggling readers.",
    "Assistant superintendent overseeing our district's literacy strategic plan.",
    "2nd grade teacher building decodable text libraries for my classroom.",
    "Reading recovery teacher transitioning to a structured literacy framework.",
    "K-2 dyslexia specialist working on early identification protocols.",
    "Middle school reading teacher addressing the transition gap in grades 4-6.",
    "Family engagement coordinator developing at-home literacy programs.",
    "School psychologist focused on reading disability identification and support.",
    "Kindergarten teacher implementing explicit phonemic awareness instruction.",
    "District professional development lead training staff in structured literacy.",
    "5th grade ELA teacher integrating content-area reading with foundational skills.",
    "Curriculum director evaluating new structured literacy programs for adoption.",
    "Speech-language pathologist collaborating on phonological awareness instruction.",
    "Technology integration specialist supporting digital literacy tools.",
    "Title I coordinator managing reading intervention programs across 8 schools.",
    "1st grade teacher passionate about building strong decoding foundations.",
    "Bilingual education teacher developing Spanish-English transfer strategies.",
    "Data coach helping teachers use assessment data to drive reading instruction.",
    "High school reading specialist working with students who read below grade level.",
    "Library media specialist building a decodable and diverse text collection.",
    "Parent liaison developing family reading nights and literacy workshops.",
]

INTRO_MESSAGES = [
    "I'd love to connect and share strategies!",
    "We seem to be tackling similar challenges. Let's chat!",
    "Would love to hear about your district's approach.",
    "Great match score! Let's connect and collaborate.",
    "I think we could learn a lot from each other.",
    "Your bio resonated with me — facing the same issues here.",
    "Interested in comparing notes on our literacy initiatives.",
    "Hi! Would love to share resources and ideas.",
]

MESSAGE_BODIES = [
    "Hi! Thanks for connecting. How is your district handling the structured literacy transition?",
    "We just adopted a new phonics curriculum this year. Happy to share what we've learned so far.",
    "Do you have any recommendations for professional development resources?",
    "Our screening data from this fall was really eye-opening. Are you using DIBELS or something else?",
    "I'd love to hear about your coaching model. We're trying to build one from scratch.",
    "We're seeing great results with our tier 2 intervention — would love to tell you about it.",
    "What decodable text series is your district using? We're evaluating options.",
    "Have you found effective strategies for getting teacher buy-in on the new approach?",
    "Our family engagement numbers have been low. Any tips from your program?",
    "How are you handling the older students who missed foundational skills?",
    "Thanks for sharing that resource! I'll pass it along to my team.",
    "That's a great idea. We tried something similar and it worked well.",
    "Let me know when you're free for a longer conversation about this.",
    "I really appreciate the collaboration. This platform is exactly what I needed.",
]

BATCH_SIZE = 500


class Command(BaseCommand):
    help = "Seed test users with districts, selections, connections, and messages (bulk insert)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=20,
            help="Number of users to create (default: 20)",
        )
        parser.add_argument(
            "--domain", type=str, default="tributary-test.org",
            help="Email domain for all seeded users (default: tributary-test.org)",
        )
        parser.add_argument(
            "--password", type=str, default="TributaryDemo1!",
            help="Shared password for all seeded users (default: TributaryDemo1!)",
        )
        parser.add_argument(
            "--connections", action="store_true",
            help="Also create random connections between seeded users",
        )
        parser.add_argument(
            "--messages", action="store_true",
            help="Also create conversations and messages (implies --connections)",
        )
        parser.add_argument(
            "--compute-scores", action="store_true",
            help="Run match score computation after seeding",
        )
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete all previously seeded users from this domain before creating new ones",
        )

    def handle(self, *args, **options):
        count = options["count"]
        domain = options["domain"]
        password = options["password"]
        create_connections = options["connections"] or options["messages"]
        create_messages = options["messages"]
        compute_scores = options["compute_scores"]

        if options["clear"]:
            deleted, _ = User.objects.filter(email__endswith=f"@{domain}").delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} objects from @{domain}"))

        districts = list(District.objects.all())
        problems = list(ProblemStatement.objects.filter(is_active=True))

        if not districts:
            self.stdout.write(self.style.ERROR(
                "No districts in DB. Run 'python manage.py ingest_nces' first."
            ))
            return

        if not problems:
            self.stdout.write(self.style.ERROR("No active problem statements in DB."))
            return

        self.stdout.write(f"Seeding {count} users with @{domain} ...")

        # Hash password once — all users share it
        hashed_password = make_password(password)
        now = timezone.now()

        # Build unique emails
        used_emails = set(
            User.objects.filter(email__endswith=f"@{domain}")
            .values_list("email", flat=True)
        )

        # ---------- 1. Build User objects in memory ----------
        self.stdout.write("  Building user objects...")
        user_objects = []
        for _ in range(count):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            base = f"{first.lower()}.{last.lower()}"
            email = f"{base}@{domain}"
            suffix = 1
            while email in used_emails:
                email = f"{base}{suffix}@{domain}"
                suffix += 1
            used_emails.add(email)

            user_objects.append(User(
                id=uuid.uuid4(),
                email=email,
                password=hashed_password,
                first_name=first,
                last_name=last,
                role="MEMBER",
                is_active=True,
                bio=random.choice(BIOS),
                district=random.choice(districts),
                date_joined=now - timedelta(days=random.randint(1, 90)),
            ))

        # ---------- 2. Bulk insert users ----------
        self.stdout.write(f"  Inserting {count} users...")
        User.objects.bulk_create(user_objects, batch_size=BATCH_SIZE)
        self.stdout.write(self.style.SUCCESS(f"  {count} users inserted."))

        # ---------- 3. Bulk insert email verifications ----------
        self.stdout.write("  Creating email verifications...")
        email_objects = [
            EmailAddress(user=u, email=u.email, primary=True, verified=True)
            for u in user_objects
        ]
        EmailAddress.objects.bulk_create(email_objects, batch_size=BATCH_SIZE)

        # ---------- 4. Bulk insert FERPA consents ----------
        self.stdout.write("  Creating FERPA consents...")
        consent_objects = [
            FerpaConsent(user=u, ip_address="127.0.0.1", consent_text_version="1.0")
            for u in user_objects
        ]
        FerpaConsent.objects.bulk_create(consent_objects, batch_size=BATCH_SIZE)

        # ---------- 5. Bulk insert problem selections ----------
        self.stdout.write("  Creating problem selections...")
        selection_objects = []
        for u in user_objects:
            num_selections = random.choice([1, 2, 2, 3, 3])
            selected = random.sample(problems, min(num_selections, len(problems)))
            for ps in selected:
                selection_objects.append(
                    UserProblemSelection(user=u, problem_statement=ps)
                )
        UserProblemSelection.objects.bulk_create(selection_objects, batch_size=BATCH_SIZE)
        self.stdout.write(self.style.SUCCESS(f"  {len(selection_objects)} problem selections inserted."))

        # ---------- 6. Connections ----------
        if create_connections and len(user_objects) >= 2:
            self.stdout.write("  Creating connections...")
            num_connections = min(len(user_objects) * 2, len(user_objects) * (len(user_objects) - 1) // 2)
            pairs_created = set()
            conn_objects = []

            for _ in range(num_connections):
                a, b = random.sample(user_objects, 2)
                pair = tuple(sorted([str(a.id), str(b.id)]))
                if pair in pairs_created:
                    continue
                pairs_created.add(pair)

                status = random.choice([
                    Connection.ACCEPTED, Connection.ACCEPTED, Connection.ACCEPTED,
                    Connection.PENDING,
                ])
                conn_objects.append(Connection(
                    requester=a, recipient=b, status=status,
                    intro_message=random.choice(INTRO_MESSAGES) if random.random() > 0.3 else "",
                ))

            Connection.objects.bulk_create(conn_objects, batch_size=BATCH_SIZE)
            self.stdout.write(self.style.SUCCESS(f"  {len(conn_objects)} connections inserted."))

            # ---------- 7. Messages ----------
            if create_messages:
                self.stdout.write("  Creating conversations and messages...")
                accepted = [c for c in conn_objects if c.status == Connection.ACCEPTED]
                convos_created = 0
                msg_objects = []
                participant_objects = []

                for conn in accepted:
                    if random.random() > 0.6:
                        continue

                    convo = Conversation(id=uuid.uuid4())
                    participant_objects.append(
                        ConversationParticipant(conversation=convo, user=conn.requester)
                    )
                    participant_objects.append(
                        ConversationParticipant(conversation=convo, user=conn.recipient)
                    )
                    convos_created += 1

                    num_msgs = random.randint(2, 8)
                    for j in range(num_msgs):
                        sender = conn.requester if j % 2 == 0 else conn.recipient
                        msg_objects.append(Message(
                            conversation=convo,
                            sender=sender,
                            body=random.choice(MESSAGE_BODIES),
                        ))

                # Bulk insert conversations first (need PKs for participants/messages)
                convo_objects = list({p.conversation for p in participant_objects})
                Conversation.objects.bulk_create(convo_objects, batch_size=BATCH_SIZE)
                ConversationParticipant.objects.bulk_create(participant_objects, batch_size=BATCH_SIZE)
                Message.objects.bulk_create(msg_objects, batch_size=BATCH_SIZE)
                self.stdout.write(self.style.SUCCESS(
                    f"  {convos_created} conversations with {len(msg_objects)} messages inserted."
                ))

        # ---------- 8. Match scores ----------
        if compute_scores:
            self.stdout.write("Computing match scores (this may take a moment)...")
            from apps.matching.tasks import compute_all_match_scores
            compute_all_match_scores()
            self.stdout.write(self.style.SUCCESS("Match scores computed."))

        # ---------- Summary ----------
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("SEED COMPLETE"))
        self.stdout.write(f"  Domain:   @{domain}")
        self.stdout.write(f"  Password: {password}")
        self.stdout.write(f"  Users:    {count}")
        self.stdout.write(f"  Login as any user at /login")
        self.stdout.write("=" * 50)
