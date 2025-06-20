# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_drivers.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import Drivers # Importe o modelo Drivers
import json
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa dados de pilotos da API Ergast F1 e popula o banco de dados. Apenas novos pilotos são adicionados.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar os dados de pilotos. Padrão é o ano corrente.'
        )

    def handle(self, *args, **options):
        # Determina o ano a ser usado
        year = options['year'] if options['year'] is not None else datetime.now().year
        api_url = f"https://api.jolpi.ca/ergast/f1/{year}/drivers/" # URL da API de Pilotos

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação de dados de pilotos para o ano {year} de {api_url}...'))

        new_drivers_count = 0
        skipped_existing_drivers_count = 0
        error_drivers_count = 0

        # Obter o último driverid existente ANTES do loop principal.
        last_driver_global = Drivers.objects.order_by('-driverid').first()
        next_driver_id_counter = 1 if not last_driver_global or last_driver_global.driverid is None else last_driver_global.driverid + 1

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            if 'MRData' in data and 'DriverTable' in data['MRData'] and 'Drivers' in data['MRData']['DriverTable']:
                drivers_data = data['MRData']['DriverTable']['Drivers']

                for driver_json in drivers_data:
                    driver_ref_from_api = driver_json['driverId'] # Este é o valor para 'driverref' no modelo

                    try:
                        with transaction.atomic():
                            # 1. Verificar se o piloto já existe (usando driverref como chave de unicidade)
                            if Drivers.objects.filter(driverref=driver_ref_from_api).exists():
                                skipped_existing_drivers_count += 1
                                self.stdout.write(self.style.WARNING(f'Piloto EXISTENTE (Ignorado): {driver_json.get("givenName", "")} {driver_json.get("familyName", "")} (Ref: {driver_ref_from_api})'))
                                continue # Pula para o próximo piloto

                            # 2. Preparar dados do piloto para criação
                            driver_insert_data = {
                                'driverid': next_driver_id_counter, # Atribui o ID sequencial aqui
                                'driverref': driver_ref_from_api,
                                'number': driver_json.get('permanentNumber'), # Pode ser null
                                'code': driver_json.get('code'), # Pode ser null
                                'forename': driver_json.get('givenName'),
                                'surname': driver_json.get('familyName'),
                                'dob': driver_json.get('dateOfBirth'),
                                'nationality': driver_json.get('nationality'),
                                'url': driver_json.get('url'),
                            }

                            # 3. Criar o novo piloto
                            driver = Drivers.objects.create(**driver_insert_data)
                            new_drivers_count += 1
                            self.stdout.write(self.style.SUCCESS(f'Adicionado NOVO Piloto: {driver.forename} {driver.surname} (Ref: {driver.driverref}, ID: {driver.driverid})'))
                            next_driver_id_counter += 1 # Incrementa para o próximo novo piloto

                    except IntegrityError as e:
                        # Este erro pode ocorrer se houver um piloto duplicado inserido por outra transação
                        # ou se houver um driverid duplicado por algum motivo, embora o exists() tente evitar.
                        skipped_existing_drivers_count += 1
                        self.stderr.write(self.style.WARNING(f'Erro de Integridade (provável duplicidade) para Piloto {driver_json.get("driverId", "N/A")}: {e}'))
                    except Exception as e:
                        error_drivers_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar piloto {driver_json.get("driverId", "N/A")}: {e}'))

            else:
                self.stderr.write(self.style.ERROR('Estrutura JSON inesperada para pilotos. Verifique o formato da API.'))
                error_drivers_count = 1

            # --- Resumo final ---
            self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Pilotos ---'))
            self.stdout.write(self.style.SUCCESS(f'Pilotos Novos Inseridos: {new_drivers_count}'))
            self.stdout.write(self.style.WARNING(f'Pilotos Existentes (Ignorados): {skipped_existing_drivers_count}'))
            self.stdout.write(self.style.ERROR(f'Pilotos com Erros: {error_drivers_count}'))
            self.stdout.write(self.style.SUCCESS('Importação de pilotos concluída!'))

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Erro ao conectar ou obter dados da API Ergast: {e}'))
            self.stdout.write(self.style.ERROR('Importação de pilotos FALHOU devido a erro de conexão/API.'))
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da API: {e}'))
            self.stdout.write(self.style.ERROR('Importação de pilotos FALHOU devido a erro de formato JSON.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a importação geral: {e}'))
            self.stdout.write(self.style.ERROR('Importação de pilotos FALHOU devido a erro inesperado.'))