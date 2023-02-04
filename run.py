from api.app import create_app, socketio, configure_celery, celery

app = create_app()
configure_celery(app)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
