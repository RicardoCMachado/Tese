import csv
import math
from pickle import TRUE
import re
import subprocess
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from geopy.geocoders import Nominatim
from polycircles import polycircles
import requests
from gtts import gTTS
import os
import random
import socket
import pandas as pd
import simplekml
from shapely.geometry import Point, Polygon
from pydub import AudioSegment
import time
from time import sleep


BASE_DIR = Path(__file__).resolve().parent
ROADS_CSV_CANDIDATES = [
    BASE_DIR / "roads_portugal.csv",
    BASE_DIR.parent / "firetec-multithread" / "data" / "roads_portugal.csv",
]
ROAD_GRID_CELL_DEGREES = 0.05
INITIAL_ROAD_RADIUS_M = 2000
ROAD_RADIUS_INCREMENT_M = 500
MAX_ROAD_RADIUS_M = 6000
MAX_ROADS_RETURNED = 5
DEFAULT_SWITCH_PORTS = [8080]  # Ex.: [8081] ou [8081, 8080]
LOCAL_BIND_IP = None  # Ex.: "192.168.0.20" se quiseres forcar o IP local
CONNECTION_TIMEOUT_S = 5
RETRY_ATTEMPTS = 3
RETRY_DELAY_S = 0.5
# Protocolo confirmado em laboratorio em 27/04/2026:
# - switch funcional: 192.168.0.22
# - porta funcional: 8080
# - payload: WAV + b"PS=FIRETEC1;" + b"PI=8400;" + b"AF=<freqs>;"
# - WAV a 32000 Hz com sample width = 1


def resolve_roads_csv_path():
    for candidate in ROADS_CSV_CANDIDATES:
        if candidate.exists():
            return candidate
    return ROADS_CSV_CANDIDATES[-1]


def cell_for(latitude, longitude):
    return (
        math.floor(latitude / ROAD_GRID_CELL_DEGREES),
        math.floor(longitude / ROAD_GRID_CELL_DEGREES)
    )


