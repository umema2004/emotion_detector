terminal 1: 
o\templates> python -m http.server 5500

terminal 2:
o> uvicorn main:socket_app --host 0.0.0.0 --port 8000
