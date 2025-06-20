# AppServer/f1app_project/core/views.py
from django.http import JsonResponse
from django.db import connection

def animated_race_chart_data(request):
    # SQL para obter todas as vitórias, ordenadas cronologicamente
    # Incluímos raceid para garantir uma ordem consistente por corrida
    query = """
    SELECT
        dr.driverref,
        dr.forename || ' ' || dr.surname AS driver_name,
        ra.year,
        ra.name AS race_name, -- Nome da corrida para referência
        ra.round AS race_round, -- Rodada da corrida para ordem
        ra.date AS race_date -- Data da corrida para ordem
    FROM
        results re
    JOIN
        races ra ON re.raceid = ra.raceid
    JOIN
        drivers dr ON re.driverid = dr.driverid
    WHERE
        re.positionorder = 1
    ORDER BY
        ra.year, ra.round, ra.date, re.raceid
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        # Fetch all rows as a list of dictionaries for easier processing
        columns = [col[0] for col in cursor.description]
        winners = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Processar os dados para criar os "frames" da animação
    animated_data = []
    driver_wins = {} # Guarda as vitórias acumuladas por piloto
    previous_time_step = None # Usaremos para agrupar por corrida/data

    for winner_event in winners:
        driver_ref = winner_event['driverref']
        driver_name = winner_event['driver_name']
        race_info = f"{winner_event['race_name']} ({winner_event['year']})"
        # Usar uma combinação de ano e rodada para garantir a ordem e agrupar por corrida
        current_time_step = f"{winner_event['year']}-R{winner_event['race_round']}"

        # Se mudamos para uma nova corrida/ponto no tempo, salve o frame anterior
        if previous_time_step and current_time_step != previous_time_step:
            # Cria uma cópia das vitórias acumuladas para este frame
            # Isso é importante para que o estado do frame não mude à medida que driver_wins é atualizado
            frame_drivers = [{"driverRef": dr_ref, "driverName": dr_info[0], "wins": dr_info[1]}
                             for dr_ref, dr_info in driver_wins.items()]

            # Ordena os pilotos por vitórias acumuladas para este frame
            sorted_drivers_for_frame = sorted(
                frame_drivers,
                key=lambda x: x['wins'],
                reverse=True
            )
            animated_data.append({
                "timeStep": previous_time_step,
                "raceInfo": race_info, # Info da corrida que iniciou este frame
                "drivers": sorted_drivers_for_frame # Não limitar aqui, o frontend pode fazer isso
            })
            # Não há necessidade de re-usar o estado, pois estamos copiando para o frame

        # Atualiza as vitórias acumuladas do piloto atual
        # driver_wins armazena (driver_name, wins_count)
        driver_wins[driver_ref] = (driver_name, driver_wins.get(driver_ref, (driver_name, 0))[1] + 1)
        previous_time_step = current_time_step

    # Adiciona o último frame após o loop (para garantir que a última corrida seja incluída)
    if driver_wins:
        frame_drivers_final = [{"driverRef": dr_ref, "driverName": dr_info[0], "wins": dr_info[1]}
                               for dr_ref, dr_info in driver_wins.items()]
        sorted_drivers_for_final_frame = sorted(
            frame_drivers_final,
            key=lambda x: x['wins'],
            reverse=True
        )
        animated_data.append({
            "timeStep": previous_time_step,
            "raceInfo": winners[-1]['race_name'], # Apenas para o último frame
            "drivers": sorted_drivers_for_final_frame
        })


    return JsonResponse(animated_data, safe=False)

def hello_world(request):
    # Esta é a API simples que já tínhamos planejado para o frontend
    return JsonResponse({"message": "Olá do Backend Django no Kubernetes!"})