from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.celebrity_list, name='celebrity_list'),
    path('add/', views.add_celebrity, name='add_celebrity'),
    path('celebrity/<int:celeb_id>/', views.celebrity_detail, name='celebrity_detail'),
    path('celebrity/<int:celeb_id>/sighting/', views.add_sighting, name='add_sighting'),
    path('celebrity/edit/<int:celebrity_id>/', views.celebrity_edit, name='celebrity_edit'),
    path('celebrity/delete/<int:celebrity_id>/', views.celebrity_delete, name='celebrity_delete'),
    path('celebrity/<int:celebrity_id>/update_popularity/', views.update_popularity, name='update_popularity'),

    path('sighting/edit/<int:sighting_id>/', views.edit_celebrity_sighting, name='edit_celebrity_sighting'),
    path('sighting/delete/<int:sighting_id>/', views.delete_celebrity_sighting, name='delete_celebrity_sighting'),

    path('activities/', views.activity_list, name='activity_list'),
    path('activities/search/', views.search_activities, name='search_activities'),
    path('activities/edit/<int:activity_id>/', views.activity_edit, name='edit_activity'),
    path('activities/delete/<int:activity_id>/', views.delete_activity, name='delete_activity'),
    path('activities/<int:activity_id>/category/', views.set_activity_category, name='set_activity_category'),

    path('check-celebrity/', views.check_celebrity_exists, name='check_celebrity_exists'),
    path('api/suggest/', views.suggest, name='suggest'),
    path('api/image-suggestions/', views.image_suggestions, name='image_suggestions'),
    path('api/popularity/batch/', views.update_popularity_batch, name='update_popularity_batch'),
    path('api/all-celeb-ids/', views.all_celeb_ids, name='all_celeb_ids'),
    path('sync/git/', views.git_sync_view, name='git_sync'),

    path('login/', auth_views.LoginView.as_view(template_name='celebs/login.html'), name='celebs_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='celebs_logout'),
]
