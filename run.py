from backend.app import app, socketio

if __name__ == '__main__':
    def find_available_port(start_port, max_port=5010):
        """Find an available port between start_port and max_port."""
        import socket
        for port in range(start_port, max_port + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('', port))
                    return port
                except OSError:
                    continue
        return None

    port = find_available_port(5000)
    if port:
        print(f"Starting server on port {port}")
        socketio.run(app, host='0.0.0.0', port=port)
    else:
        print("No available ports found between 5000 and 5010") 