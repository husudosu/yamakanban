from flask_socketio import Namespace, emit, join_room


class BoardNamespace(Namespace):

    def on_connect(self):
        print("Client connected")

    def on_disconnect(self):
        pass

    def on_my_event(self, data):
        print("My event", data)

    def on_board_change(self, data):
        print(f"Subscribing to new board events: {data}")
        board_id = data["board_id"]
        join_room(f"board-{board_id}")
