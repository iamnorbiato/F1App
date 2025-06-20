# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_qualifying.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import Qualifying, Race, Drivers, Constructors # Importe todos os modelos necessários
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa e atualiza dados de classificação de treinos (qualifying) da API Ergast F1. Agora com paginação para trazer todos os registros.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar/atualizar os dados de qualificação. Padrão é o ano corrente.'
        )

    def handle(self, *args, **options):
        year = options['year'] if options['year'] is not None else datetime.now().year
        base_api_url = f"https://api.jolpi.ca/ergast/f1/{year}/qualifying/" # URL base para qualificação por ano

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação paginada de dados de qualificação para o ano {year} de {base_api_url}...'))

        new_qualifying_count = 0
        updated_qualifying_count = 0
        skipped_error_qualifying_count = 0

        # Lógica de Paginação
        all_races_data = [] # Vamos coletar todas as 'Race's (cada uma com seus 'QualifyingResults')
        limit = 30 # Limite padrão da API Ergast
        offset = 0
        total_records = None # Será atualizado após a primeira requisição

        while True:
            api_url = f"{base_api_url}?limit={limit}&offset={offset}"
            self.stdout.write(self.style.SUCCESS(f"  Fetching page: {api_url}")) # Mensagem de progresso em verde

            try:
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()

                mr_data = data.get('MRData', {})
                if total_records is None:
                    total_records = int(mr_data.get('total', 0))
                    self.stdout.write(self.style.SUCCESS(f"  Total de resultados de qualificação (aproximado) a importar: {total_records}"))

                races_on_page = mr_data.get('RaceTable', {}).get('Races', [])
                all_races_data.extend(races_on_page)

                if not races_on_page or (offset + len(races_on_page)) >= total_records:
                    break # Todos os registros foram baixados ou não há mais páginas
                else:
                    offset += limit # Prepara para a próxima página

            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f'Erro ao conectar ou obter dados da API Ergast: {e}'))
                skipped_error_qualifying_count += total_records if total_records is not None else 0
                break
            except json.JSONDecodeError as e:
                self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da página {api_url}: {e}'))
                skipped_error_qualifying_count += total_records if total_records is not None else 0
                break
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a paginação para {api_url}: {e}'))
                skipped_error_qualifying_count += total_records if total_records is not None else 0
                break

        # Processamento dos dados APÓS a coleta de todas as páginas
        total_collected_results = sum(len(race.get('QualifyingResults', [])) for race in all_races_data)
        self.stdout.write(self.style.SUCCESS(f'\nIniciando processamento de {len(all_races_data)} corridas (contendo um total de {total_collected_results} resultados de qualificação) coletadas...'))

        last_qualifying_global = Qualifying.objects.order_by('-qualifyid').first()
        next_qualify_id_counter = 1 if not last_qualifying_global or last_qualifying_global.qualifyid is None else last_qualifying_global.qualifyid + 1

        for race_json in all_races_data:
            api_season = int(race_json['season'])
            api_round = int(race_json['round'])

            try:
                race_obj = Race.objects.get(year=api_season, round=api_round)
                race_id_from_db = race_obj.raceid
            except Race.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Erro: Corrida (Ano: {api_season}, Rodada: {api_round}) não encontrada no banco de dados. Ignorando resultados de qualificação desta corrida.'))
                if 'QualifyingResults' in race_json:
                    skipped_error_qualifying_count += len(race_json['QualifyingResults'])
                continue

            if 'QualifyingResults' in race_json: # MUDANÇA AQUI: de 'Results' para 'QualifyingResults'
                for result_json in race_json['QualifyingResults']: # MUDANÇA AQUI: de 'Results' para 'QualifyingResults'
                    driver_api_id = result_json['Driver']['driverId']
                    constructor_api_id = result_json['Constructor']['constructorId']

                    try:
                        driver_obj = Drivers.objects.get(driverref=driver_api_id)
                        driver_id_from_db = driver_obj.driverid
                    except Drivers.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f'Erro: Piloto (Ref: {driver_api_id}) não encontrado no banco de dados. Ignorando este resultado de qualificação.'))
                        skipped_error_qualifying_count += 1
                        continue

                    try:
                        constructor_obj = Constructors.objects.get(constructorref=constructor_api_id)
                        constructor_id_from_db = constructor_obj.constructorid
                    except Constructors.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f'Erro: Construtor (Ref: {constructor_api_id}) não encontrado no banco de dados. Ignorando este resultado de qualificação.'))
                        skipped_error_qualifying_count += 1
                        continue

                    # Converte campos para os tipos corretos
                    number = int(result_json['number']) if 'number' in result_json else None
                    position = int(result_json['position']) if 'position' in result_json else None # JSON é string, DDL é int4
                    q1 = result_json.get('Q1')
                    q2 = result_json.get('Q2')
                    q3 = result_json.get('Q3')

                    try:
                        with transaction.atomic():
                            existing_result = Qualifying.objects.filter(
                                raceid=race_id_from_db,
                                driverid=driver_id_from_db
                            ).first()

                            if existing_result:
                                # Atualiza os campos do registro existente
                                existing_result.constructorid = constructor_id_from_db
                                existing_result.number = number
                                existing_result.position = position
                                existing_result.q1 = q1
                                existing_result.q2 = q2
                                existing_result.q3 = q3
                                existing_result.save()
                                updated_qualifying_count += 1
                                self.stdout.write(self.style.WARNING(f'Atualizado Resultado de Qualificação: Piloto {driver_obj.surname} - Corrida {api_round}'))
                            else:
                                # Cria um novo registro
                                result_data = {
                                    'qualifyid': next_qualify_id_counter, # Atribui o ID sequencial
                                    'raceid': race_id_from_db,
                                    'driverid': driver_id_from_db,
                                    'constructorid': constructor_id_from_db,
                                    'number': number,
                                    'position': position,
                                    'q1': q1,
                                    'q2': q2,
                                    'q3': q3,
                                }
                                Qualifying.objects.create(**result_data)
                                new_qualifying_count += 1
                                self.stdout.write(self.style.SUCCESS(f'Criado NOVO Resultado de Qualificação: Piloto {driver_obj.surname} - Corrida {api_round} (ID: {next_qualify_id_counter})'))
                                next_qualify_id_counter += 1

                    except IntegrityError as e:
                        skipped_error_qualifying_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro de Integridade ao processar Resultado de Qualificação (Piloto {driver_api_id}, Corrida {api_round}): {e}'))
                    except Exception as e:
                        skipped_error_qualifying_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar resultado de Qualificação (Piloto {driver_api_id}, Corrida {api_round}): {e}'))

            else:
                self.stderr.write(self.style.ERROR('Estrutura JSON inesperada para resultados de qualificação. Verifique o formato da API.'))
                skipped_error_qualifying_count += 1

            self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Classificação ---'))
            self.stdout.write(self.style.SUCCESS(f'Classificações Novas Inseridas: {new_qualifying_count}'))
            self.stdout.write(self.style.WARNING(f'Classificações Atualizadas: {updated_qualifying_count}'))
            self.stdout.write(self.style.ERROR(f'Classificações com Erros/Ignorados: {skipped_error_qualifying_count}'))
            self.stdout.write(self.style.SUCCESS('Importação de qualificação concluída!'))

