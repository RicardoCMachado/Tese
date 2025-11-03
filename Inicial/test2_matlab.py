import csv
import math
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
import socket
from time import sleep 
import pandas as pd
import simplekml
from shapely.geometry import Point, Polygon
import dis
from re import L
import ast  # Para analisar a string de dados em uma lista
from pydub import AudioSegment

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

## Add to a kml file the Antena's places with information previous extracted from csv file
for row in data:
    new=kml.newpoint(name="", description=row[2], coords=[(row[0],row[1])])
    new.style.iconstyle.icon.href = 'https://cdn-icons-png.flaticon.com/512/287/287975.png' #change icon


##############################################################
## Abrir socket para receção de informação da fibra

print("[+]Servidor Estabelecendo Ligação com Parte da Fibra")
HOST = '192.168.81.210'  # Endereço IP do servidor (Verificar IP atribuido ao PC)
PORT = 8081       # Porta que o servidor espera dados

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"[++]Servidor aguardando conexões em {HOST}:{PORT}")

client_socket, client_address = server_socket.accept()
print(f"[++]Conexão de {client_address}")

print("[++]Receiving Data ")
data = client_socket.recv(1024)
data = data.decode()
#print(data)
data_list = []
data_aux= ""

# Converter a string recebida de volta em uma lista 
for i in range(len(data)):
    if ( (data[i] != "[") & (data[i] != "]") ):
        data_aux = data_aux+data[i]
        if((data[i] == " ")):
            data_list.append(float(data_aux))
            data_aux = ""
            
data_list.append(float(data_aux)) 

# Processar os números
Lat = data_list[0]
Long =data_list[1]
dir=data_list[2]
dist_fire = data_list[3]
print("[++]Informação Recebida")
print(f"Longitude do DST: {Lat}")
print(f"Latitude do DST: {Long}")
print(f"Sentido: {dir}")
print(f"Distância: {dist_fire}")

print("[++]Closing Socket ....")
client_socket.close()

# 1º é aprox. 111,11 Km
# 10 km aprox 0.090
## Determinar Local
if(dir == 1):
    longitude = Long
    latitude = Lat + ( dist_fire / 111110) ## definir se dist é em metros ou Km
elif(dir == 2):
    longitude = Long
    latitude = Lat - ( dist_fire / 111110) ## definir se dist é em metros ou Km
elif(dir == 4):
    latitude = Lat
    longitude = Long - ( dist_fire / 111110) ## definir se dist é em metros ou Km
elif(dir == 3):
    latitude = Lat
    longitude = Long + ( dist_fire / 111110) ## definir se dist é em metros ou Km


print("[+]Determinar Coordenadas do Local do Alerta")
print(f"Longitude do Alerta: {latitude}")
print(f"Latitude do Alerta: {longitude}")



#################################################################################
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
# 1º é aprox. 111,11 Km
# 10 km aprox 0.090
dist_ant = 0.063    # começamos com um raio aprox de 7km

## Criação de um circulo imaginário que tem como centro o ALERTA.
## recolher info das antenas dentro do circulo.
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
        dist = dist + 0.018  # acrescenta 2km
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
long_rad = (float(longitude)*3.14159)/180
lat_rad = (float(latitude)*3.14159)/180
dist_loc = 100000

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
      print( freg_pt[idx_loc],conc_pt[idx_loc], dist_pt[idx_loc])
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
      print( freg_pt[idx_loc], conc_pt[idx_loc], dist_pt[idx_loc])
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
	   #way.tags['latitude'] = way.lat
	    #way.tags['longitude'] = way.lon
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
audio.export("example.wav", format="wav")


######################################################################################
## Comunicação com o FireTtEc switch e o ficheiro em C para envio da letra para tocar
print("[+]Comuncicação com Firetec Switch")
with open("example.wav", 'rb') as wav_file:
      wav_data = wav_file.read()

data=wav_data +ps+ b';'+ pi+b';'+af+b';'
#print(data)
#Configurar o IP do 1ª FireTec Switch    
host= '192.168.81.236'
port = 8080

Server_socket = socket.socket() # "Create_Socket()"
print("[+]Create_Socket() ....") 
print("[+]Tries connection...") 

connected = False
while connected != True:
  try:
    Server_socket.connect((host, port))
    connected = True
    print("[+]New Firetec Swicth connection established ->"+ host) 
  except socket.error:
    sleep(0.1)

#------ [Send & Receive] ------------
print("[+]Sending data to Firetec Swicth ")
Server_socket.sendall(data)  # send data to the client

#------------------------------------------------ 
print("[+]Closing Socket ....")
Server_socket.close()  # close the connection


print("[+]Comuncicação com Firetec Switch")
with open("example.wav", 'rb') as wav_file:
      wav_data = wav_file.read()

data=wav_data +ps+ b';'+ pi+b';'+af+b';'
#print(data)
#Configurar o IP do 2ª FireTec Switch    
host= '192.168.81.208'
port = 8080

Server_socket = socket.socket() # "Create_Socket()"
print("[+]Create_Socket() ....") 
print("[+]Tries connection...") 

connected = False
while connected != True:
  try:
    Server_socket.connect((host, port))
    connected = True
    print("[+]New Firetec Swicth connection established ->"+ host) 
  except socket.error:
    sleep(0.1)

#------ [Send & Receive] ------------
print("[+]Sending data to Firetec Swicth ")
Server_socket.sendall(data)  # send data to the client

#------------------------------------------------ 
print("[+]Closing Socket ....")
Server_socket.close()  # close the connection