def distance_meters(lat1, lon1, lat2, lon2):
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2 +
        math.cos(phi1) * math.cos(phi2) *
        math.sin(delta_lambda / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def split_refs(ref):
    return [
        item.strip()
        for item in re.split(r"[;,/]", ref or "")
        if item.strip()
    ]


def first_matching_ref(refs, pattern):
    for ref in refs:
        if re.match(pattern, ref, flags=re.IGNORECASE):
            return ref
    return ""


def compact_ref(ref):
    return re.sub(r"\s+", "", ref.strip()).upper()


def format_road_label(ref, name, highway):
    refs = split_refs(ref)
    motorway_ref = first_matching_ref(refs, r"^A[\s.-]*\d+")
    national_ref = first_matching_ref(refs, r"^(EN|E\.N\.)[\s.-]*\d+")
    main_itinerary_ref = first_matching_ref(refs, r"^IP[\s.-]*\d+")
    complementary_itinerary_ref = first_matching_ref(refs, r"^IC[\s.-]*\d+")

    if motorway_ref:
        return compact_ref(motorway_ref)

    if national_ref:
        return compact_ref(national_ref).replace("E.N.", "EN")

    if main_itinerary_ref:
        return compact_ref(main_itinerary_ref)

    if complementary_itinerary_ref:
        return compact_ref(complementary_itinerary_ref)

    if name:
        return name

    return compact_ref(ref) if ref else ""


def road_group_key(point):
    if point["raw_ref"]:
        return f"ref:{compact_ref(point['raw_ref'])}"
    return f"name:{point['raw_name'].strip().lower()}"


def parse_road_point(row):
    ref = (row.get("ref") or "").strip()
    name = (row.get("name") or "").strip()
    highway = row.get("highway") or "unknown"

    if not ref and not name:
        return None

    try:
        latitude = float(row.get("latitude") or row.get("lat"))
        longitude = float(row.get("longitude") or row.get("lon"))
    except (TypeError, ValueError):
        return None

    return {
        "road_id": row.get("road_id") or row.get("id") or ref or name,
        "raw_ref": ref,
        "raw_name": name,
        "highway": highway,
        "latitude": latitude,
        "longitude": longitude,
    }


def load_road_points(path):
    road_points = []
    grid_index = {}

    if not path.exists():
        print(f"[!] Ficheiro de estradas nao encontrado: {path}")
        return road_points, grid_index

    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            point = parse_road_point(row)
            if point is None:
                continue

            index = len(road_points)
            road_points.append(point)
            grid_index.setdefault(
                cell_for(point["latitude"], point["longitude"]),
                []
            ).append(index)

    print(f"[+] Carregados {len(road_points)} pontos de estradas locais de {path}")
    return road_points, grid_index


def candidate_road_points(latitude, longitude, radius_m, road_points, grid_index):
    lat_radius = radius_m / 111_320
    cos_lat = max(abs(math.cos(math.radians(latitude))), 0.01)
    lon_radius = radius_m / (111_320 * cos_lat)

    min_cell = cell_for(latitude - lat_radius, longitude - lon_radius)
    max_cell = cell_for(latitude + lat_radius, longitude + lon_radius)

    points = []
    for lat_cell in range(min_cell[0], max_cell[0] + 1):
        for lon_cell in range(min_cell[1], max_cell[1] + 1):
            for index in grid_index.get((lat_cell, lon_cell), []):
                points.append(road_points[index])

    return points


def find_csv_roads_in_radius(latitude, longitude, radius_m, road_points, grid_index):
    candidates = candidate_road_points(
        latitude,
        longitude,
        radius_m,
        road_points,
        grid_index
    )
    nearest_by_road = {}

    for point in candidates:
        distance = distance_meters(
            latitude,
            longitude,
            point["latitude"],
            point["longitude"]
        )
        if distance > radius_m:
            continue

        key = road_group_key(point)
        current = nearest_by_road.setdefault(key, {
            "distance": float("inf"),
            "name_distance": float("inf"),
            "ref": point["raw_ref"],
            "name": point["raw_name"],
            "nearest_name": "",
            "highway": point["highway"],
        })

        if distance < current["distance"]:
            current["distance"] = distance
            current["ref"] = point["raw_ref"]
            current["name"] = point["raw_name"]
            current["highway"] = point["highway"]

        if point["raw_name"] and distance < current["name_distance"]:
            current["name_distance"] = distance
            current["nearest_name"] = point["raw_name"]

    ordered = sorted(nearest_by_road.values(), key=lambda item: item["distance"])
    roads = []
    seen = set()

    for item in ordered:
        label = format_road_label(
            item["ref"],
            item["nearest_name"] or item["name"],
            item["highway"]
        )
        if label and label not in seen:
            roads.append(label)
            seen.add(label)

    return roads[:MAX_ROADS_RETURNED]


def find_nearby_roads(latitude, longitude, road_points, grid_index):
    if not road_points:
        return []

    search_radius = INITIAL_ROAD_RADIUS_M
    roads = []

    while search_radius <= MAX_ROAD_RADIUS_M:
        roads = find_csv_roads_in_radius(
            latitude,
            longitude,
            search_radius,
            road_points,
            grid_index
        )
        if roads:
            break

        search_radius += ROAD_RADIUS_INCREMENT_M

    return roads


ROADS_CSV_PATH = resolve_roads_csv_path()
ROAD_POINTS, ROAD_GRID_INDEX = load_road_points(ROADS_CSV_PATH)
SWITCH_TARGETS = [
    {"host": "192.168.0.22", "ports": list(DEFAULT_SWITCH_PORTS)},
    {"host": "192.168.0.21", "ports": list(DEFAULT_SWITCH_PORTS)},
]


def transmit_to_firetec_switch(target, payload):
    host = target["host"]
    ports = target.get("ports") or list(DEFAULT_SWITCH_PORTS)
    attempts_total = 0
    start_time = time.time()
    last_error = "sem detalhe"

    for port in ports:
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            attempts_total += 1
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CONNECTION_TIMEOUT_S)

            try:
                if LOCAL_BIND_IP:
                    sock.bind((LOCAL_BIND_IP, 0))

                print(f"[++] A ligar a {host}:{port} (tentativa {attempt}/{RETRY_ATTEMPTS})")
                sock.connect((host, port))
                print(f"[+] Ligacao estabelecida -> {host}:{port}")

                print("[++] Enviando dados para o Firetec Switch")
                sock.sendall(payload)

                duration = time.time() - start_time
                print(f"[+] Envio concluido para {host}:{port} em {duration:.2f}s")
                return {
                    "host": host,
                    "port": port,
                    "success": True,
                    "attempts": attempts_total,
                    "duration": duration,
                    "error": None,
                }

            except socket.timeout:
                last_error = f"Timeout ao conectar a {host}:{port}"
                print(f"[!] {last_error}")
            except socket.error as exc:
                last_error = f"Erro de socket em {host}:{port}: {exc}"
                print(f"[!] {last_error}")
            finally:
                try:
                    sock.close()
                except Exception:
                    pass

            if attempt < RETRY_ATTEMPTS:
                sleep(RETRY_DELAY_S)

    duration = time.time() - start_time
    print(f"[!] Switch {host} falhou apos {attempts_total} tentativas")
    return {
        "host": host,
        "port": None,
        "success": False,
        "attempts": attempts_total,
        "duration": duration,
        "error": last_error,
    }


