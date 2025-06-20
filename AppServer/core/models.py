# G:\Learning\3Tier_F1App\AppServer\core\models.py
from django.db import models

class Circuit(models.Model):
    circuitid = models.IntegerField(primary_key=True, null=False, blank=False)
    circuitRef = models.CharField(db_column='circuitref', max_length=50, unique=True, help_text="Unique circuit identifier from Ergast API (circuitId).")
    name = models.CharField(db_column='"name"', max_length=100) # Aumentado max_length para nomes maiores
    location = models.CharField(db_column='"location"', max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    alt = models.IntegerField(null=True, blank=True, help_text="Altitude in meters")
    url = models.URLField(max_length=255, null=True, blank=True) # Aumentado max_length para URLs

    def __str__(self):
        return f"{self.name} ({self.country})"

    class Meta:
        db_table = 'circuits' # Certifique-se que o schema e nome da tabela estão corretos
        managed = False
        verbose_name = "Circuito"
        verbose_name_plural = "Circuitos"
        ordering = ['name']

class Race(models.Model):
    raceid = models.IntegerField(primary_key=True, null=False, blank=False)
    year = models.IntegerField(db_column='"year"', null=False, blank=False)
    round = models.IntegerField(null=False, blank=False) # 'round' não está quotado no DDL, então o nome default deve funcionar
    circuitid = models.IntegerField(null=True, blank=True, help_text="ID do circuito da tabela de Circuitos no DB.")
    name = models.CharField(db_column='"name"', max_length=50)
    date = models.CharField(max_length=50)
    time = models.CharField(max_length=50)
    url = models.URLField(max_length=128, null=True, blank=True)
    fp1_date = models.CharField(max_length=50, null=True, blank=True)
    fp1_time = models.CharField(max_length=50, null=True, blank=True)
    fp2_date = models.CharField(max_length=50, null=True, blank=True)
    fp2_time = models.CharField(max_length=50, null=True, blank=True)
    fp3_date = models.CharField(max_length=50, null=True, blank=True)
    fp3_time = models.CharField(max_length=50, null=True, blank=True)
    quali_date = models.CharField(max_length=50, null=True, blank=True)
    quali_time = models.CharField(max_length=50, null=True, blank=True)
    sprint_date = models.CharField(max_length=50, null=True, blank=True)
    sprint_time = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'races'
        managed = False
        verbose_name = "Corrida"
        verbose_name_plural = "Corridas"
        unique_together = ('year', 'round')
        ordering = ['year', 'round']

    def __str__(self):
        return f"{self.name} {self.year} (Round {self.round})"
    
class Constructors(models.Model): # NOME DA CLASSE NO PLURAL, CONFORME SOLICITADO
    constructorid = models.IntegerField(primary_key=True)
    constructorref = models.CharField(db_column='constructorref', max_length=50, unique=True) # Nome da coluna no DB (lowercase)
    name = models.CharField(db_column='"name"', max_length=50)
    nationality = models.CharField(max_length=50, null=True, blank=True)
    url = models.URLField(max_length=128, null=True, blank=True)
    
    class Meta:
        db_table = 'constructors' # CORRIGIDO: Removido 'f1app_usr.'
        managed = False # Django não gerencia a tabela
        verbose_name = "Construtor"
        verbose_name_plural = "Construtores" # Mantido no plural aqui para a exibição
        ordering = ['name']

    def __str__(self):
        return self.name

    
class Status(models.Model): 
    statusid = models.IntegerField(primary_key=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        db_table = 'status'
        managed = False
        verbose_name = "Status"
        verbose_name_plural = "Status"
        ordering = ['status']

    def __str__(self):
        return self.name
    
class Seasons(models.Model): 
    year = models.IntegerField(primary_key=True, db_column='"year"')
    url  = models.URLField(max_length=128, null=False, blank=False)
    
    class Meta:
        db_table = 'seasons'
        managed = False
        verbose_name = "Temporada"
        verbose_name_plural = "Temporadas"
        ordering = ['year']

    def __str__(self):
        return str(self.year)
    
class ConstructorStandings(models.Model):
    constructorstandingsid = models.IntegerField(primary_key=True)

    raceid = models.IntegerField(null=False, blank=False)
    constructorid = models.IntegerField(null=False, blank=False)

    points = models.IntegerField(null=True, blank=True) # DDL é int4
    position = models.IntegerField(null=True, blank=True) # DDL é int4, JSON é string
    positiontext = models.CharField(db_column='positiontext', max_length=50, null=True, blank=True) # Mapeamento para nome do DB

    wins = models.IntegerField(null=True, blank=True) # DDL é int4

    class Meta:
        db_table = 'constructor_standings' # Assumindo schema padrão
        managed = False # Django não gerencia a tabela
        verbose_name = "Classificação de Construtores"
        verbose_name_plural = "Classificações de Construtores"
        unique_together = ('raceid', 'constructorid')
        ordering = ['-position'] # Ordenar por posição (decrescente ou crescente, conforme preferir)

    def __str__(self):
        return f"Construtor ID: {self.constructorid} - Corrida ID: {self.raceid} - Posição: {self.position}"
    
class Drivers(models.Model): 
    driverid = models.IntegerField(primary_key=True)
    driverref = models.CharField(db_column='driverref', max_length=50, unique=True, null=False, blank=False) # Garante NOT NULL e unicidade
    number = models.CharField(db_column='number', max_length=50, null=True, blank=True)
    code = models.CharField(max_length=50, null=True, blank=True)
    forename = models.CharField(db_column='forename', max_length=50, null=True, blank=True)
    surname = models.CharField(db_column='surname', max_length=50, null=True, blank=True)
    dob = models.CharField(max_length=50, null=True, blank=True)
    nationality = models.CharField(max_length=50, null=True, blank=True)
    url = models.URLField(max_length=200, null=True, blank=True) # Max_length de 200 conforme DDL

    class Meta:
        db_table = 'drivers' # Assumindo schema padrão
        managed = False # Django não gerencia a tabela
        verbose_name = "Piloto"
        verbose_name_plural = "Pilotos"
        ordering = ['surname', 'forename'] # Ordem padrão por sobrenome e nome

    def __str__(self):
        return f"{self.forename} {self.surname} ({self.code})"
    
class DriverStandings(models.Model):
    driverstandingsid = models.IntegerField(primary_key=True)
    raceid = models.IntegerField(null=False, blank=False)
    driverid = models.IntegerField(null=False, blank=False)
    points = models.IntegerField(null=True, blank=True) # DDL é int4
    position = models.IntegerField(null=True, blank=True) # DDL é int4, JSON é string
    positiontext = models.CharField(db_column='positiontext', max_length=50, null=True, blank=True)
    wins = models.IntegerField(null=True, blank=True) # DDL é int4

    class Meta:
        db_table = 'driver_standings' # Assumindo schema padrão
        managed = False # Django não gerencia a tabela
        verbose_name = "Classificação de Pilotos"
        verbose_name_plural = "Classificações de Pilotos"
        # Chave de unicidade para identificar um registro único que pode ser atualizado
        # A combinação raceid + driverid é única para uma entrada
        unique_together = ('raceid', 'driverid')
        ordering = ['raceid', 'position'] # Ordem padrão

    def __str__(self):
        return f"Piloto ID: {self.driverid} - Corrida ID: {self.raceid} - Posição: {self.position}"
    
class Result(models.Model): # Usando o nome singular 'Result'
    # PK gerenciada pelo Python
    resultid = models.IntegerField(primary_key=True)
    raceid = models.IntegerField(null=False, blank=False)
    driverid = models.IntegerField(null=False, blank=False)
    constructorid = models.IntegerField(null=False, blank=False)
    statusid = models.IntegerField(null=True, blank=True) # Pode ser null no DDL
    number = models.IntegerField(db_column='number', null=True, blank=True) # DDL é int4, 'number' entre aspas
    grid = models.IntegerField(null=True, blank=True) # DDL é int4
    positionorder = models.IntegerField(null=True, blank=True) # DDL é int4
    laps = models.IntegerField(null=True, blank=True) # DDL é int4
    points = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    position = models.CharField(db_column='position', max_length=50, null=True, blank=True) # DDL é varchar(50), 'position' entre aspas
    positiontext = models.CharField(db_column='positiontext', max_length=50, null=True, blank=True) # DDL é varchar(50)
    time = models.CharField(db_column='time', max_length=50, null=True, blank=True) # DDL é varchar(50), 'time' entre aspas
    milliseconds = models.CharField(null=True, blank=True, max_length=50) # DDL é varchar(50)
    fastestlap = models.CharField(null=True, blank=True, max_length=50) # DDL é varchar(50)
    rank = models.CharField(db_column='rank', max_length=50, null=True, blank=True) # DDL é varchar(50), 'rank' entre aspas
    fastestlaptime = models.CharField(null=True, blank=True, max_length=50) # DDL é varchar(50)
    fastestlapspeed = models.CharField(null=True, blank=True, max_length=50) # DDL é varchar(50)


    class Meta:
        db_table = 'results' # Assumindo schema padrão
        managed = False # Django não gerencia a tabela
        verbose_name = "Resultado"
        verbose_name_plural = "Resultados"
        # Chave de unicidade para identificar um registro único que pode ser atualizado
        # Conforme DDL: UNIQUE (raceid, driverid, constructorid, number)
        unique_together = ('raceid', 'driverid', 'constructorid', 'number')
        ordering = ['raceid', 'positionorder'] # Ordenar por corrida e ordem de posição

    def __str__(self):
        return f"Resultado Corrida ID: {self.raceid}, Piloto ID: {self.driverid}, Pos: {self.position}"

class SprintResult(models.Model): # Usando o nome singular 'SprintResult'
    # PK gerenciada pelo Python
    resultid = models.IntegerField(primary_key=True)
    raceid = models.IntegerField(null=False, blank=False)
    driverid = models.IntegerField(null=False, blank=False)
    constructorid = models.IntegerField(null=True, blank=True) # Pode ser nulo no DDL
    statusid = models.IntegerField(null=True, blank=True)      # Pode ser nulo no DDL
    number = models.IntegerField(db_column='number', null=True, blank=True) # DDL é int4, 'number' entre aspas
    grid = models.IntegerField(null=True, blank=True)    # DDL é int4
    positionorder = models.IntegerField(null=True, blank=True) # DDL é int4
    points = models.IntegerField(null=True, blank=True)  # DDL é int4
    laps = models.IntegerField(null=True, blank=True)    # DDL is int4
    position = models.CharField(db_column='position', max_length=50, null=True, blank=True)        # DDL é varchar(50), 'position' entre aspas
    positiontext = models.CharField(db_column='positiontext', max_length=50, null=True, blank=True) # DDL is varchar(50)
    time = models.CharField(db_column='time', max_length=50, null=True, blank=True)            # DDL is varchar(50), 'time' entre aspas
    milliseconds = models.CharField(max_length=50, null=True, blank=True)  # DDL is varchar(50)
    fastestlap = models.CharField(max_length=50, null=True, blank=True)      # DDL is varchar(50)
    rank = models.CharField(db_column='rank', max_length=50, null=True, blank=True)          # DDL is varchar(50), 'rank' entre aspas
    fastestlaptime = models.CharField(max_length=50, null=True, blank=True)  # DDL is varchar(50)

    class Meta:
        db_table = 'sprint_results' # Assumindo schema padrão
        managed = False # Django não gerencia a tabela
        verbose_name = "Resultado de Sprint"
        verbose_name_plural = "Resultados de Sprint"
        unique_together = ('raceid', 'driverid') # Conforme DDL
        ordering = ['raceid', 'positionorder']

    def __str__(self):
        return f"Resultado Sprint - Piloto ID: {self.driverid}, Corrida ID: {self.raceid}, Pos: {self.position}"
    
class Qualifying(models.Model): # Usando o nome singular 'Qualifying'
    # PK gerenciada pelo Python
    qualifyid = models.IntegerField(primary_key=True)

    # FKs para Race, Drivers, Constructors (como IntegerField)
    raceid = models.IntegerField(null=False, blank=False)
    driverid = models.IntegerField(null=False, blank=False)
    constructorid = models.IntegerField(null=True, blank=True) # Pode ser nulo no DDL

    # Campos numéricos
    number = models.IntegerField(db_column='number', null=True, blank=True) # DDL é int4, 'number' entre aspas
    # 'position' é int4 no DDL, mas string no JSON. Converteremos no script.
    position = models.IntegerField(db_column='position', null=True, blank=True) # DDL é int4, 'position' entre aspas

    # Tempos de qualificação (varchar)
    q1 = models.CharField(max_length=50, null=True, blank=True) # DDL é varchar(50)
    q2 = models.CharField(max_length=50, null=True, blank=True) # DDL é varchar(50)
    q3 = models.CharField(max_length=50, null=True, blank=True) # DDL é varchar(50)

    class Meta:
        db_table = 'qualifying' # Assumindo schema padrão
        managed = False # Django não gerencia a tabela
        verbose_name = "Classificação"
        verbose_name_plural = "Classificações"
        # Chave de unicidade para identificar um registro único
        unique_together = ('raceid', 'driverid') # Conforme DDL
        ordering = ['raceid', 'position'] # Ordenar por corrida e posição

    def __str__(self):
        return f"Qualifying - Corrida ID: {self.raceid}, Piloto ID: {self.driverid}, Pos: {self.position}"
    
class PitStop(models.Model):
    # pit_stopid é a chave primária INT4 NOT NULL
    pit_stopid = models.IntegerField(primary_key=True, null=False, blank=False)
    raceid = models.IntegerField(null=False, blank=False)
    driverid = models.IntegerField(null=False, blank=False)
    stop = models.IntegerField(null=False, blank=False)
    lap = models.IntegerField(null=True, blank=True)
    time = models.CharField(db_column='time', max_length=50, null=True, blank=True)
    # duration e milliseconds são VARCHAR no DB
    duration = models.CharField(max_length=50, null=True, blank=True)
    milliseconds = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'pit_stops'
        managed = False
        verbose_name = "Pit Stop"
        verbose_name_plural = "Pit Stops"
        unique_together = ('raceid', 'driverid', 'stop') # UNIQUE KEY composta
        ordering = ['raceid', 'lap', 'time']

    def __str__(self):
        return f"Pit Stop ID: {self.pit_stopid} - Corrida ID: {self.raceid}, Piloto ID: {self.driverid}, Parada: {self.stop}"
    
class LapTimes(models.Model): # Usando o nome plural 'LapTimes'
    # PK gerenciada pelo Python
    lap_timeid = models.IntegerField(primary_key=True, null=False, blank=False)

    # FKs para Race e Drivers (como IntegerField)
    raceid = models.IntegerField(null=False, blank=False)
    driverid = models.IntegerField(null=False, blank=False)
    lap = models.IntegerField(null=False, blank=False) # Número da volta

    # Campos de tempo e posição
    position = models.IntegerField(db_column='position', null=False, blank=False) # DDL é int4, 'position' entre aspas
    time = models.CharField(db_column='time', max_length=50, null=True, blank=True) # DDL é varchar(50), 'time' entre aspas
    milliseconds = models.IntegerField(null=True, blank=True) # DDL é int4, será calculado a partir de 'time'

    class Meta:
        db_table = 'lap_times' # Assumindo schema padrão
        managed = False # Django não gerencia a tabela
        verbose_name = "Tempo de Volta"
        verbose_name_plural = "Tempos de Volta"
        # UNIQUE (raceid, driverid, lap) conforme DDL
        unique_together = ('raceid', 'driverid', 'lap')
        ordering = ['raceid', 'lap', 'position'] # Ordem padrão

    def __str__(self):
        return f"Volta {self.lap} - Piloto ID: {self.driverid}, Corrida ID: {self.raceid}, Tempo: {self.time}"