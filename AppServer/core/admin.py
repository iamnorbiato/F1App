# G:\Learning\3Tier_F1App\AppServer\core\admin.py

from django.contrib import admin
from .models import Circuit, Race, Constructors, Seasons, ConstructorStandings, Drivers, DriverStandings, Result, SprintResult, Qualifying, PitStop, LapTimes

# Registra o modelo Circuit
@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'location', 'circuitRef', 'url')
    search_fields = ('name', 'country', 'circuitRef')
    ordering = ('name',)

# Registra o modelo Race
@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'round', 'circuitid', 'date', 'time')
    search_fields = ('name', 'year', 'round')
    list_filter = ('year', 'circuitid') # Pode filtrar por ano e circuito
    ordering = ('-year', '-round')

# Registra o modelo Constructors
@admin.register(Constructors)
class ConstructorsAdmin(admin.ModelAdmin):
    list_display = ('name', 'nationality', 'constructorref', 'url')
    search_fields = ('name', 'nationality', 'constructorref')
    ordering = ('name',)

# Registra o modelo Seasons
@admin.register(Seasons)
class SeasonsAdmin(admin.ModelAdmin):
    list_display = ('year', 'url')
    search_fields = ('year',)
    ordering = ('-year',)

# Registra o modelo ConstructorStandings
@admin.register(ConstructorStandings)
class ConstructorStandingsAdmin(admin.ModelAdmin):
    list_display = ('raceid', 'constructorid', 'points', 'position', 'wins')
    search_fields = ('raceid', 'constructorid')
    list_filter = ('raceid',) # Pode filtrar por corrida
    ordering = ('raceid', 'position')

@admin.register(Drivers)
class DriversAdmin(admin.ModelAdmin):
    list_display = ('forename', 'surname', 'code', 'nationality', 'driverref')
    search_fields = ('forename', 'surname', 'code', 'driverref')
    ordering = ('surname', 'forename')

@admin.register(DriverStandings)
class DriverStandingsAdmin(admin.ModelAdmin):
    list_display = ('raceid', 'driverid', 'points', 'position', 'wins')
    search_fields = ('raceid', 'driverid')
    list_filter = ('raceid', 'driverid')
    ordering = ('raceid', '-position')

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('raceid', 'driverid', 'constructorid', 'position', 'points', 'statusid')
    search_fields = ('raceid__raceName', 'driverid__forename', 'driverid__surname', 'constructorid__name') # Exemplo com lookup se fosse FK
    list_filter = ('raceid', 'constructorid', 'statusid')
    ordering = ('raceid', 'positionorder')
    
@admin.register(SprintResult)
class SprintResultAdmin(admin.ModelAdmin):
    list_display = ('raceid', 'driverid', 'position', 'points', 'statusid')
    search_fields = ('raceid__raceName', 'driverid__forename', 'driverid__surname') # Estes funcionarão para campos relacionados em FK, mas como são IntegerField para IDs, a pesquisa será por ID
    list_filter = ('raceid', 'constructorid', 'statusid')
    ordering = ('raceid', 'positionorder')
    
@admin.register(Qualifying)
class QualifyingAdmin(admin.ModelAdmin):
    list_display = ('raceid', 'driverid', 'position', 'q1', 'q2', 'q3')
    search_fields = ('raceid__raceName', 'driverid__forename', 'driverid__surname')
    list_filter = ('raceid', 'constructorid')
    ordering = ('raceid', 'position')
 
@admin.register(PitStop)
class PitStopAdmin(admin.ModelAdmin):
    list_display = ('pit_stopid', 'raceid', 'driverid', 'stop', 'lap', 'duration', 'time')
    search_fields = ('pit_stopid', 'raceid', 'driverid', 'stop') # Pesquisar por IDs
    list_filter = ('raceid', 'driverid')
    ordering = ('raceid', 'lap', 'time')
       
@admin.register(LapTimes)
class LapTimesAdmin(admin.ModelAdmin):
    list_display = ('lap_timeid', 'raceid', 'driverid', 'lap', 'position', 'time', 'milliseconds')
    search_fields = ('raceid', 'driverid', 'lap') # Pesquisa por IDs
    list_filter = ('raceid', 'lap')
    ordering = ('raceid', 'lap', 'position')