# criar objeto kml
kml = simplekml.Kml()
## READ FILE CALL 123.CSV (Tem a informação das antenas de rádio)
nome_file="123.csv"
# reading CSV file
# ler ficheiro csv que contém info das estaçoes de rádio
data = pd.read_csv(nome_file)

# reading CSV file e put date in vars
long_ant=data["Longitude Corrigida"].tolist()
lat_ant=data["Latitude Corrigida"].tolist()
freq_trans=data["Frequência [MHz]"].tolist()
PS_est=data["PS"].tolist()
PI_est=data["PI"].tolist()
raio_trans=data["Raio [Km]"].tolist()
data = [[long_ant[i],lat_ant[i],freq_trans[i],PS_est[i],PI_est[i],raio_trans[i]] for i in range(len(long_ant))] 

## Variaveis para definir ps e pi
ps_inc = 0
pi_inc = 0

## Add to a kml file the Antena's places with information previous extracted from csv file
for row in data:
    new=kml.newpoint(name=row[3], description=row[2], coords=[(row[0],row[1])])
    new.style.iconstyle.icon.href = 'https://cdn-icons-png.flaticon.com/512/287/287975.png' #change icon

##################################################################################
# Menu para escolha do tipo de coordenada a inserir: aleatoria, predifinida ou manual
while TRUE:
    ##INSERT Coordenates by USER:
    print("######################### ALERTA #######################")
    print("Escolha uma das Opções Seguintes para Gerar um Local de Alerta")
    print("Opção 1 - Inserir Coordenadas Manualmente")
    print("Opção 2 - Gerar Coordenadas Aleatórias")
    print("Opção 3 - Local de Alerta em Cacia")

    local_alert = (input())
    if (local_alert == '1'):
              
        ##INSERT Coordenates by USER:
        # Insert Coordenates manually from Terminal
        print()
        print("Introduza as coordenadas(latitude e longitude) onde ocorreu o Alerta")
        print("             Menu de Coordenadas: ")
        print("             Portugal Continental: ")
        print("         latitude = [37.16348;41.90280] (S/N) ")
        print("         longitude = [-9.59106;-7.06023] (O/E)" )
        print()
        latitude = (input("Introduzir Latitude: "))
        longitude = (input("Introduzir longitude: "))
        #break
    elif(local_alert == '2'):
        # sup esq 41.799663 , -8.629966
        # sup dir 41.758699 , -7.278648
        # inf esq 37.260596 , -8.564048
        # inf dir 37.286823, -7.509360
        latitude = round(random.uniform(37.275684, 41.765498), 6)
        longitude = round(random.uniform(-8.5865498,-7.356487), 6)
        print("Coordenada do Alerta Gerada:")
        print('Latitude: ' + str(latitude) + '  Longitude: ' + str(longitude))
        print()
        #break
    elif(local_alert == '3'):
         ## Alerta em Cacia
        latitude = 40.682352
        longitude = -8.63209
        #break


    ########################################################################
    ## Imagem do alerta no google earth 
    # icon para local do alerta
    print("[+]Gerar Imagem Google Earth com as Antenas")
    alerta=kml.newpoint(name="FIRE!", description="local", coords=[(longitude,latitude)])
    alerta.style.iconstyle.icon.href = 'https://issaquahhighlands.com/wp-content/uploads/2015/10/fire.jpg' #change icon
    alerta.style.labelstyle.scale = 2
    alerta.style.labelstyle.color = simplekml.Color.white  # Make the text red
    kml.save("list_v1.kml")

    ###################################################################################
    ## Calculo das antenas mais proximas:
    ##
    # 1º é aprox. 111,11 Km
    # 10 km aprox 0.090
    dist_ant = 0.063 # 7km
    ## Criação de um circulo imaginário que tem como centro o ALERTA.
    ## recolher info das antenas dentro do circulo. até 5 antenas
    num_ant = 0
        
    print("[+]Procura Antenas Próximas ao Local do Alerta")
    while True:
            
        range_latitude1 =float(latitude)+dist_ant
        range_latitude2 =float(latitude)-dist_ant
        range_longitude1 =float(longitude)+dist_ant
        range_longitude2 =float(longitude)-dist_ant
        # identifica antenas no raio proximo
        idx = 0 ##   linha no ficheiro csv = idx + 2
        p_it = 0
        list_idx = []
            
        for i in range(len(lat_ant[1:])):
            if (lat_ant[i] < (range_latitude1)) & (lat_ant[i] > (range_latitude2) ):
                if (long_ant[i] < (range_longitude1)) & (long_ant[i] > (range_longitude2) ):
                    ant_ver = 0 # verificar antenas no mesmo sitio
                    list_idx.append(i)
                    idx=i
                    #verificar se esta antena já está na lista de antenas encontradas
                    # para não contar como antena nova
                    if p_it == 0:
                        num_ant = num_ant+1
                        #print(idx)
                        #print(x4[i])
                        antena=kml.newpoint(name=PS_est[i], description=PS_est[i], coords=[(long_ant[idx],lat_ant[idx])])
                        antena.style.iconstyle.icon.href = 'https://d1nhio0ox7pgb.cloudfront.net/_img/o_collection_png/green_dark_grey/256x256/plain/antenna.png' #change icon
                        antena.style.labelstyle.color = simplekml.Color.white  # Make the text blue
                        antena.style.labelstyle.scale = 2
                        kml.save("list_v1.kml")
                        p_it = 1
                    else:
                        for j in range(len(list_idx)-1):  # o últimos elemento do array list_idx é o próprio
                            if(long_ant[list_idx[j]]==long_ant[idx] and lat_ant[list_idx[j]]==lat_ant[idx]):
                                ant_ver = ant_ver+1
                                #print(ant_ver)
                        if ant_ver == 0:
                            num_ant = num_ant+1
                            antena=kml.newpoint(name=PS_est[i], description=PS_est[i], coords=[(long_ant[idx],lat_ant[idx])])
                            antena.style.iconstyle.icon.href = 'https://d1nhio0ox7pgb.cloudfront.net/_img/o_collection_png/green_dark_grey/256x256/plain/antenna.png' #change icon
                            antena.style.labelstyle.color = simplekml.Color.white  # Make the text blue
                            antena.style.labelstyle.scale = 2
                            kml.save("list_v1.kml")

        if num_ant >= 5:
            break 
        else:
            dist_ant = dist_ant + 0.018  # acrescenta 2km
            num_ant = 0
        ## Lista de frequências, PS  e PI 
        
    list_af = []
    af = "AF="
    for i in range(len(list_idx)):
        if (freq_trans[list_idx[i]] in list_af):
            pass 
        else:
            list_af.append(freq_trans[list_idx[i]])
            af = af+str(freq_trans[list_idx[i]])+','
    # acrescentar as freq que estamos a usar para simular no lab
    af = af+str(100.0)+','+str(102.0)+','
    #print(list_af)
    af = af[:-1]
    ## print para verificaçao
    print(af)

    af = bytes(af,'utf-8')
        
    ## print para verificaçao
    ps = "PS="+str('FIRETEC1') ## PS do tipo FIRETECX onde X incrementa consoante o numero de incendios
    ps = bytes(ps,'utf-8')
    #print(ps)
    # ps_inc = (ps_inc +1)
    # if(ps_inc == 10 ):
    #     ps_inc = 0

    ## print para verificaçao
    # if(pi_inc < 16):
    #     pi = "PI="+str(840)+str(hex(pi_inc)[2:])    ## PI tem de ser 84XX consuante deteta incendio aumenta o valor de XX
    #     pi = bytes(pi,'utf-8')
    # else:
    #     pi = "PI="+str(84)+str(hex(pi_inc)[2:])    ## PI tem de ser 84XX consuante deteta incendio aumenta o valor de XX
    #     pi = bytes(pi,'utf-8')
    pi = "PI="+str(8400)    ## PI tem de ser 84XX consuante deteta incendio aumenta o valor de XX
    pi = bytes(pi,'utf-8')
    #print(pi)
    # pi_inc = pi_inc +1
    # if(pi_inc > 255 ):
    #     pi_inc = 0

    #################################################################################
    ## Circulo de transmissao da mensagem
    print("[+]Gerar Imagem com Circulo de Transmissão")

    # criar circulo
    for i in range(len(list_idx)):
        polycircle = polycircles.Polycircle(latitude=float(lat_ant[list_idx[i]]),
                                            longitude=float(long_ant[list_idx[i]]),
                                            radius=float(raio_trans[list_idx[i]]*1000),
                                            number_of_vertices=36)
        pol = kml.newpolygon(name="Circle",
                            outerboundaryis=polycircle.to_kml())
        pol.style.polystyle.color = simplekml.Color.changealphaint(200, simplekml.Color.green)
            
    kml.save("list_v1.kml")


    ######################################################################################
    ## Determinar a localidade do Alerta
    #extrair dados da base de dados de codigos postais para caso seja necessario
    nome_files="Localidades_Portugal.csv"
    # reading CSV file
    local = pd.read_csv(nome_files)
    # reading CSV file e put date in vars
    long_pt=local["Longitude"].tolist()
    lat_pt=local["Latitude"].tolist()
    freg_pt=local["Freguesia"].tolist()
    conc_pt=local["Concelho"].tolist()
    dist_pt=local["Distrito"].tolist()
    local = [[long_pt[i],lat_pt[i],freg_pt[i],conc_pt[i],dist_pt[i]] for i in range(len(long_pt))]
    dist_loc = 100000
    long_rad = (float(longitude)*3.14159)/180
    lat_rad = (float(latitude)*3.14159)/180

    print("[+]Determinar Nome da Localidade do Alerta")

    try:
        locator = Nominatim(user_agent='myGeocoder')
        location = locator.reverse((latitude,longitude))
        # Como não queremos tanta informaçao que está no location 
        # acedemos ao seu dictionary e retiramos a informação que precisamos
        # Problemas l.address tem tamanhos variaveis dependentes do local e key diferentes tambem 
        # dependendo do local('village ou 'town')
        l = location.address    # l é uma string proveniente do dictionary location e key address
        l1 = location.address.split(',')  # dividimos a string num array de string atravé da ,

        #print(any(char.isdigit() for char in l1[len(l1)-2]))
        if(any(char.isdigit() for char in l1[len(l1)-2])):  ## string com o codigo postal EX: Bairro dos 14 Fogos, Caridade, Reguengos de Monsaraz, Évora, 7200-225, Portugal

            if(len(l1)<5):
                for i in range(len(long_pt[1:])):
                    long_loc_rad = (long_pt[i]*3.14159)/180
                    lat_loc_rad = (lat_pt[i]*3.14159)/180
                    dist = 6372795.477 * math.acos( math.sin(lat_rad)*math.sin(lat_loc_rad) + math.cos(lat_rad)*math.cos(lat_loc_rad) * math.cos(long_rad - long_loc_rad) )
                    if(dist < dist_loc):
                        dist_loc = dist
                        idx_loc = i

                print('\nLocalidade do Alerta:')
                print( freg_pt[idx_loc], conc_pt[idx_loc], dist_pt[idx_loc])
                alert = "Alerta de Incêndio na Freguesia de "+freg_pt[idx_loc]+", no Concelho de "+conc_pt[idx_loc]+", no Distrito de "+dist_pt[idx_loc]
                #print(dist_loc)
            else:
                alert = "Alerta de Incêndio na Freguesia de "+l1[len(l1)-5]+", no Concelho de "+l1[len(l1)-4]+", no Distrito de "+l1[len(l1)-3]

        else:  ##  string sem o codigo postal EX: Bairro dos 14 Fogos, Caridade, Reguengos de Monsaraz, Évora, Portugal
            if(len(l1)<4):
                for i in range(len(long_pt[1:])):
                    long_loc_rad = (long_pt[i]*3.14159)/180
                    lat_loc_rad = (lat_pt[i]*3.14159)/180
                    dist = 6372795.477 * math.acos( math.sin(lat_rad)*math.sin(lat_loc_rad) + math.cos(lat_rad)*math.cos(lat_loc_rad) * math.cos(long_rad - long_loc_rad) )
                    if(dist < dist_loc):
                        dist_loc = dist
                        idx_loc = i

                print('\nLocalidade do Alerta:')
                print(freg_pt[idx_loc], conc_pt[idx_loc], dist_pt[idx_loc])
                alert = "Alerta de Incêndio na Freguesia de "+freg_pt[idx_loc]+", no Concelho de "+conc_pt[idx_loc]+", no Distrito de "+dist_pt[idx_loc]
                #print(dist_loc)
            else:
                alert = "Alerta de Incêndio na Freguesia de "+l1[len(l1)-4]+", no Concelho de "+l1[len(l1)-3]+", no Distrito de "+l1[len(l1)-2]

    except:
        for i in range(len(long_pt[1:])):
            long_loc_rad = (long_pt[i]*3.14159)/180
            lat_loc_rad = (lat_pt[i]*3.14159)/180
            dist = 6372795.477 * math.acos( math.sin(lat_rad)*math.sin(lat_loc_rad) + math.cos(lat_rad)*math.cos(lat_loc_rad) * math.cos(long_rad - long_loc_rad) )
            if(dist < dist_loc):
                dist_loc = dist
                idx_loc = i

        print('\nLocalidade do Alerta:')
        print( freg_pt[idx_loc], conc_pt[idx_loc], dist_pt[idx_loc])
        alert = "Alerta de Incêndio na Freguesia de "+freg_pt[idx_loc]+", no Concelho de "+conc_pt[idx_loc]+", no Distrito de "+dist_pt[idx_loc]

    print('\nMensagem de Alerta Gerada:')
    print (alert)

    ######################################################################################
    ## Encontrar as Estradas num circulo de raio dinâmico do Local do Alerta
    # Usa o CSV local roads_portugal.csv em vez do Overpass API.
    print("[+]Procurar Estradas Próximas ao Local do Alerta")
    name_road = find_nearby_roads(
        float(latitude),
        float(longitude),
        ROAD_POINTS,
        ROAD_GRID_INDEX
    )

    if name_road:
        print("[+] Estradas encontradas no CSV local: " + ", ".join(name_road))
        alert = alert + ", cuidado ao circular na estrada " + ", ".join(name_road)
    else:
        print("[!] Nenhuma estrada encontrada no CSV local.")

    
    print('\nMensagem de Alerta Gerada:')
    print(alert)

    ###################################################################################
        ## Criar ficheiro de audio
    print("[+]Gerar Ficheiro Aúdio com Mensagem do Alerta")
    tts = gTTS(alert, lang='pt')

    tts.save("example.mp3")


    # Load the audio file
    audio = AudioSegment.from_file("example.mp3", format="mp3")

        # Set the sample rate and bit depth
    audio = audio.set_frame_rate(32000)
    audio = audio.set_sample_width(1)

        # Save the audio file in WAV format
    audio.export("example1.wav", format="wav")


    ######################################################################################
       ## Comunicação com os Firetec Switchs
    print("[+]Comuncicação com Firetec Switch")
    with open("example1.wav", 'rb') as wav_file:
        wav_data = wav_file.read()

            
    data=wav_data +ps+ b';'+ pi+b';'+af+b';'
    print(f"[+] Payload preparado | WAV={len(wav_data)} bytes | total={len(data)} bytes")

    transmission_results = []
    for target in SWITCH_TARGETS:
        transmission_results.append(
            transmit_to_firetec_switch(target, data)
        )

    success_count = sum(1 for result in transmission_results if result["success"])
    print(f"[+] Resumo transmissao: {success_count}/{len(transmission_results)} switches OK")
    for result in transmission_results:
        if result["success"]:
            print(
                f"    - {result['host']} OK em {result['port']} "
                f"({result['duration']:.2f}s)"
            )
        else:
            print(
                f"    - {result['host']} FALHOU "
                f"({result['error']})"
            )

