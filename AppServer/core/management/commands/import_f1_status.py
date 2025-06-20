# G:\Learning\33Tier_F1App\AppServer\core\management\commands\import_f1_status.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import Status # Importe o modelo Status
import json
import os

class Command(BaseCommand):
    help = 'Importa dados de status da API Ergast F1 e popula o banco de dados. Agora com paginação para trazer todos os registros.'

    # Esta API de Status retorna todos os status, então não precisamos de um argumento --year aqui.
    # A URL base é fixa.

    def handle(self, *args, **options):
        base_api_url = "https://api.jolpi.ca/ergast/f1/status/" # URL base da API de Status

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação paginada de dados de status de {base_api_url}...'))

        new_status_count = 0
        skipped_existing_status_count = 0
        error_status_count = 0

        # Lógica de Paginação
        all_status_data = []
        limit = 30 # Limite padrão da API Ergast
        offset = 0
        total_records = None # Será atualizado após a primeira requisição

        while True:
            # Constrói a URL com os parâmetros de paginação
            api_url = f"{base_api_url}?limit={limit}&offset={offset}"
            self.stdout.write(self.style.SUCCESS(f"  Fetching page: {api_url}")) # Mensagem de progresso em verde

            try:
                response = requests.get(api_url)
                response.raise_for_status() # Lança exceção para erros HTTP
                data = response.json()

                mr_data = data.get('MRData', {})
                if total_records is None:
                    total_records = int(mr_data.get('total', 0))
                    self.stdout.write(self.style.SUCCESS(f"  Total de status a importar: {total_records}"))

                status_on_page = mr_data.get('StatusTable', {}).get('Status', [])
                all_status_data.extend(status_on_page)

                if not status_on_page or (offset + len(status_on_page)) >= total_records:
                    break # Todos os registros foram baixados ou não há mais páginas
                else:
                    offset += limit # Prepara para a próxima página

            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f'Erro de conexão/API ao buscar página {api_url}: {e}'))
                error_status_count = total_records if total_records is not None else 0
                break
            except json.JSONDecodeError as e:
                self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da página {api_url}: {e}'))
                error_status_count = total_records if total_records is not None else 0
                break
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a paginação para {api_url}: {e}'))
                error_status_count = total_records if total_records is not None else 0
                break

        # Processamento dos dados APÓS a coleta de todas as páginas
        self.stdout.write(self.style.SUCCESS(f'\nIniciando processamento de {len(all_status_data)} status coletados...'))

        # Obter o último statusid existente ANTES do loop de processamento.
        last_status_global = Status.objects.order_by('-statusid').first()
        next_status_id_counter = 1 if not last_status_global or last_status_global.statusid is None else last_status_global.statusid + 1


        for status_json in all_status_data: # Agora itera sobre TODOS os dados coletados
            # A API de Status tem 'statusId' (int) e 'status' (string)
            status_id_from_api = int(status_json['statusId']) # ID numérico do status da API
            status_text_from_api = status_json['status']      # Texto do status da API (ex: "Finished", "Did not start")

            try:
                with transaction.atomic():
                    # Usamos o 'statusId' da API como identificador único para buscar ou criar
                    existing_status = Status.objects.filter(statusid=status_id_from_api).first()

                    if existing_status:
                        # Se o status existe, podemos atualizar o texto se ele mudou.
                        # DDL: statusid int4 NOT NULL, status varchar(50) NULL
                        if existing_status.status != status_text_from_api:
                            existing_status.status = status_text_from_api
                            existing_status.save()
                            skipped_existing_status_count += 1 # Contar como existente/atualizado
                            self.stdout.write(self.style.WARNING(f'Status EXISTENTE (Atualizado): {status_text_from_api} (ID: {status_id_from_api})'))
                        else:
                            skipped_existing_status_count += 1 # Contar como existente
                            # self.stdout.write(self.style.WARNING(f'Status EXISTENTE (Ignorado): {status_text_from_api} (ID: {status_id_from_api})'))
                    else:
                        # Se o status não existe, cria um novo
                        status_data = {
                            'statusid': status_id_from_api, # Usamos o statusId da API diretamente como PK
                            'status': status_text_from_api,
                        }
                        status = Status.objects.create(**status_data)
                        new_status_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Adicionado NOVO Status: {status.status} (ID: {status.statusid})'))
                        # Não incrementamos next_status_id_counter aqui porque statusid vem direto da API e é a PK.
                        # É um caso especial comparado a raceid, constructorid, etc.

            except IntegrityError as e:
                skipped_existing_status_count += 1 # Conta como existente, caso haja concorrência
                self.stderr.write(self.style.WARNING(f'Erro de Integridade (provável duplicidade) para Status {status_id_from_api}: {e}'))
            except Exception as e:
                error_status_count += 1
                self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar status {status_id_from_api}: {e}'))

        self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Status ---'))
        self.stdout.write(self.style.SUCCESS(f'Status Novos Inseridos: {new_status_count}'))
        self.stdout.write(self.style.WARNING(f'Status Existentes (Ignorados/Atualizados): {skipped_existing_status_count}'))
        self.stdout.write(self.style.ERROR(f'Status com Erros: {error_status_count}'))
        self.stdout.write(self.style.SUCCESS('Importação de status concluída!'))