# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_constructor_standings.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import ConstructorStandings, Race, Constructors # Importe todos os modelos necessários (Race singular)
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa e atualiza dados de classificação de construtores da API Ergast F1.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar/atualizar os dados de classificação de construtores. Padrão é o ano corrente.'
        )

    def handle(self, *args, **options):
        year = options['year'] if options['year'] is not None else datetime.now().year
        api_url = f"https://api.jolpi.ca/ergast/f1/{year}/constructorstandings/"

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação/atualização de classificação de construtores para o ano {year} de {api_url}...'))

        new_standings_count = 0
        updated_standings_count = 0
        skipped_error_standings_count = 0

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            if 'MRData' in data and 'StandingsTable' in data['MRData'] and 'StandingsLists' in data['MRData']['StandingsTable']:
                standings_lists = data['MRData']['StandingsTable']['StandingsLists']

                if not standings_lists:
                    self.stdout.write(self.style.WARNING(f"Nenhum dado de classificação de construtores encontrado para o ano {year} na API."))
                    return

                # Obter o último constructorstandingsid existente ANTES do loop principal.
                # Este contador será incrementado APENAS para NOVAS criações.
                last_standing_global = ConstructorStandings.objects.order_by('-constructorstandingsid').first()
                next_standings_id_counter = 1 if not last_standing_global or last_standing_global.constructorstandingsid is None else last_standing_global.constructorstandingsid + 1


                for standings_list in standings_lists:
                    api_season = int(standings_list['season'])
                    api_round = int(standings_list['round'])

                    try:
                        race_obj = Race.objects.get(year=api_season, round=api_round)
                        race_id_from_db = race_obj.raceid
                    except Race.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f'Erro: Corrida (Ano: {api_season}, Rodada: {api_round}) não encontrada no banco de dados. Ignorando classificações desta rodada.'))
                        # Pode ser mais preciso contar o número de classificações ignoradas se o race_obj não existir
                        if 'ConstructorStandings' in standings_list:
                             skipped_error_standings_count += len(standings_list['ConstructorStandings'])
                        continue

                    if 'ConstructorStandings' in standings_list:
                        for constructor_standing_json in standings_list['ConstructorStandings']:
                            constructor_api_id = constructor_standing_json['Constructor']['constructorId']

                            try:
                                constructor_obj = Constructors.objects.get(constructorref=constructor_api_id)
                                constructor_id_from_db = constructor_obj.constructorid
                            except Constructors.DoesNotExist:
                                self.stderr.write(self.style.ERROR(f'Erro: Construtor (Ref: {constructor_api_id}) não encontrado no banco de dados. Ignorando classificação para esta rodada/construtor.'))
                                skipped_error_standings_count += 1
                                continue

                            points = float(constructor_standing_json.get('points', 0)) # Usar .get e valor padrão
                            position = int(constructor_standing_json.get('position', 0))
                            position_text = constructor_standing_json.get('positionText')
                            wins = int(constructor_standing_json.get('wins', 0))

                            try:
                                with transaction.atomic():
                                    # Tenta encontrar o registro existente
                                    existing_standing = ConstructorStandings.objects.filter(
                                        raceid=race_id_from_db,
                                        constructorid=constructor_id_from_db
                                    ).first()

                                    if existing_standing:
                                        # Se o registro existe, atualiza os campos
                                        existing_standing.points = points
                                        existing_standing.position = position
                                        existing_standing.positiontext = position_text
                                        existing_standing.wins = wins
                                        existing_standing.save()
                                        updated_standings_count += 1
                                        self.stdout.write(self.style.WARNING(f'Atualizada Classificação: Construtor {constructor_obj.name} - Rodada {api_round}'))
                                    else:
                                        # Se o registro não existe, cria um novo
                                        standing_data = {
                                            'constructorstandingsid': next_standings_id_counter, # Atribui o ID sequencial AQUI
                                            'raceid': race_id_from_db,
                                            'constructorid': constructor_id_from_db,
                                            'points': points,
                                            'position': position,
                                            'positiontext': position_text,
                                            'wins': wins,
                                        }
                                        ConstructorStandings.objects.create(**standing_data)
                                        new_standings_count += 1
                                        self.stdout.write(self.style.SUCCESS(f'Criada Classificação: Construtor {constructor_obj.name} - Rodada {api_round} (ID: {next_standings_id_counter})'))
                                        next_standings_id_counter += 1 # Incrementa apenas para NOVAS criações

                            except IntegrityError as e:
                                skipped_error_standings_count += 1
                                self.stderr.write(self.style.ERROR(f'Erro de Integridade (provável duplicidade não tratada) ao processar Construtor {constructor_api_id} (Rodada {api_round}): {e}'))
                            except Exception as e:
                                skipped_error_standings_count += 1
                                self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar classificação Construtor {constructor_api_id} (Rodada {api_round}): {e}'))

            else:
                self.stderr.write(self.style.ERROR('Estrutura JSON inesperada para classificação de construtores. Verifique o formato da API.'))
                skipped_error_standings_count += 1

            self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Classificação de Construtores ---'))
            self.stdout.write(self.style.SUCCESS(f'Classificações Novas Inseridas: {new_standings_count}'))
            self.stdout.write(self.style.WARNING(f'Classificações Atualizadas: {updated_standings_count}'))
            self.stdout.write(self.style.ERROR(f'Classificações com Erros/Ignoradas: {skipped_error_standings_count}'))
            self.stdout.write(self.style.SUCCESS('Importação de classificação de construtores concluída!'))

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Erro ao conectar ou obter dados da API Ergast: {e}'))
            self.stdout.write(self.style.ERROR('Importação de classificação de construtores FALHOU devido a erro de conexão/API.'))
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da API: {e}'))
            self.stdout.write(self.style.ERROR('Importação de classificação de construtores FALHOU devido a erro de formato JSON.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a importação geral: {e}'))
            self.stdout.write(self.style.ERROR('Importação de classificação de construtores FALHOU devido a erro inesperado.'))