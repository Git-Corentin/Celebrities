

# Migrez les PDFs existants
from portfolio.models import Project, ProjectMedia

for project in Project.objects.filter(pdf_report__isnull=False):
    ProjectMedia.objects.create(
        project=project,
        media_type='pdf',
        file=project.pdf_report,
        caption="Rapport du projet",
        order=0
    )
    print(f"✓ Migré : {project.title}")