# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_circuits.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import Circuit # Importe o modelo Circuit
import json
import os

class Command(BaseCommand):
    help = 'Importa dados de circuitos da API Ergast F1 e popula o banco de dados. Agora com paginação para trazer todos os registros.'

    def handle(self, *args, **options):
        base_api_url = "https://api.jolpi.ca/ergast/f1/circuits/" # URL base sem offset/limit

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação paginada de dados de circuitos de {base_api_url}...'))

        new_circuits_count = 0
        existing_circuits_count = 0
        error_circuits_count = 0

        # Lógica de Paginação
        all_circuits_data = []
        limit = 30 # Limite padrão da API Ergast (pode variar, mas 30 é comum)
        offset = 0
        total_records = None # Será atualizado após a primeira requisição

        while True:
            # Constrói a URL com os parâmetros de paginação
            api_url = f"{base_api_url}?limit={limit}&offset={offset}"
            # MUDANÇA AQUI: De self.style.NOTICE para self.style.SUCCESS
            self.stdout.write(self.style.SUCCESS(f"  Fetching page: {api_url}")) # Mensagem de progresso em verde

            try:
                response = requests.get(api_url)
                response.raise_for_status() # Lança exceção para erros HTTP
                data = response.json()

                mr_data = data.get('MRData', {})
                # Atualiza o total de registros após a primeira requisição
                if total_records is None:
                    total_records = int(mr_data.get('total', 0))
                    self.stdout.write(self.style.SUCCESS(f"  Total de circuitos a importar: {total_records}"))

                # Extrai os circuitos da página atual
                circuits_on_page = mr_data.get('CircuitTable', {}).get('Circuits', [])
                all_circuits_data.extend(circuits_on_page)

                # Verifica se há mais páginas
                if (offset + len(circuits_on_page)) >= total_records:
                    break # Todos os registros foram baixados
                else:
                    offset += limit # Prepara para a próxima página

            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f'Erro de conexão/API ao buscar página {api_url}: {e}'))
                error_circuits_count = total_records if total_records is not None else 0 # Marca tudo como erro se a busca inicial falhar
                break # Sai do loop em caso de erro de API
            except json.JSONDecodeError as e:
                self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da página {api_url}: {e}'))
                error_circuits_count = total_records if total_records is not None else 0
                break # Sai do loop
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a paginação para {api_url}: {e}'))
                error_circuits_count = total_records if total_records is not None else 0
                break

        # Processamento dos dados APÓS a coleta de todas as páginas
        self.stdout.write(self.style.SUCCESS(f'\nIniciando processamento de {len(all_circuits_data)} circuitos coletados...'))

        # Obter o último circuitid existente ANTES do loop de processamento.
        last_circuit_global = Circuit.objects.order_by('-circuitid').first()
        next_circuit_id_counter = 1 if not last_circuit_global or last_circuit_global.circuitid is None else last_circuit_global.circuitid + 1

        for circuit_json in all_circuits_data: # Agora itera sobre TODOS os dados coletados
            circuit_ref_from_api = circuit_json['circuitId']

            try:
                with transaction.atomic():
                    existing_circuit = Circuit.objects.filter(circuitRef=circuit_ref_from_api).first()

                    if existing_circuit:
                        existing_circuits_count += 1
                        # self.stdout.write(self.style.WARNING(f'Circuito EXISTENTE (Ignorado): {circuit_json["circuitName"]} (Ref: {circuit_ref_from_api})'))
                    else:
                        circuit_data = {
                            'circuitid': next_circuit_id_counter,
                            'circuitRef': circuit_ref_from_api,
                            'name': circuit_json['circuitName'],
                            'location': circuit_json['Location'].get('locality'),
                            'country': circuit_json['Location'].get('country'),
                            'lat': float(circuit_json['Location']['lat']),
                            'lng': float(circuit_json['Location']['long']),
                            'alt': int(circuit_json['Location'].get('alt')) if circuit_json['Location'].get('alt') else None,
                            'url': circuit_json['url']
                        }
                        circuit = Circuit.objects.create(**circuit_data)
                        new_circuits_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Criado NOVO Circuito: {circuit.name} (Ref: {circuit.circuitRef}, ID: {circuit.circuitid})'))
                        next_circuit_id_counter += 1

            except IntegrityError:
                existing_circuits_count += 1 # Conta como existente, caso haja concorrência ou PK duplicada
                self.stdout.write(self.style.WARNING(f'Tentativa de criar circuito EXISTENTE (Ignorado por unicidade): {circuit_json["circuitName"]} (Ref: {circuit_ref_from_api})'))
            except Exception as e:
                error_circuits_count += 1
                self.stderr.write(self.style.ERROR(f'Erro ao processar circuito {circuit_json.get("circuitId", "N/A")}: {e}'))

        self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Circuitos ---'))
        self.stdout.write(self.style.SUCCESS(f'Circuitos Novos Inseridos: {new_circuits_count}'))
        self.stdout.write(self.style.WARNING(f'Circuitos Existentes (Ignorados): {existing_circuits_count}'))
        self.stdout.write(self.style.ERROR(f'Circuitos com Erros: {error_circuits_count}'))
        self.stdout.write(self.style.SUCCESS('Importação de circuitos concluída!'))