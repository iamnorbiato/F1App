# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_results.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import Result, Race, Drivers, Constructors, Status
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Importa e atualiza dados de resultados de corridas da API Ergast F1. Agora com paginação para trazer todos os registros.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar/atualizar os dados de resultados. Padrão é o ano corrente.'
        )

    def handle(self, *args, **options):
        year = options['year'] if options['year'] is not None else datetime.now().year
        base_api_url = f"https://api.jolpi.ca/ergast/f1/{year}/results/"

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação paginada de resultados para o ano {year} de {base_api_url}...'))

        new_results_count = 0
        updated_results_count = 0
        skipped_error_results_count = 0

        all_races_data = []
        limit = 30
        offset = 0
        total_records = None

        while True:
            api_url = f"{base_api_url}?limit={limit}&offset={offset}"
            self.stdout.write(self.style.SUCCESS(f"  Fetching page: {api_url}"))

            try:
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()

                mr_data = data.get('MRData', {})
                if total_records is None:
                    total_records = int(mr_data.get('total', 0))
                    self.stdout.write(self.style.SUCCESS(f"  Total de resultados (aproximado) a importar: {total_records}"))

                races_on_page = mr_data.get('RaceTable', {}).get('Races', [])
                all_races_data.extend(races_on_page)

                if not races_on_page or (offset + len(races_on_page)) >= total_records:
                    break
                else:
                    offset += limit

            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f'Erro de conexão/API ao buscar página {api_url}: {e}'))
                skipped_error_results_count += total_records if total_records is not None else 0
                break
            except json.JSONDecodeError as e:
                self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da página {api_url}: {e}'))
                skipped_error_results_count += total_records if total_records is not None else 0
                break
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a paginação para {api_url}: {e}'))
                skipped_error_results_count += total_records if total_records is not None else 0
                break

        total_collected_results = sum(len(race.get('Results', [])) for race in all_races_data)
        self.stdout.write(self.style.SUCCESS(f'\nIniciando processamento de {len(all_races_data)} corridas (contendo um total de {total_collected_results} resultados) coletadas...'))

        last_result_global = Result.objects.order_by('-resultid').first()
        next_result_id_counter = 1 if not last_result_global or last_result_global.resultid is None else last_result_global.resultid + 1

        for race_json in all_races_data:
            api_season = int(race_json['season'])
            api_round = int(race_json['round'])

            try:
                race_obj = Race.objects.get(year=api_season, round=api_round)
                race_id_from_db = race_obj.raceid
            except Race.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Erro: Corrida (Ano: {api_season}, Rodada: {api_round}) não encontrada no banco de dados. Ignorando resultados desta corrida.'))
                if 'Results' in race_json:
                    skipped_error_results_count += len(race_json['Results'])
                continue

            if 'Results' in race_json:
                for result_json in race_json['Results']:
                    driver_api_id = result_json['Driver']['driverId']
                    constructor_api_id = result_json['Constructor']['constructorId']
                    status_api_status = result_json['status']

                    try:
                        driver_obj = Drivers.objects.get(driverref=driver_api_id)
                        driver_id_from_db = driver_obj.driverid
                    except Drivers.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f'Erro: Piloto (Ref: {driver_api_id}) não encontrado no banco de dados. Ignorando este resultado.'))
                        skipped_error_results_count += 1
                        continue

                    try:
                        constructor_obj = Constructors.objects.get(constructorref=constructor_api_id)
                        constructor_id_from_db = constructor_obj.constructorid
                    except Constructors.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f'Erro: Construtor (Ref: {constructor_api_id}) não encontrado no banco de dados. Ignorando este resultado.'))
                        skipped_error_results_count += 1
                        continue

                    try:
                        status_obj = Status.objects.get(status=status_api_status)
                        status_id_from_db = status_obj.statusid
                    except Status.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f'Erro: Status (Valor: "{status_api_status}") não encontrado no banco de dados. Ignorando este resultado.'))
                        skipped_error_results_count += 1
                        continue

                    number = int(result_json['number']) if 'number' in result_json else None
                    grid = int(result_json['grid']) if 'grid' in result_json else None
                    position = result_json.get('position')
                    position_text = result_json.get('positionText')
                    position_order = int(result_json['positionOrder']) if 'positionOrder' in result_json else None
                    points = float(result_json.get('points', 0))
                    laps = int(result_json['laps']) if 'laps' in result_json else None
                    time_str = result_json.get('Time', {}).get('time')
                    milliseconds_str = result_json.get('Time', {}).get('millis')
                    fastest_lap_rank = result_json.get('FastestLap', {}).get('rank')
                    fastest_lap_time = result_json.get('FastestLap', {}).get('Time', {}).get('time')
                    fastest_lap_speed = None
                    rank_value = result_json.get('FastestLap', {}).get('rank')

                    try:
                        with transaction.atomic():
                            existing_result = Result.objects.filter(
                                raceid=race_id_from_db,
                                driverid=driver_id_from_db,
                                constructorid=constructor_id_from_db,
                                number=number
                            ).first()

                            if existing_result:
                                existing_result.grid = grid
                                existing_result.position = position
                                existing_result.positiontext = position_text
                                existing_result.positionorder = position_order
                                existing_result.points = points
                                existing_result.laps = laps
                                existing_result.time = time_str
                                existing_result.milliseconds = milliseconds_str
                                existing_result.fastestlap = result_json.get('FastestLap', {}).get('lap')
                                existing_result.rank = rank_value
                                existing_result.fastestlaptime = fastest_lap_time
                                existing_result.fastestlapspeed = fastest_lap_speed
                                existing_result.statusid = status_id_from_db
                                existing_result.save()
                                updated_results_count += 1
                                self.stdout.write(self.style.WARNING(f'Atualizado Resultado: Piloto {driver_obj.surname} - Corrida {api_round}'))
                            else:
                                result_data = {
                                    'resultid': next_result_id_counter,
                                    'raceid': race_id_from_db,
                                    'driverid': driver_id_from_db,
                                    'constructorid': constructor_id_from_db,
                                    'statusid': status_id_from_db,
                                    'number': number,
                                    'grid': grid,
                                    'position': position,
                                    'positiontext': position_text,
                                    'positionorder': position_order,
                                    'points': points,
                                    'laps': laps,
                                    'time': time_str,
                                    'milliseconds': milliseconds_str,
                                    'fastestlap': result_json.get('FastestLap', {}).get('lap'),
                                    'rank': rank_value,
                                    'fastestlaptime': fastest_lap_time,
                                    'fastestlapspeed': fastest_lap_speed,
                                }
                                Result.objects.create(**result_data)
                                new_results_count += 1
                                self.stdout.write(self.style.SUCCESS(f'Criado NOVO Resultado: Piloto {driver_obj.surname} - Corrida {api_round} (ID: {next_result_id_counter})'))
                                next_result_id_counter += 1

                    except IntegrityError as e:
                        skipped_error_results_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro de Integridade ao processar Resultado (Piloto {driver_api_id}, Corrida {api_round}): {e}'))
                    except Exception as e:
                        skipped_error_results_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar resultado (Piloto {driver_api_id}, Corrida {api_round}): {e}'))

        self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Resultados ---'))
        self.stdout.write(self.style.SUCCESS(f'Resultados Novos Inseridos: {new_results_count}'))
        self.stdout.write(self.style.WARNING(f'Resultados Atualizados: {updated_results_count}'))
        self.stdout.write(self.style.ERROR(f'Resultados com Erros/Ignorados: {skipped_error_results_count}'))
        self.stdout.write(self.style.SUCCESS('Importação de resultados concluída!'))
