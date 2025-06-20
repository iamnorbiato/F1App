# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_pit_stops.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import PitStop, Race, Drivers
import json
from datetime import datetime

# Função auxiliar para formatar milissegundos (string) em MM:SS.sss (string)
def format_milliseconds_to_mm_ss_sss(ms_str):
    if ms_str is None or not str(ms_str).isdigit(): # Valida se é uma string numérica
        return None
    
    ms = int(ms_str)
    total_seconds = ms / 1000.0
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    milliseconds_remainder = int((total_seconds - int(total_seconds)) * 1000)

    return f"{minutes:02d}:{seconds:02d}.{milliseconds_remainder:03d}"


class Command(BaseCommand):
    help = 'Importa e atualiza dados de pit stops da API Ergast F1. Realiza paginação por rodada e por página.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar/atualizar os dados de pit stops. Padrão é o ano corrente.'
        )

    def handle(self, *args, **options):
        year = options['year'] if options['year'] is not None else datetime.now().year

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação de pit stops para o ano {year}...'))

        new_pitstops_count = 0
        updated_pitstops_count = 0
        skipped_error_pitstops_count = 0

        try:
            available_rounds = Race.objects.filter(year=year).order_by('round').values_list('round', flat=True)

            if not available_rounds:
                self.stdout.write(self.style.WARNING(f"Nenhuma rodada encontrada na tabela Race para o ano {year}. Certifique-se de importar corridas primeiro."))
                return

            self.stdout.write(self.style.SUCCESS(f"Rodadas encontradas para o ano {year}: {list(available_rounds)}"))

            # Obter o último pit_stopid existente ANTES do loop principal.
            last_pit_stop_global = PitStop.objects.order_by('-pit_stopid').first()
            next_pit_stop_id_counter = 1 if not last_pit_stop_global or last_pit_stop_global.pit_stopid is None else last_pit_stop_global.pit_stopid + 1

            for api_round in available_rounds:
                base_api_url_round = f"https://api.jolpi.ca/ergast/f1/{year}/{api_round}/pitstops"

                all_pitstops_data_for_round = []
                limit = 30
                offset = 0
                total_records_round = None

                while True:
                    api_url = f"{base_api_url_round}?limit={limit}&offset={offset}"
                    self.stdout.write(self.style.SUCCESS(f"  Fetching pit stops for Round {api_round}, page: {api_url}"))

                    try:
                        response = requests.get(api_url)
                        response.raise_for_status()
                        data = response.json()

                        mr_data = data.get('MRData', {})
                        if total_records_round is None:
                            total_records_round = int(mr_data.get('total', 0))
                            self.stdout.write(self.style.SUCCESS(f"  Total de pit stops para Round {api_round}: {total_records_round}"))

                        races_list_on_page = mr_data.get('RaceTable', {}).get('Races', [])
                        pitstops_on_page = []
                        if races_list_on_page:
                            pitstops_on_page = races_list_on_page[0].get('PitStops', [])

                        all_pitstops_data_for_round.extend(pitstops_on_page)

                        if not pitstops_on_page or (offset + len(pitstops_on_page)) >= total_records_round:
                            break
                        else:
                            offset += limit

                    except requests.exceptions.RequestException as e:
                        self.stderr.write(self.style.ERROR(f'Erro ao conectar/API para Round {api_round}, página {api_url}: {e}'))
                        skipped_error_pitstops_count += total_records_round if total_records_round is not None else 0
                        break
                    except json.JSONDecodeError as e:
                        self.stderr.write(self.style.ERROR(f'Erro JSON para Round {api_round}, página {api_url}: {e}'))
                        skipped_error_pitstops_count += total_records_round if total_records_round is not None else 0
                        break
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a paginação para {api_url}: {e}'))
                        skipped_error_pitstops_count += total_records_round if total_records_round is not None else 0
                        break

                self.stdout.write(self.style.SUCCESS(f'\nIniciando processamento de {len(all_pitstops_data_for_round)} pit stops coletados para Round {api_round}...'))

                try:
                    race_obj_db = Race.objects.get(year=year, round=api_round)
                    race_id_from_db = race_obj_db.raceid
                except Race.DoesNotExist:
                    self.stderr.write(self.style.ERROR(f'Erro CRÍTICO: Corrida (Ano: {year}, Rodada: {api_round}) não encontrada no DB após coleta de pit stops. Isso não deveria acontecer. Ignorando pit stops desta rodada.'))
                    skipped_error_pitstops_count += len(all_pitstops_data_for_round)
                    continue

                for pitstop_json in all_pitstops_data_for_round:
                    driver_api_id = pitstop_json['driverId']
                    stop_number = int(pitstop_json['stop'])

                    try:
                        driver_obj = Drivers.objects.get(driverref=driver_api_id)
                        driver_id_from_db = driver_obj.driverid
                    except Drivers.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f'Erro: Piloto (Ref: {driver_api_id}) não encontrado no DB. Ignorando pit stop da Corrida {api_round}, Parada {stop_number}.'))
                        skipped_error_pitstops_count += 1
                        continue

                    lap = int(pitstop_json['lap']) if 'lap' in pitstop_json else None
                    time_str = pitstop_json.get('time')

                    raw_milliseconds_str = pitstop_json.get('milliseconds')
                    # Formatamos o campo 'duration' a partir de 'milliseconds' (string)
                    # usando a função auxiliar para garantir "MM:SS.sss"
                    formatted_duration_str = format_milliseconds_to_mm_ss_sss(raw_milliseconds_str)

                    try:
                        with transaction.atomic():
                            existing_pitstop = PitStop.objects.filter(
                                raceid=race_id_from_db,
                                driverid=driver_id_from_db,
                                stop=stop_number
                            ).first()

                            if existing_pitstop:
                                existing_pitstop.lap = lap
                                existing_pitstop.time = time_str
                                existing_pitstop.duration = formatted_duration_str
                                existing_pitstop.milliseconds = raw_milliseconds_str
                                existing_pitstop.save()
                                updated_pitstops_count += 1
                                self.stdout.write(self.style.WARNING(f'Atualizado Pit Stop: Piloto {driver_obj.surname}, Corrida {api_round}, Parada {stop_number}'))
                            else:
                                pitstop_data = {
                                    'pit_stopid': next_pit_stop_id_counter,
                                    'raceid': race_id_from_db,
                                    'driverid': driver_id_from_db,
                                    'stop': stop_number,
                                    'lap': lap,
                                    'time': time_str,
                                    'duration': formatted_duration_str,
                                    'milliseconds': raw_milliseconds_str,
                                }
                                pitstop = PitStop.objects.create(**pitstop_data)
                                new_pitstops_count += 1
                                self.stdout.write(self.style.SUCCESS(f'Criado NOVO Pit Stop: Piloto {driver_obj.surname}, Corrida {api_round}, Parada {stop_number} (ID: {pitstop.pit_stopid})'))
                                next_pit_stop_id_counter += 1

                    except IntegrityError as e:
                        skipped_error_pitstops_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro de Integridade ao processar Pit Stop (Piloto {driver_api_id}, Corrida {api_round}, Parada {stop_number}): {e}'))
                    except Exception as e:
                        skipped_error_pitstops_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar Pit Stop (Piloto {driver_api_id}, Corrida {api_round}, Parada {stop_number}): {e}. Detalhe: {e}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ocorreu um erro geral durante a importação: {e}'))
            self.stdout.write(self.style.ERROR('Importação de pit stops FALHOU devido a erro geral inesperado.'))


        self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Pit Stops ---'))
        self.stdout.write(self.style.SUCCESS(f'Pit Stops Novos Inseridos: {new_pitstops_count}'))
        self.stdout.write(self.style.WARNING(f'Pit Stops Atualizados: {updated_pitstops_count}'))
        self.stdout.write(self.style.ERROR(f'Pit Stops com Erros/Ignorados: {skipped_error_pitstops_count}'))
        self.stdout.write(self.style.SUCCESS('Importação de pit stops concluída!'))