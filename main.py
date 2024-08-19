import signal
import sys
from mud_server import MUDServer

def signal_handler(sig, frame):
    print("\nShutting down the server...")
    if server:
        server.stop()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    server = MUDServer()
    
    print("Server is running. Press Ctrl+C to stop.")
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down...")
        server.stop()