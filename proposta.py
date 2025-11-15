import threading
import socket
import time
import logging
import uuid
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from datetime import datetime, timezone
from gtts import gTTS
import simplekml
import pandas as pd
import capparser
import io

# Configuração de logging
logging.basicConfig(filename='firetec.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =========================
# Funções principais
# =========================

def gerar_cap(localidade, concelho, distrito):
    try:
        xml_out = "output.xml"
        agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        identifier = str(uuid.uuid4())

        xml_str = f'''<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>{identifier}</identifier>
  <sender>FireTec</sender>
  <sent>{agora}</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <category>Fire</category>
    <event>Incêndio Florestal</event>
    <urgency>Immediate</urgency>
    <severity>Severe</severity>
    <certainty>Observed</certainty>
    <area>
      <areaDesc>{localidade}, {concelho}, {distrito}</areaDesc>
    </area>
  </info>
</alert>'''

        with open(xml_out, "w", encoding="utf-8", newline="\n") as f:
            f.write(xml_str)

        logging.info("Ficheiro CAP gerado com sucesso.")
        return xml_out
    except Exception as e:
        logging.error(f"Erro ao gerar CAP: {e}")
        return None



def validar_cap(xml_file):
    try:
        dom = minidom.parse(xml_file)
        root = dom.documentElement
        if root.tagName.lower() not in ["alert", "cap:alert"]:
            raise ValueError("Elemento raiz inesperado no CAP.")

        logging.info("Validacao CAP concluida (XML bem formado)")
    except Exception as e:
        logging.error(f"Erro na validacao CAP: {e}")

def gerar_audio(mensagem):
    try:
        gTTS(mensagem, lang='pt').save("example1.wav")
        logging.info("Audio gerado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao gerar audio: {e}")


def gerar_kml(lat, lon):
    try:
        kml = simplekml.Kml()
        kml.newpoint(name="Alerta de Incêndio", coords=[(lon, lat)])
        kml.save("list_v1.kml")
        logging.info("Ficheiro KML gerado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao gerar KML: {e}")


def enviar_socket(xml_file):
    try:
        with open(xml_file, "r", encoding="utf-8") as f:
            xml_data = f.read()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            # s.connect(("127.0.0.1", 5000))
            # s.sendall(xml_data.encode())
            logging.info("Envio via socket omitido (simulado).")
        except ConnectionRefusedError:
            logging.error("Servidor FireTec não disponivel.")
        finally:
            s.close()
    except Exception as e:
        logging.error(f"Erro no envio de socket: {e}")


# =========================
# Função principal
# =========================

def main():
    start = time.time()

    # Leitura de dados CSV
    df = pd.read_csv("Inicial/Localidades_Portugal.csv")
    linha = df.sample(1).iloc[0]
    localidade = linha["Localidade"]
    concelho = linha["Concelho"]
    distrito = linha["Distrito"]
    lat, lon = float(linha["Latitude"]), float(linha["Longitude"])

    mensagem = f"Alerta de incêndio na freguesia {localidade}, concelho {concelho}, distrito {distrito}."

    # Geração do CAP
    xml_file = gerar_cap(localidade, concelho, distrito)

    # Threads paralelas
    threads = [
        threading.Thread(target=gerar_audio, args=(mensagem,)),
        threading.Thread(target=gerar_kml, args=(lat, lon)),
        threading.Thread(target=enviar_socket, args=(xml_file,))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    validar_cap(xml_file)

    elapsed = time.time() - start
    logging.info(f"Processo concluido em {elapsed:.2f} segundos.")


if __name__ == "__main__":
    main()
