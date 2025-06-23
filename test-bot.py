import logging
from pyVoIP.VoIP import VoIPPhone, InvalidStateError, CallState
import time
import wave
import socket
import pyVoIP
from pyVoIP.audio_handler import answer
from pyVoIP.config import SIP_SERVER, SIP_PORT, SIP_EXTENSION, SIP_PASSWORD, SIP_USERNAME

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

pyVoIP.DEBUG = True

# Your local and public IPs
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def get_free_port(start_port, end_port):
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Set socket options to avoid address already in use error
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('0.0.0.0', port))
                # If binding succeeds, return the available port
                return port
            except socket.error:
                # If the port is already in use, try the next one
                continue
    raise Exception("No free port found in the given range.")     


def start_sip_phone():
    try:
        logging.info("Initializing VoIPPhone...")
        phone = VoIPPhone(
            SIP_SERVER, SIP_PORT, SIP_EXTENSION, SIP_PASSWORD,
            myIP=get_local_ip(), sipPort=get_free_port(5061,5070), auth_username=SIP_USERNAME, callCallback=answer
        )
        phone.start()
        logging.info("Phone started successfully.")
        return phone
    except Exception as e:
        logging.critical(f"Fatal error: {e}")
        return None    


# Instantiate and start the VoIP phone
if __name__ == "__main__":
    phone = start_sip_phone()

    if phone:
        input("Press enter to disable the phone...")
        phone.stop()
        time.sleep(3)
        logging.info("Phone stopped successfully.")

 
