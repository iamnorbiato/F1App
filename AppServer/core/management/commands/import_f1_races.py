# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_races.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError # Importar IntegrityError para lidar com duplicidade
from core.models import Race, Circuit
import json
import os
from datetime import datetime 

class Command(BaseCommand):
    help = 'Importa dados de corridas da API Ergast F1 e popula o banco de dados. Apenas novas corridas são adicionadas.'

    def add_arguments(self, parser):
        # Adiciona o argumento --year (opcional)
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar os dados de corridas. Padrão é o ano corrente.'
        )

    def handle(self, *args, **options):
        # Determina o ano a ser usado
        # Se --year foi fornecido, usa esse ano. Caso contrário, usa o ano corrente (2025 atualmente).
        year = options['year'] if options['year'] is not None else datetime.now().year

        # Constrói a URL da API com o ano dinâmico
        api_url = f"https://api.jolpi.ca/ergast/f1/{year}/races/"

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação de dados de corridas de {api_url}...'))

        # Contadores para o resumo final
        new_races_count = 0
        skipped_existing_races_count = 0
        error_races_count = 0

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            if 'MRData' in data and 'RaceTable' in data['MRData'] and 'Races' in data['MRData']['RaceTable']:
                races_data = data['MRData']['RaceTable']['Races']

                # Obter o último raceid existente ANTES do loop.
                # Se não houver corridas, começa com 1.
                # Certifica-se de ordenar corretamente pelo campo raceid.
                last_race = Race.objects.order_by('-raceid').first()
                next_race_id_counter = 1 if not last_race or last_race.raceid is None else last_race.raceid + 1

                for race_json in races_data:
                    year = int(race_json['season'])
                    round_num = int(race_json['round'])
                    circuit_ref = race_json['Circuit']['circuitId']

                    try:
                        with transaction.atomic():
                            # 1. Verificar se a corrida já existe (usando year e round como chaves de unicidade)
                            if Race.objects.filter(year=year, round=round_num).exists():
                                skipped_existing_races_count += 1
                                self.stdout.write(self.style.WARNING(f'Corrida EXISTENTE (Ignorada): {race_json["raceName"]} ({year} R{round_num})'))
                                continue # Pula para a próxima corrida

                            # 2. Encontrar o Circuit correspondente ou pular se não existir
                            try:
                                # Não precisamos da instância completa do Circuit, apenas confirmamos sua existência
                                # e pegamos o circuitId da API para o campo circuitid do Race
                                # A linha abaixo serve apenas para validar que o circuito existe no seu DB
                                Circuit.objects.get(circuitRef=circuit_ref)
                            except Circuit.DoesNotExist:
                                error_races_count += 1
                                self.stderr.write(self.style.ERROR(f'Erro: Circuito {circuit_ref} não encontrado no banco de dados. Ignorando corrida {race_json["raceName"]} ({year} R{round_num}).'))
                                continue # Pula para a próxima corrida se o circuito não estiver no DB

                            # 3. Preparar dados da corrida para criação
                            # Assegura que fpX_date/time, quali_date/time, sprint_date/time sejam None se não existirem
                            race_data = {
                                'raceid': next_race_id_counter, # Atribuir o raceid sequencial aqui
                                'year': year,
                                'round': round_num,
                                'circuitid': circuit_ref, # Passa o circuitId da API diretamente
                                'name': race_json['raceName'],
                                'date': race_json['date'],
                                'time': race_json['time'],
                                'url': race_json['url'],
                                'fp1_date': race_json.get('FirstPractice', {}).get('date'),
                                'fp1_time': race_json.get('FirstPractice', {}).get('time'),
                                'fp2_date': race_json.get('SecondPractice', {}).get('date'),
                                'fp2_time': race_json.get('SecondPractice', {}).get('time'),
                                'fp3_date': race_json.get('ThirdPractice', {}).get('date'),
                                'fp3_time': race_json.get('ThirdPractice', {}).get('time'),
                                'quali_date': race_json.get('Qualifying', {}).get('date'),
                                'quali_time': race_json.get('Qualifying', {}).get('time'),
                                'sprint_date': race_json.get('Sprint', {}).get('date'),
                                'sprint_time': race_json.get('Sprint', {}).get('time'),
                                # Se 'SprintQualifying' for necessário, adicione aqui e no models.py
                                # 'sprint_quali_date': race_json.get('SprintQualifying', {}).get('date'),
                                # 'sprint_quali_time': race_json.get('SprintQualifying', {}).get('time'),
                            }

                            # 4. Criar a nova corrida
                            race = Race.objects.create(**race_data)
                            new_races_count += 1
                            self.stdout.write(self.style.SUCCESS(f'Adicionada NOVA Corrida: {race.name} ({race.year} R{race.round}, RaceID: {race.raceid})'))
                            next_race_id_counter += 1 # Incrementa para a próxima nova corrida

                    except IntegrityError as e:
                        # Este erro pode ocorrer se houver uma corrida duplicada inserida por outra transação
                        # ou se houver um raceid duplicado por algum motivo, embora o exists() tente evitar.
                        skipped_existing_races_count += 1
                        self.stderr.write(self.style.WARNING(f'Erro de Integridade (provável duplicidade) para {race_json.get("raceName", "N/A")}: {e}'))
                    except Exception as e:
                        error_races_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar corrida {race_json.get("raceName", "N/A")}: {e}'))

            else:
                self.stderr.write(self.style.ERROR('Estrutura JSON inesperada para corridas. Verifique o formato da API.'))
                # Pode ajustar error_races_count aqui se souber o total de corridas esperadas
                error_races_count = len(races_data) if 'MRData' in data and 'RaceTable' in data['MRData'] else 0

            # --- Resumo final ---
            self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Corridas ---'))
            self.stdout.write(self.style.SUCCESS(f'Corridas Novas Inseridas: {new_races_count}'))
            self.stdout.write(self.style.WARNING(f'Corridas Existentes (Ignoradas): {skipped_existing_races_count}'))
            self.stdout.write(self.style.ERROR(f'Corridas com Erros: {error_races_count}'))
            self.stdout.write(self.style.SUCCESS('Importação de corridas concluída!'))

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Erro ao conectar ou obter dados da API Ergast: {e}'))
            self.stdout.write(self.style.ERROR('Importação de corridas FALHOU devido a erro de conexão/API.'))
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da API: {e}'))
            self.stdout.write(self.style.ERROR('Importação de corridas FALHOU devido a erro de formato JSON.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a importação geral: {e}'))
            self.stdout.write(self.style.ERROR('Importação de corridas FALHOU devido a erro inesperado.'))