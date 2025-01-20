from django.contrib import admin
from django.urls import path
from users import views

urlpatterns = [
    path('', views.index, name='home'),  # Homepage
    path('admin/', admin.site.urls),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('change-password/', views.change_password, name='change_password'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),
    path('add-client/', views.add_client, name='add_client'),
    path('client-list/', views.client_list, name='client_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout, name='logout'),
]

