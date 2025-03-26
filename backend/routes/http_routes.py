from flask import jsonify

def init_http_routes(app):
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy"}) 