from django.db import migrations


PROBLEM_STATEMENTS = [
    {
        "title": "Curriculum adoption and implementation fidelity",
        "description": "Ensuring consistent and faithful implementation of adopted literacy curricula across schools and classrooms, including alignment with structured literacy principles.",
        "category": "Curriculum",
    },
    {
        "title": "Teacher training and PD — moving staff to structured literacy",
        "description": "Designing and delivering professional development that transitions teaching staff from balanced literacy or other approaches to evidence-based structured literacy instruction.",
        "category": "Instruction",
    },
    {
        "title": "Early identification of struggling readers — screening and tiering",
        "description": "Implementing universal screening protocols to identify students at risk for reading difficulties and placing them in appropriate intervention tiers.",
        "category": "Assessment",
    },
    {
        "title": "Dyslexia identification and evidence-based support protocols",
        "description": "Establishing processes for identifying students with dyslexia and providing evidence-based interventions and accommodations.",
        "category": "Special Populations",
    },
    {
        "title": "Supporting multilingual learners (ELL/ESL) in literacy acquisition",
        "description": "Developing effective literacy instruction strategies for English language learners that build on their linguistic assets while developing English proficiency.",
        "category": "Special Populations",
    },
    {
        "title": "The Grade 3-4 transition — learning-to-read to reading-to-learn",
        "description": "Addressing the critical shift from decoding-focused instruction to comprehension-focused instruction as students move from primary to intermediate grades.",
        "category": "Instruction",
    },
    {
        "title": "Phonics and decodable text — moving away from leveled readers",
        "description": "Transitioning from leveled reader systems to decodable text and systematic phonics instruction aligned with the science of reading.",
        "category": "Curriculum",
    },
    {
        "title": "Family and community engagement in at-home literacy practices",
        "description": "Building partnerships with families and communities to support literacy development outside of school through effective communication and resources.",
        "category": "Family Engagement",
    },
    {
        "title": "Funding and resource allocation — making the internal case",
        "description": "Building the case for literacy investment, securing funding, and strategically allocating resources for maximum impact on student reading outcomes.",
        "category": "Operations",
    },
    {
        "title": "Progress monitoring and data literacy — data-driven instruction",
        "description": "Using assessment data effectively to monitor student progress, inform instructional decisions, and ensure accountability at all levels.",
        "category": "Assessment",
    },
    {
        "title": "Leadership alignment on structured literacy approach",
        "description": "Building consensus among district and school leaders on the importance of structured literacy and maintaining alignment through leadership transitions.",
        "category": "Leadership",
    },
    {
        "title": "Screening tool selection — DIBELS, mCLASS, iReady, etc.",
        "description": "Evaluating and selecting appropriate screening and assessment tools that provide actionable data for literacy instruction and intervention.",
        "category": "Assessment",
    },
    {
        "title": "Chronic absenteeism and its impact on reading development",
        "description": "Addressing the relationship between chronic absenteeism and reading achievement, and developing strategies to mitigate lost instructional time.",
        "category": "Student Wellbeing",
    },
    {
        "title": "Supporting students with IEPs in general literacy instruction",
        "description": "Ensuring students with Individualized Education Programs receive effective literacy instruction in both general education and specialized settings.",
        "category": "Special Populations",
    },
    {
        "title": "Building a sustainable literacy coaching model at scale",
        "description": "Developing and sustaining an instructional coaching model that supports teachers in implementing evidence-based literacy practices across the district.",
        "category": "Instruction",
    },
]


def seed_problems(apps, schema_editor):
    ProblemStatement = apps.get_model("matching", "ProblemStatement")
    for ps in PROBLEM_STATEMENTS:
        ProblemStatement.objects.create(
            title=ps["title"],
            description=ps["description"],
            category=ps["category"],
            is_active=True,
            version=1,
        )


def unseed_problems(apps, schema_editor):
    ProblemStatement = apps.get_model("matching", "ProblemStatement")
    ProblemStatement.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("matching", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_problems, unseed_problems),
    ]
