from modeltranslation.translator import translator, TranslationOptions
from .models import Category, Institution, Project, ProjectMedia


class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


class InstitutionTranslationOptions(TranslationOptions):
    fields = ('name',)


class ProjectTranslationOptions(TranslationOptions):
    fields = ('title', 'short_description', 'description', 'technologies')


class ProjectMediaTranslationOptions(TranslationOptions):
    fields = ('caption',)


translator.register(Category, CategoryTranslationOptions)
translator.register(Institution, InstitutionTranslationOptions)
translator.register(Project, ProjectTranslationOptions)
translator.register(ProjectMedia, ProjectMediaTranslationOptions)