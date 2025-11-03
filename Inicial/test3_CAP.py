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
import overpy
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
    # Usar overpass API para enviar o query e obter a informaçao dos servidores em json format 
    # e posteriormente extrair para ficheiros csv
    print("[+]Procurar Estradas Próximas ao Local do Alerta")
    raio = str(2000)	
    num_road = 0
    name_road = []


    while num_road <1:
        
        while True:     # caso o ficheiro criado esteja vazio aumenta o raio e sai deste while
            api = overpy.Overpass()
            result = api.query("""(
                way
                (around:"""+raio+""","""+str(latitude)+""","""+str(longitude)+""")
                [highway~"^(motorway|trunk|primary|secondary|tertiary)$"];
            >;);out;""")

            list_node_tags = []
            for way in result.ways:
                way.tags['id'] = way.id
                list_node_tags.append(way.tags)
            data_frame = pd.DataFrame(list_node_tags)
            data_frame.to_csv('road_name.csv')
            #print("\nFoi criado o ficheiro - road_name.csv - no atual diretorio.")

            road = pd.read_csv("road_name.csv")
                #print(road)
                #print(raio)

                # sair do while True caso o ficheiros csv criado esteja vazio e 
                # aumentamos o raio para nova tentativa
            if (len(road)== 0):
                raio = str(int(raio)+500)
                break  

                # pode ser craido um ficheiro com informação mas 
                # não tem a informação que queremos
            try:

                    # o ficheiro criado não está vazio 
                    # verificar se neste temos mais de 2 estradas
                    # retiramos a coluna 'ref' do ficheiro que contem o nome da estrada
                road_ref = road["ref"].tolist()
                    # Verificamos se é um nome válido ou nulo
                cnt = pd.isnull(road["ref"])

                
                    # Apenas contamos nomes válidos e guardamos numa variável para verificar
                    # se é igual ao anterior guardado
                for i in range(len(road_ref)):
                    if cnt[i] == False:
                        if (road_ref[i] in name_road):
                            pass
                        else:
                            name_road.append(road_ref[i])
                            num_road = num_road+1
                
                    #print(name_road)
                    #print(num_road)
                if (num_road <2):
                    raio = str(int(raio)+500)
                else:
                    break
            except:
                    #print("Foi criado um ficheiro sem a coluna 'ref', o raio será aumentado")
                raio = str(int(raio)+500)

    alert = alert+ ", cuidado ao circular na estrada "
    for i in range(num_road):
        alert = alert+name_road[i]+", " 

    
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

    byts = open("example1.wav", "rb").read()

    ######################################################################################
    ##  Comunicaçao com Servidor com CAP

    import capparser

    alert = capparser.element.Alert(sender="FireTec",
                                    status=capparser.enums.Status.Actual,
                                    msgType=capparser.enums.MsgType.Alert,
                                    scope=capparser.enums.Scope.Private)

    alert.setSource("FireTec")
    alert.addAddress("FireTec")


    # Alterar mensagem evento para caso especifico
    info = capparser.element.Info(category=[capparser.enums.Category.Fire],
                                event="Incendio Florestal",
                                urgency=capparser.enums.Urgency.Immediate,
                                severity=capparser.enums.Severity.Severe,
                                certainty=capparser.enums.Certainty.Observed)


    info.setSenderName("FireTec")
    info.setInstruction(
        "Foi detetado um possivel incendio florestal na sua area, precaucao e aconselhada.")

    param1 = capparser.element.Parameter(parameterName="PS",
                                        parameterValue=str(ps))
    param2 = capparser.element.Parameter(parameterName="PI",
                                        parameterValue=str(pi))
    info.addParameter(param1)
    info.addParameter(param2)

    # ciclo para criar listagem de frequencias

    # for i in range(len(list_af)):
    #   paramvalue= "AF="+str(list_af[i])
    #   param3 = capparser.element.Parameter(parameterName="AF",
    #                                        parameterValue=paramvalue)
    #   info.addParameter(param3)

    paramvalue= "AF="+str(list_af[1])
    param3 = capparser.element.Parameter(parameterName="AF",parameterValue=paramvalue)
    info.addParameter(param3)

    alert.addInfo(info)

    #capparser.writeAlertToFile(alert, "output.xml")

    ######################################################################################
    ## Envio do CAP para o arduino
    # Convert bytes to string representation of hex values
    import base64
    import binascii
    import socket
    import sys, os
    from gtts import gTTS

    resource = capparser.Resource()
    resource.setResourceDesc("Audio Message")
    resource.setMimeType("audio/wav")
    
    # Convert bytes to string representation of hex values
    resource.setDerefUri(binascii.hexlify(byts).decode('utf8'))

    # Adding resource to alert and write new file
    info.addResource(resource)
    alert.addInfo(info)
    capparser.writeAlertToFile(alert, "test.xml")

    #capparser.writeAlertToFile(alert, "output.xml")

    ## testing: python3 test3_CAP.py 192.168.0.23:8080
    #addr = sys.argv[1].split(':')
    
    #host= addr[0]
    #port = int(addr[1])

    ######################################################################################
    ## Comunicação com os Firetec Switchs
    print("[+]Comuncicação com Firetec Switch")

    #Configurar o IP do 1ª FireTec Switch
    #host= '192.168.81.183'     
    host= '192.168.0.22'
    port = 8080
    #host = socket.gethostname()
    #port = 5000  # initiate port no above 1024

    Server_socket = socket.socket() # "Create_Socket()"
    print("[++]Create_Socket() ....") 
    print("[++]Tries connection...") 
    connected = False
    while connected != True:
        try:
            Server_socket.connect((host, port))
            connected = True
            print("[+]New Firetec Swicth connection established ->"+ host) 
        except socket.error:
            sleep(0.1)

    #------ [Send & Receive] ------------
    print("[++]Sending data to Firetec Swicth ")
    Server_socket.sendall(data)  # send data to the client

    #------------------------------------------------ 
    print("[++]Closing Socket ....")
    Server_socket.close()  # close the connection
    #Configurar o IP do 2ª FireTec Switch
    #host= '192.168.81.189'     
    host= '192.168.0.21'
    port = 8080
    #host = socket.gethostname()
    #port = 5000  # initiate port no above 1024

    Server_socket = socket.socket() # "Create_Socket()"
    print("[++]Create_Socket() ....") 
    print("[++]Tries connection...") 
    connected = False
    while connected != True:
        try:
            Server_socket.connect((host, port))
            connected = True
            print("[+]New Firetec Swicth connection established ->"+ host) 
        except socket.error:
            sleep(0.1)

    #------ [Send & Receive] ------------
    print("[++]Sending data to Firetec Swicth ")
    Server_socket.sendall(data)  # send data to the client

    #------------------------------------------------ 
    print("[++]Closing Socket ....")
    Server_socket.close()  # close the connection

