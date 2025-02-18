import socket
import threading
import random
import datetime  # <-- new import for timestamp
from tkinter import *
from tkinter import simpledialog  # Fix import for simpledialog

# บทบาทในเกม
ROLES = ["Werewolf", "Villager", "Seer", "Witch"]

# ข้อมูลเกม
rooms = {}
clients = {}
ready_status = {}

# GUI สำหรับเลือกโหมด
def start_game(username, mode, room_name=None):
    global root
    root.destroy()
    if mode == "host":
        host_mode(username, room_name)
    elif mode == "join":
        client_mode(username, room_name)

def main_menu():
    global root
    root = Tk()
    root.title("Werewolf Game - Main Menu")
    root.geometry("350x250")

    # New: Use a header label and a frame for inputs
    header = Label(root, text="Werewolf Game", font=("Helvetica", 16, "bold"))
    header.pack(pady=10)

    frame = Frame(root)
    frame.pack(pady=10)

    label_username = Label(frame, text="Enter your username:", font=("Helvetica", 12))
    label_username.grid(row=0, column=0, padx=5, pady=5)
    entry_username = Entry(frame, font=("Helvetica", 12))
    entry_username.grid(row=0, column=1, padx=5, pady=5)

    # New: Use a frame for buttons
    btn_frame = Frame(root)
    btn_frame.pack(pady=10)

    def create_game():
        username = entry_username.get()
        if username:
            room_name = simpledialog.askstring("Create Game", "Enter room name:")
            if room_name:
                start_game(username, "host", room_name)

    def join_game():
        username = entry_username.get()
        if username:
            room_name = simpledialog.askstring("Join Game", "Enter room name:")
            if room_name:
                start_game(username, "join", room_name)

    button_create = Button(btn_frame, text="Create Game", font=("Helvetica", 12), width=12, command=create_game)
    button_create.grid(row=0, column=0, padx=10, pady=5)
    button_join = Button(btn_frame, text="Join Game", font=("Helvetica", 12), width=12, command=join_game)
    button_join.grid(row=0, column=1, padx=10, pady=5)

    root.mainloop()

# Host Mode (Server + Player)
def host_mode(username, room_name):
    global rooms, clients, ready_status
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(5)

    def handle_client(client_socket, addr):
        print(f"[NEW CONNECTION] {addr} connected.")
        while True:
            try:
                message = client_socket.recv(1024).decode()
                if message.startswith("JOIN_ROOM"):
                    # Changed: Extract room_name and username from message "JOIN_ROOM:<room_name>:<username>"
                    parts = message.split(":")
                    room_name = parts[1]
                    username = parts[2] if len(parts) > 2 else "Unknown"
                    if room_name in rooms:
                        rooms[room_name]["players"].append((username, addr))
                        ready_status[username] = False
                        clients[addr] = client_socket
                        client_socket.send(f"JOINED_ROOM:{room_name}".encode())
                        for player in rooms[room_name]["players"]:
                            clients[player[1]].send(f"UPDATE_PLAYERS:{update_player_list(room_name)}".encode())
                    else:
                        client_socket.send("ROOM_NOT_FOUND".encode())
                elif message.startswith("START_GAME"):
                    room_name = message.split(":")[1]
                    if room_name in rooms:
                        players = rooms[room_name]["players"]
                        roles = random.sample(ROLES, len(players))
                        rooms[room_name]["roles"] = roles
                        for i, player in enumerate(players):
                            clients[player[1]].send(f"ROLE_ASSIGNED:{roles[i]}".encode())
                elif message.startswith("READY"):
                    player_name = message.split(":")[1]
                    ready_status[player_name] = True
                    for player in rooms[room_name]["players"]:
                        clients[player[1]].send(f"UPDATE_PLAYERS:{update_player_list(room_name)}".encode())
                    # Auto-start game: Once every player is ready, randomize roles and broadcast them.
                    if all(ready_status.get(p[0], False) for p in rooms[room_name]["players"]):
                        print("[ALL PLAYERS READY] Starting game...")
                        players = rooms[room_name]["players"]
                        roles = random.sample(ROLES, len(players))
                        rooms[room_name]["roles"] = roles
                        for i, player in enumerate(players):
                            clients[player[1]].send(f"ROLE_ASSIGNED:{roles[i]}".encode())
                elif message.startswith("CHAT:"):
                    # New: Broadcast chat messages with a timestamp.
                    # Expected format from client: "CHAT:<username>:<message>"
                    parts = message.split(":", 2)
                    sender = parts[1]
                    chat_msg = parts[2]
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    broadcast = f"CHAT:{sender}:{timestamp}:{chat_msg}"
                    for player in rooms[room_name]["players"]:
                        clients[player[1]].send(broadcast.encode())
            except Exception as e:
                print(f"[ERROR] {e}")
                break
        client_socket.close()  # Ensure socket is closed

    def start_server():
        print("[SERVER STARTED]")
        while True:
            client_socket, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            thread.start()

    # Changed: Initialize room without pre-adding host
    rooms[room_name] = {"players": [], "roles": []}
    # Start the server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

    # Host joins the game as a player
    client_mode(username, room_name)

