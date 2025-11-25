from django.urls import path
from . import views

urlpatterns = [
    path('', views.celebrity_list, name='celebrity_list'),
    path('add/', views.add_celebrity, name='add_celebrity'),
    path('celebrity/<int:celeb_id>/', views.celebrity_detail, name='celebrity_detail'),
    path('celebrity/edit/<int:celebrity_id>/', views.celebrity_edit, name='celebrity_edit'),
    path('celebrity/delete/<int:celebrity_id>/', views.celebrity_delete, name='celebrity_delete'),
    path('activities/', views.activity_list, name='activity_list'),
    path('activities/search/', views.search_activities, name='search_activities'),
    path('activities/delete/<int:activity_id>/', views.delete_activity, name='delete_activity'),
    path('activities/edit/<int:activity_id>/', views.activity_edit, name='edit_activity'),
    path('check-celebrity/', views.check_celebrity_exists, name='check_celebrity_exists'),
    path('sighting/edit/<int:sighting_id>/', views.edit_celebrity_sighting, name='edit_celebrity_sighting'),
    path('sighting/delete/<int:sighting_id>/', views.delete_celebrity_sighting, name='delete_celebrity_sighting'),
    path("celebrity/<int:celebrity_id>/update_popularity/", views.update_popularity, name="update_popularity"),
    path("update_popularity_step/", views.update_popularity_step, name="update_popularity_step"),
    path('api/all-celeb-ids/', views.all_celeb_ids, name='all_celeb_ids')


]
