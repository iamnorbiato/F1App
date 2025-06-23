#!/bin/bash

# Lista de comandos Django management para executar, na ordem especificada
COMMANDS=(
    "import_f1_circuits"
    "import_f1_races"
    "import_f1_constructors"
    "import_f1_season"
    "import_f1_constructor_standings"
    "import_f1_drivers"
    "import_f1_driver_standings"
    "import_f1_results"
    "import_f1_sprint_results"
    "import_f1_qualifying"
    "import_f1_pit_stops"
    "import_f1_lap_times"
)

# Datas agendadas para a execução dos imports no formato YYYY-MM-DD
# Assumindo o ano corrente como 2025 para as datas fornecidas.
SCHEDULED_DATES=(
    "2025-06-30"
    "2025-07-07"
    "2025-07-28"
    "2025-08-04"
    "2025-09-01"
    "2025-09-08"
    "2025-09-22"
    "2025-10-06"
    "2025-10-19"
    "2025-10-27"
    "2025-11-10"
    "2025-11-23"
    "2025-12-01"
    "2025-12-08"
)

# Função para executar um único comando Django management
run_django_command() {
    local cmd="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Executando: python manage.py $cmd"
    # Assumimos que o diretório de trabalho do pod CronJob será /app,
    # onde o manage.py está.
    python manage.py "$cmd"
    return $? # Retorna o status de saída do comando
}

# Função principal para orquestrar a execução com lógica de retry
main() {
    local current_date=$(date '+%Y-%m-%d')
    local is_scheduled_date=false

    # 1. Verifica se a data atual é uma das datas agendadas
    for s_date in "${SCHEDULED_DATES[@]}"; do
        if [[ "$current_date" == "$s_date" ]]; then
            is_scheduled_date=true
            break
        fi
    done

    if [ "$is_scheduled_date" = false ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Hoje ($current_date) não é uma data agendada para importação de dados. Saindo."
        exit 0 # Sai com sucesso se não for uma data agendada
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') - Hoje ($current_date) é uma data agendada para importação de dados. Iniciando processo."

    local current_tasks=("${COMMANDS[@]}")
    local all_tasks_succeeded=false
    local max_passes=5 # Número máximo de "passes" pela lista de comandos para permitir retries

    for (( pass_num=1; pass_num<=$max_passes; pass_num++ )); do
        echo "$(date '+%Y-%m-%d %H:%M:%S') - --- Passagem $pass_num de $max_passes ---"
        local failed_in_pass=() # Lista de tarefas que falharam nesta passagem

        # Se não há mais tarefas para rodar, saímos
        if [ ${#current_tasks[@]} -eq 0 ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Todas as tarefas foram concluídas com sucesso em passagens anteriores."
            all_tasks_succeeded=true
            break
        fi

        # Executa as tarefas pendentes nesta passagem
        for task in "${current_tasks[@]}"; do
            if run_django_command "$task"; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') - SUCESSO: $task"
            else
                echo "$(date '+%Y-%m-%d %H:%M:%S') - FALHA: $task. Será tentado novamente na próxima passagem."
                failed_in_pass+=("$task") # Adiciona à lista de falhas para re-tentativa
            fi
        done

        # Atualiza a lista de tarefas para a próxima passagem com as que falharam
        current_tasks=("${failed_in_pass[@]}")

        if [ ${#failed_in_pass[@]} -eq 0 ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Todas as tarefas foram concluídas com sucesso nesta passagem."
            all_tasks_succeeded=true
            break # Sai do loop principal se não houver falhas
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - --- ${#failed_in_pass[@]} tarefas falharam nesta passagem. Restantes para re-tentativa: ${current_tasks[@]} ---"
            sleep 10 # Pequeno delay antes da próxima passagem para evitar loop rápido
        fi
    done

    # Verifica o status geral e sai
    if [ "$all_tasks_succeeded" = true ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Resumo: Todas as tarefas agendadas concluídas com sucesso."
        exit 0 # Indica sucesso para o CronJob
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Resumo: ATENÇÃO! Algumas tarefas não foram concluídas após $max_passes passagens: ${current_tasks[@]}"
        exit 1 # Indica falha para o CronJob
    fi
}

# Executa a função principal
main