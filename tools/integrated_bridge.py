"""Host-only Messages bridge; student code and API credentials stay separate."""

import sys
from http.server import ThreadingHTTPServer

from model_backend import PROJECT, complete

sys.path.insert(0, str(PROJECT))
from integrated_agent.transport import MessagesHandler

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8770), MessagesHandler)
    server.complete_model = complete
    print("Integrated model bridge: http://127.0.0.1:8770/v1/messages", flush=True)
    server.serve_forever()
