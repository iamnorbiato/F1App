# Use uma imagem oficial do Python como base
FROM python:3.10-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de requisitos para cache do pip
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Expõe a porta que o Django usará (padrão é 8000)
EXPOSE 8000

# Comando para iniciar o servidor Django (este será ajustado depois com Gunicorn)
# Por enquanto, vamos manter simples para testes
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]