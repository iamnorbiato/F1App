# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_lap_times.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import LapTimes, Race, Drivers # Importe os modelos necessários
import json
from datetime import datetime
import time # Importar o módulo time para usar sleep

# Função auxiliar para parsear tempo MM:SS.sss para milissegundos (int)
def parse_time_to_milliseconds(time_str):
    if not time_str:
        return None
    
    try:
        if '.' in time_str:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds_ms = parts[1].split('.')
            seconds = int(seconds_ms[0])
            milliseconds = int(seconds_ms[1].ljust(3, '0')[:3]) # Garante 3 dígitos para milissegundos
            return (minutes * 60 * 1000) + (seconds * 1000) + milliseconds
        else:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1])
            return (minutes * 60 * 1000) + (seconds * 1000)
    except ValueError:
        return None

class Command(BaseCommand):
    help = 'Importa e atualiza dados de tempos de volta (laps) da API Ergast F1. Realiza paginação por rodada e por página.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar/atualizar os dados de tempos de volta. Padrão é o ano corrente.'
        )
        parser.add_argument(
            '--round',
            type=int,
            help='Opcional. A rodada específica para importar os dados de tempos de volta. Se omitido, importa todas as rodadas do ano.'
        )

    def handle(self, *args, **options):
        year = options['year'] if options['year'] is not None else datetime.now().year
        specific_round = options['round']

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação de tempos de volta para o ano {year}...'))
        if specific_round:
            self.stdout.write(self.style.SUCCESS(f'Processando apenas a rodada: {specific_round}'))


        new_laptimes_count = 0
        updated_laptimes_count = 0
        skipped_error_laptimes_count = 0

        try:
            if specific_round:
                rounds_to_process = [specific_round]
            else:
                available_rounds = Race.objects.filter(year=year).order_by('round').values_list('round', flat=True)
                if not available_rounds:
                    self.stdout.write(self.style.WARNING(f"Nenhuma rodada encontrada na tabela Race para o ano {year}. Certifique-se de importar corridas primeiro."))
                    return
                rounds_to_process = list(available_rounds)
                self.stdout.write(self.style.SUCCESS(f"Rodadas encontradas para o ano {year}: {rounds_to_process}"))

            # Obter o último lap_timeid existente ANTES do loop principal.
            last_lap_time_global = LapTimes.objects.order_by('-lap_timeid').first()
            next_lap_time_id_counter = 1 if not last_lap_time_global or last_lap_time_global.lap_timeid is None else last_lap_time_global.lap_timeid + 1

            for api_round in rounds_to_process:
                base_api_url_round = f"https://api.jolpi.ca/ergast/f1/{year}/{api_round}/laps"

                all_laps_data_for_round = []
                limit = 30
                offset = 0
                total_records_round = None

                while True:
                    api_url = f"{base_api_url_round}?limit={limit}&offset={offset}"
                    self.stdout.write(self.style.SUCCESS(f"  Fetching lap times for Round {api_round}, page: {api_url}"))

                    try:
                        response = requests.get(api_url)
                        response.raise_for_status()
                        data = response.json()

                        mr_data = data.get('MRData', {})
                        if total_records_round is None:
                            total_records_round = int(mr_data.get('total', 0))
                            self.stdout.write(self.style.SUCCESS(f"  Total de tempos de volta para Round {api_round}: {total_records_round}"))

                        races_list_on_page = mr_data.get('RaceTable', {}).get('Races', [])
                        laps_on_page = []
                        if races_list_on_page:
                            laps_on_page = races_list_on_page[0].get('Laps', [])

                        all_laps_data_for_round.extend(laps_on_page)

                        if not laps_on_page or (offset + len(laps_on_page)) >= total_records_round:
                            break
                        else:
                            offset += limit
                            time.sleep(15) # PAUSA AQUI: 1 segundo entre as páginas da mesma rodada

                    except requests.exceptions.RequestException as e:
                        self.stderr.write(self.style.ERROR(f'Erro ao conectar/API para Round {api_round}, página {api_url}: {e}'))
                        # Não incrementa skipped_error_laptimes_count aqui, pois o erro é na requisição, não no item
                        time.sleep(5)
                        break
                    except json.JSONDecodeError as e:
                        self.stderr.write(self.style.ERROR(f'Erro JSON para Round {api_round}, página {api_url}: {e}'))
                        # Não incrementa skipped_error_laptimes_count aqui
                        break
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a paginação para {api_url}: {e}'))
                        # Não incrementa skipped_error_laptimes_count aqui
                        break

                self.stdout.write(self.style.SUCCESS(f'\nIniciando processamento de {len(all_laps_data_for_round)} voltas coletadas para Round {api_round}...'))

                try:
                    race_obj_db = Race.objects.get(year=year, round=api_round)
                    race_id_from_db = race_obj_db.raceid
                except Race.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f'Erro CRÍTICO: Corrida (Ano: {year}, Rodada: {api_round}) não encontrada no DB após coleta de tempos de volta. Isso não deveria acontecer. Ignorando tempos de volta desta rodada.'))
                    skipped_error_laptimes_count += len(all_laps_data_for_round) # Conta todos os desta rodada
                    continue

                for lap_json in all_laps_data_for_round:
                    lap_number = int(lap_json['number'])

                    if 'Timings' in lap_json:
                        for timing_json in lap_json['Timings']:
                            driver_api_id = timing_json['driverId']

                            try:
                                driver_obj = Drivers.objects.get(driverref=driver_api_id)
                                driver_id_from_db = driver_obj.driverid
                            except Drivers.DoesNotExist:
                                self.stderr.write(self.style.ERROR(f'Erro: Piloto (Ref: {driver_api_id}) não encontrado no DB. Ignorando tempo de volta da Corrida {api_round}, Volta {lap_number}.'))
                                skipped_error_laptimes_count += 1
                                continue

                            position = int(timing_json['position']) if 'position' in timing_json else None
                            time_str = timing_json.get('time')
                            milliseconds_value = parse_time_to_milliseconds(time_str)

                            try:
                                with transaction.atomic():
                                    existing_lap_time = LapTimes.objects.filter(
                                        raceid=race_id_from_db,
                                        driverid=driver_id_from_db,
                                        lap=lap_number
                                    ).first()

                                    if existing_lap_time:
                                        existing_lap_time.position = position
                                        existing_lap_time.time = time_str
                                        existing_lap_time.milliseconds = milliseconds_value
                                        existing_lap_time.save()
                                        updated_laptimes_count += 1
                                        self.stdout.write(self.style.WARNING(f'Atualizado Tempo de Volta: Piloto {driver_obj.surname}, Corrida {api_round}, Volta {lap_number}'))
                                    else:
                                        lap_time_data = {
                                            'lap_timeid': next_lap_time_id_counter, # Usado aqui
                                            'raceid': race_id_from_db,
                                            'driverid': driver_id_from_db,
                                            'lap': lap_number,
                                            'position': position,
                                            'time': time_str,
                                            'milliseconds': milliseconds_value,
                                        }
                                        LapTimes.objects.create(**lap_time_data)
                                        new_laptimes_count += 1
                                        self.stdout.write(self.style.SUCCESS(f'Criado NOVO Tempo de Volta: Piloto {driver_obj.surname}, Corrida {api_round}, Volta {lap_number}'))
                                        next_lap_time_id_counter += 1 # Incrementado aqui

                            except IntegrityError as e:
                                skipped_error_laptimes_count += 1
                                self.stderr.write(self.style.ERROR(f'Erro de Integridade ao processar Tempo de Volta (Piloto {driver_api_id}, Corrida {api_round}, Volta {lap_number}): {e}'))
                            except Exception as e:
                                skipped_error_laptimes_count += 1
                                self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar Tempo de Volta (Piloto {driver_api_id}, Corrida {api_round}, Volta {lap_number}): {e}. Detalhe: {e}'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ocorreu um erro geral durante a importação: {e}'))
            self.stdout.write(self.style.ERROR('Importação de tempos de volta FALHOU devido a erro geral inesperado.'))


        self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Tempos de Volta ---'))
        self.stdout.write(self.style.SUCCESS(f'Tempos de Volta Novos Inseridos: {new_laptimes_count}'))
        self.stdout.write(self.style.WARNING(f'Tempos de Volta Atualizados: {updated_laptimes_count}'))
        self.stdout.write(self.style.ERROR(f'Tempos de Volta com Erros/Ignorados: {skipped_error_laptimes_count}'))
        self.stdout.write(self.style.SUCCESS('Importação de tempos de volta concluída!'))