# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_constructors.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import Constructors
import json
import os
from datetime import datetime 

class Command(BaseCommand):
    help = 'Importa dados de construtores da API Ergast F1 e popula o banco de dados. Apenas novos construtores são adicionados.'

    def add_arguments(self, parser):
        # Adiciona o argumento --year (opcional)
        parser.add_argument(
            '--year',
            type=int,
            help='Opcional. O ano para o qual importar os dados de construtores. Padrão é o ano corrente.'
        )

    def handle(self, *args, **options):
        # Se --year foi fornecido, usa esse ano. Caso contrário, usa o ano corrente.
        year = options['year'] if options['year'] is not None else datetime.now().year

        # Constrói a URL da API com o ano dinâmico
        api_url = f"https://api.jolpi.ca/ergast/f1/{year}/constructors/"

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação de dados de construtores para o ano {year} de {api_url}...'))

        new_constructors_count = 0
        skipped_existing_constructors_count = 0
        error_constructors_count = 0
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            if 'MRData' in data and 'ConstructorTable' in data['MRData'] and 'Constructors' in data['MRData']['ConstructorTable']:
                constructors_data = data['MRData']['ConstructorTable']['Constructors']

                last_constructor = Constructors.objects.order_by('-constructorid').first() # CORRIGIDO: Usando Constructors
                next_constructor_id_counter = 1 if not last_constructor or last_constructor.constructorid is None else last_constructor.constructorid + 1

                for constructor_json in constructors_data:
                    constructor_ref_from_api = constructor_json['constructorId']

                    try:
                        with transaction.atomic():
                            if Constructors.objects.filter(constructorref=constructor_ref_from_api).exists():
                                skipped_existing_constructors_count += 1
                                self.stdout.write(self.style.WARNING(f'Construtor EXISTENTE (Ignorado): {constructor_json["name"]} (Ref: {constructor_ref_from_api})'))
                                continue

                            constructor_data = {
                                'constructorid': next_constructor_id_counter,
                                'constructorref': constructor_ref_from_api,
                                'name': constructor_json['name'],
                                'nationality': constructor_json.get('nationality'),
                                'url': constructor_json.get('url'),
                            }

                            constructor = Constructors.objects.create(**constructor_data)
                            new_constructors_count += 1
                            self.stdout.write(self.style.SUCCESS(f'Adicionado NOVO Construtor: {constructor.name} (Ref: {constructor.constructorref}, ID: {constructor.constructorid})'))
                            next_constructor_id_counter += 1

                    except IntegrityError as e:
                        skipped_existing_constructors_count += 1
                        self.stderr.write(self.style.WARNING(f'Erro de Integridade (provável duplicidade) para {constructor_json.get("name", "N/A")}: {e}'))
                    except Exception as e:
                        error_constructors_count += 1
                        self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar construtor {constructor_json.get("constructorId", "N/A")}: {e}'))

            else:
                self.stderr.write(self.style.ERROR('Estrutura JSON inesperada para construtores. Verifique o formato da API.'))
                error_constructors_count = len(constructors_data) if 'MRData' in data and 'ConstructorTable' in data['MRData'] else 0

            self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Construtores ---'))
            self.stdout.write(self.style.SUCCESS(f'Construtores Novos Inseridos: {new_constructors_count}'))
            self.stdout.write(self.style.WARNING(f'Construtores Existentes (Ignorados): {skipped_existing_constructors_count}'))
            self.stdout.write(self.style.ERROR(f'Construtores com Erros: {error_constructors_count}'))
            self.stdout.write(self.style.SUCCESS('Importação de construtores concluída!'))

        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Erro ao conectar ou obter dados da API Ergast: {e}'))
            self.stdout.write(self.style.ERROR('Importação de construtores FALHOU devido a erro de conexão/API.'))
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da API: {e}'))
            self.stdout.write(self.style.ERROR('Importação de construtores FALHOU devido a erro de formato JSON.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a importação geral: {e}'))
            self.stdout.write(self.style.ERROR('Importação de construtores FALHOU devido a erro inesperado.'))