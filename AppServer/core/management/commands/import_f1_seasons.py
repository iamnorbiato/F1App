# G:\Learning\3Tier_F1App\AppServer\core\management\commands\import_f1_seasons.py

import requests
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from core.models import Seasons # Importe o modelo Seasons
import json
import os

class Command(BaseCommand):
    help = 'Importa dados de temporadas da API Ergast F1 e popula o banco de dados. Agora com paginação para trazer todos os registros.'

    # Esta API de Seasons retorna todas as temporadas, então não precisamos de um argumento --year aqui na url da API.
    # removemos add_arguments para esta API.

    def handle(self, *args, **options):
        base_api_url = "https://api.jolpi.ca/ergast/f1/seasons/" # URL base sem offset/limit

        self.stdout.write(self.style.SUCCESS(f'Iniciando importação paginada de dados de temporadas de {base_api_url}...'))

        new_seasons_count = 0
        skipped_existing_seasons_count = 0
        error_seasons_count = 0

        # Lógica de Paginação
        all_seasons_data = []
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
                    self.stdout.write(self.style.SUCCESS(f"  Total de temporadas a importar: {total_records}"))

                seasons_on_page = mr_data.get('SeasonTable', {}).get('Seasons', [])
                all_seasons_data.extend(seasons_on_page)

                if (offset + len(seasons_on_page)) >= total_records:
                    break # Todos os registros foram baixados
                else:
                    offset += limit # Prepara para a próxima página

            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(f'Erro de conexão/API ao buscar página {api_url}: {e}'))
                error_seasons_count = total_records if total_records is not None else 0
                break
            except json.JSONDecodeError as e:
                self.stderr.write(self.style.ERROR(f'Erro ao decodificar JSON da página {api_url}: {e}'))
                error_seasons_count = total_records if total_records is not None else 0
                break
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Ocorreu um erro inesperado durante a paginação para {api_url}: {e}'))
                error_seasons_count = total_records if total_records is not None else 0
                break

        # Processamento dos dados APÓS a coleta de todas as páginas
        self.stdout.write(self.style.SUCCESS(f'\nIniciando processamento de {len(all_seasons_data)} temporadas coletadas...'))

        for season_json in all_seasons_data: # Agora itera sobre TODOS os dados coletados
            season_year = int(season_json['season'])

            try:
                with transaction.atomic():
                    if Seasons.objects.filter(year=season_year).exists():
                        skipped_existing_seasons_count += 1
                        # self.stdout.write(self.style.WARNING(f'Temporada EXISTENTE (Ignorada): {season_year}'))
                    else:
                        season_insert_data = {
                            'year': season_year,
                            'url': season_json['url'],
                        }
                        season = Seasons.objects.create(**season_insert_data)
                        new_seasons_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Adicionada NOVA Temporada: {season.year}'))

            except IntegrityError as e:
                skipped_existing_seasons_count += 1
                self.stderr.write(self.style.WARNING(f'Erro de Integridade (provável duplicidade de ano) para Temporada {season_year}: {e}'))
            except Exception as e:
                error_seasons_count += 1
                self.stderr.write(self.style.ERROR(f'Erro inesperado ao processar temporada {season_year}: {e}'))

        self.stdout.write(self.style.SUCCESS('\n--- Resumo da Importação de Temporadas ---'))
        self.stdout.write(self.style.SUCCESS(f'Temporadas Novas Inseridas: {new_seasons_count}'))
        self.stdout.write(self.style.WARNING(f'Temporadas Existentes (Ignoradas): {skipped_existing_seasons_count}'))
        self.stdout.write(self.style.ERROR(f'Temporadas com Erros: {error_seasons_count}'))
        self.stdout.write(self.style.SUCCESS('Importação de temporadas concluída!'))