# Client Mode
def client_mode(username, room_name):
    global rooms, clients, ready_status
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", 5555))

    client.send(f"JOIN_ROOM:{room_name}:{username}".encode())
    response = client.recv(1024).decode()
    if response.startswith("JOINED_ROOM"):
        print(f"[JOINED ROOM] {room_name}")
    else:
        print("[ERROR] Room not found")
        client.close()
        return

    # New: Enhanced UI using frames and custom styling
    root = Tk()
    root.title(f"Werewolf Game - {username}")
    root.geometry("400x350")
    root.configure(bg="#f0f0f0")

    header = Label(root, text=f"Room: {room_name}", font=("Helvetica", 16, "bold"), bg="#f0f0f0")
    header.pack(pady=10)

    label_count = Label(root, text="Players in room: 0", font=("Helvetica", 12), bg="#f0f0f0")
    label_count.pack(pady=5)

    label_role = Label(root, text="Waiting for game to start...", font=("Helvetica", 12), bg="#f0f0f0")
    label_role.pack(pady=10)

    players_frame = Frame(root, bg="#ffffff", bd=2, relief=RIDGE)
    players_frame.pack(pady=10, padx=20, fill="both", expand=True)
    label_players = Label(players_frame, text="Players:\n", font=("Helvetica", 12), bg="#ffffff", justify=LEFT)
    label_players.pack(pady=10, padx=10, anchor="w")

    def send_ready():
        try:
            client.send(f"READY:{username}".encode())
        except Exception as e:
            print(f"[ERROR] {e}")

    button_ready = Button(root, text="Ready", font=("Helvetica", 12), command=send_ready)
    button_ready.pack(pady=10)

    # Variables for game screen (chat UI)
    game_screen_loaded = False
    chat_display = None

    # New: Function to load the game screen with role and chat UI.
    def load_game_screen(role):
        nonlocal game_screen_loaded, chat_display
        if game_screen_loaded:
            return
        game_screen_loaded = True
        for widget in root.winfo_children():
            widget.destroy()
        # Display player's role
        role_label = Label(root, text=f"Your Role: {role}", font=("Helvetica", 16, "bold"), bg="#f0f0f0")
        role_label.pack(pady=10)
        # Chat display
        chat_display = Text(root, state=DISABLED, width=50, height=10, font=("Helvetica", 12))
        chat_display.pack(pady=5, padx=10)
        # Chat entry and send button frame
        entry_frame = Frame(root, bg="#f0f0f0")
        entry_frame.pack(pady=5)
        chat_entry = Entry(entry_frame, width=30, font=("Helvetica", 12))
        chat_entry.pack(side=LEFT, padx=(0,10))
        def send_chat():
            msg = chat_entry.get().strip()
            if msg:
                try:
                    client.send(f"CHAT:{username}:{msg}".encode())
                except Exception as e:
                    print(f"[ERROR] {e}")
                chat_entry.delete(0, END)
        send_button = Button(entry_frame, text="Send", font=("Helvetica", 12), command=send_chat)
        send_button.pack(side=LEFT)
    
    # Modified: receive_messages now also handles chat and loads game screen.
    def receive_messages():
        nonlocal game_screen_loaded, chat_display
        while True:
            try:
                message = client.recv(1024).decode()
                if message.startswith("ROLE_ASSIGNED"):
                    role = message.split(":", 1)[1]
                    # Load game screen with chat UI when role is received.
                    root.after(0, load_game_screen, role)
                elif message.startswith("CHAT:"):
                    # Format: CHAT:<sender>:<timestamp>:<message>
                    parts = message.split(":", 3)
                    sender = parts[1]
                    timestamp = parts[2]
                    chat_msg = parts[3]
                    display = f"[{timestamp}] {sender}: {chat_msg}\n"
                    if game_screen_loaded and chat_display:
                        root.after(0, lambda: (chat_display.config(state=NORMAL),
                                                 chat_display.insert(END, display),
                                                 chat_display.config(state=DISABLED),
                                                 chat_display.see(END)))
                elif message.startswith("UPDATE_PLAYERS"):
                    player_list = message.split(":", 1)[1]
                    label_players.config(text=f"Players:\n{player_list}")
                    count = len([p for p in player_list.splitlines() if p.strip() != ""])
                    label_count.config(text=f"Players in room: {count}")
            except Exception as e:
                print(f"[ERROR] {e}")
                break
        client.close()

    thread = threading.Thread(target=receive_messages)
    thread.daemon = True
    thread.start()

    root.mainloop()

def update_player_list(room_name):
    players = rooms[room_name]["players"]
    player_list = "\n".join([f"{player[0]} - {'Ready' if ready_status.get(player[0], False) else 'Not Ready'}" for player in players])
    return player_list

# เริ่มต้นโปรแกรม
if __name__ == "__main__":
    main_menu()