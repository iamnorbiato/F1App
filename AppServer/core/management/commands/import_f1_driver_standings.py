# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_driver_standings.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import DriverStandings, Race, Drivers # Importe todos os modelos necessários
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa e atualiza dados de classificação de pilotos da API Ergast F1.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar/atualizar os dados de classificação de pilotos. Padrão é o ano corrente.'
        )

    def handle(self, *args, **options):
        year = options['year'] if options['year'] is not None else datetime.now().year
        api_url = f"https://api.jolpi.ca/ergast/f1/{year}/driverstandings/"

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação/atualização de classificação de pilotos para o ano {year} de {api_url}...'))

        new_standings_count = 0
        updated_standings_count = 0
        skipped_error_standings_count = 0 # Contagem para erros internos ou dados ausentes

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            if 'MRData' in data and 'StandingsTable' in data['MRData'] and 'StandingsLists' in data['MRData']['StandingsTable']:
                standings_lists = data['MRData']['StandingsTable']['StandingsLists']

                if not standings_lists:
                    self.stdout.write(self.style.WARNING(f"Nenhum dado de classificação de pilotos encontrado para o ano {year} na API."))
                    return

                # Obter o último driverstandingsid existente ANTES do loop principal.
                last_standing_global = DriverStandings.objects.order_by('-driverstandingsid').first()
                next_standings_id_counter = 1 if not last_standing_global or last_standing_global.driverstandingsid is None else last_standing_global.driverstandingsid + 1

                for standings_list in standings_lists:
                    api_season = int(standings_list['season'])
                    api_round = int(standings_list['round'])

                    # 1. Encontrar a Race correspondente para obter o raceid.
                    try:
                        race_obj = Race.objects.get(year=api_season, round=api_round)
                        race_id_from_db = race_obj.raceid
                    except Race.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f'Erro: Corrida (Ano: {api_season}, Rodada: {api_round}) não encontrada no banco de dados. Ignorando classificações desta rodada.'))
                        if 'DriverStandings' in standings_list:
                             skipped_error_standings_count += len(standings_list['DriverStandings'])
                        continue

                    if 'DriverStandings' in standings_list:
                        for driver_standing_json in standings_list['DriverStandings']:
                            driver_api_id = driver_standing_json['Driver']['driverId']

                            # 2. Encontrar o Driver correspondente para obter o driverid.
                            try:
                                driver_obj = Drivers.objects.get(driverref=driver_api_id)
                                driver_id_from_db = driver_obj.driverid
                            except Drivers.DoesNotExist:
                                self.stderr.write(self.style.ERROR(f'Erro: Piloto (Ref: {driver_api_id}) não encontrado no banco de dados. Ignorando classificação para esta rodada/piloto.'))
                                skipped_error_standings_count += 1
                                continue

                            # Converter campos para os tipos corretos
                            points = float(driver_standing_json.get('points', 0))
                            position = int(driver_standing_json.get('position', 0))
                            position_text = driver_standing_json.get('positionText') # CharField no modelo
                            wins = int(driver_standing_json.get('wins', 0))

                            try:
                                with transaction.atomic():
                                    # Tenta encontrar o registro existente
                                    existing_standing = DriverStandings.objects.filter(
                                        raceid=race_id_from_db,
                                        driverid=driver_id_from_db
                                    ).first()

                                    if existing_standing:
                                        # Se o registro existe, atualiza os campos
                                        existing_standing.points = points
                                        existing_standing.position = position
                                        existing_standing.positiontext = position_text
                                        existing_standing.wins = wins
                                        existing_standing.save()
                                        updated_standings_count += 1
                                        self.stdout.write(self.style.WARNING(f'Atualizada Classificação: Piloto {driver_obj.forename} {driver_obj.surname} - Rodada {api_round}'))
                                    else:
                                        # Se o registro não existe, cria um novo
                                        standing_data = {
                                            'driverstandingsid': next_standings_id_counter, # Atribui o ID sequencial AQUI
                                            'raceid': race_id_from_db,
                                            'driverid': driver_id_from_db,
                                            'points': points,
                                            'position': position,
                                            'positiontext': position_text,
                                            'wins': wins,
                                        }
                                        DriverStandings.objects.create(**standing_data)
                                        new_standings_count += 1
                                        self.stdout.write(self.style.SUCCESS(f'Criada Classificação: Piloto {driver_obj.forename} {driver_obj.surname} - Rodada {api_round} (ID: {next_standings_id_counter})'))
                                        next_standings_id_counter += 1 # Incrementa apenas para NOVAS criações

                            except IntegrityError as e:
                                skipped_error_standings_count += 1
                                self.stderr.write(self.style.ERROR(f'Erro de Integridade (provável duplicidade não tratada) ao processar Piloto {driver_api_id} (Rodada {api_round}): {e}'))
                            except Exception as e:
                                skipped_error_standings_count += 1
                                self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar classificação Piloto {driver_api_id} (Rodada {api_round}): {e}'))

            else:
                self.stderr.write(self.style.ERROR('Estrutura JSON inesperada para classificação de pilotos. Verifique o formato da API.'))
                skipped_error_standings_count += 1

            self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Classificação de Pilotos ---'))
            self.stdout.write(self.style.SUCCESS(f'Classificações Novas Inseridas: {new_standings_count}'))
            self.stdout.write(self.style.WARNING(f'Classificações Atualizadas: {updated_standings_count}'))
            self.stdout.write(self.style.ERROR(f'Classificações com Erros/Ignoradas: {skipped_error_standings_count}'))
            self.stdout.write(self.style.SUCCESS('Importação de classificação de pilotos concluída!'))

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Erro ao conectar ou obter dados da API Ergast: {e}'))
            self.stdout.write(self.style.ERROR('Importação de classificação de pilotos FALHOU devido a erro de conexão/API.'))
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da API: {e}'))
            self.stdout.write(self.style.ERROR('Importação de classificação de pilotos FALHOU devido a erro de formato JSON.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a importação geral: {e}'))
            self.stdout.write(self.style.ERROR('Importação de classificação de pilotos FALHOU devido a erro inesperado.'))