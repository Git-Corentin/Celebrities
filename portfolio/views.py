# portfolio/views.py
from django.views.generic import ListView, DetailView
from .models import Project, Category

class ProjectListView(ListView):
    model = Project
    template_name = "portfolio/project_list.html"
    context_object_name = "projects"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Récupérer toutes les catégories avec leurs projets
        context['categories'] = Category.objects.prefetch_related('projects').all()
        return context
class ProjectDetailView(DetailView):
    model = Project
    template_name = "portfolio/project_detail.html"