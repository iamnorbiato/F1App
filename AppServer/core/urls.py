# AppServer/core/urls.py
from django.urls import path
from . import views # Importa as views que acabamos de criar

urlpatterns = [
    # URL para a API simples de 'hello world'
    path('hello/', views.hello_world, name='hello_world'),
    # URL para a API de dados do gráfico de corrida animado
    path('animated_race_data/', views.animated_race_chart_data, name='animated_race_chart_data'),
]