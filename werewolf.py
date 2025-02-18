import socket
import threading
import random
import re
from tkinter import *
from tkinter import simpledialog

# Roles in game
ROLES = ["Werewolf", "Villager", "Seer"]

# Game data containers
rooms = {}
clients = {}
ready_status = {}

def get_local_ip():
    """Return the local IP address by connecting to an external host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def start_udp_discovery():
    """Handle UDP discovery for the game."""
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_sock.bind(("", 5556))
    while True:
        try:
            data, addr = udp_sock.recvfrom(1024)
            if data.decode().strip() == "DISCOVER_WEREWOLF":
                host_ip = get_local_ip()
                udp_sock.sendto(host_ip.encode(), addr)
        except Exception as e:
            print(f"[UDP ERROR] {e}")
            break

def discover_host():
    """Discover host IP via UDP broadcast."""
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.settimeout(3)
    try:
        udp_sock.sendto("DISCOVER_WEREWOLF".encode(), ("<broadcast>", 5556))
        data, _ = udp_sock.recvfrom(1024)
        return data.decode().strip()
    except Exception as e:
        print(f"[DISCOVER ERROR] {e}")
        return None

# GUI and game mode selection
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

    header = Label(root, text="Werewolf Game", font=("Helvetica", 16, "bold"))
    header.pack(pady=10)
    
    frame = Frame(root)
    frame.pack(pady=10)
    Label(frame, text="Enter your username:", font=("Helvetica", 12)).grid(row=0, column=0, padx=5, pady=5)
    entry_username = Entry(frame, font=("Helvetica", 12))
    entry_username.grid(row=0, column=1, padx=5, pady=5)
    
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
    Button(btn_frame, text="Create Game", font=("Helvetica", 12), width=12, command=create_game).grid(row=0, column=0, padx=10, pady=5)
    Button(btn_frame, text="Join Game", font=("Helvetica", 12), width=12, command=join_game).grid(row=0, column=1, padx=10, pady=5)
    
    root.mainloop()

# Host Mode (Server + Player)
def host_mode(username, room_name):
    global rooms, clients, ready_status
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(5)
    
    # Start UDP discovery thread
    threading.Thread(target=start_udp_discovery, daemon=True).start()
    
    def handle_client(client_socket, addr):
        print(f"[NEW CONNECTION] {addr} connected.")
        while True:
            try:
                message = client_socket.recv(1024).decode()
                if message.startswith("JOIN_ROOM"):
                    parts = message.split(":")
                    room_name = parts[1]
                    user = parts[2] if len(parts) > 2 else "Unknown"
                    if room_name in rooms:
                        rooms[room_name]["players"].append((user, addr))
                        ready_status[user] = False
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
                        if len(players) == 2:
                            roles = ["Werewolf", "Villager"]
                            random.shuffle(roles)
                        else:
                            wolf_count = max(1, len(players) // 3)
                            wolf_indices = random.sample(range(len(players)), wolf_count)
                            non_wolf_indices = [i for i in range(len(players)) if i not in wolf_indices]
                            seer_index = random.choice(non_wolf_indices) if non_wolf_indices else None
                            roles = []
                            for i in range(len(players)):
                                if i in wolf_indices:
                                    roles.append("Werewolf")
                                elif i == seer_index:
                                    roles.append("Seer")
                                else:
                                    roles.append("Villager")
                        rooms[room_name]["roles"] = roles
                        for i, player in enumerate(players):
                            clients[player[1]].send(f"ROLE_ASSIGNED:{roles[i]}".encode())
                elif message.startswith("READY"):
                    user = message.split(":")[1]
                    ready_status[user] = True
                    for player in rooms[room_name]["players"]:
                        clients[player[1]].send(f"UPDATE_PLAYERS:{update_player_list(room_name)}".encode())
                    if all(ready_status.get(p[0], False) for p in rooms[room_name]["players"]):
                        print("[ALL PLAYERS READY] Starting game...")
                        players = rooms[room_name]["players"]
                        if len(players) == 2:
                            roles = ["Werewolf", "Villager"]
                            random.shuffle(roles)
                        else:
                            wolf_count = max(1, len(players) // 3)
                            wolf_indices = random.sample(range(len(players)), wolf_count)
                            non_wolf_indices = [i for i in range(len(players)) if i not in wolf_indices]
                            seer_index = random.choice(non_wolf_indices) if non_wolf_indices else None
                            roles = []
                            for i in range(len(players)):
                                if i in wolf_indices:
                                    roles.append("Werewolf")
                                elif i == seer_index:
                                    roles.append("Seer")
                                else:
                                    roles.append("Villager")
                        rooms[room_name]["roles"] = roles
                        for i, player in enumerate(players):
                            clients[player[1]].send(f"ROLE_ASSIGNED:{roles[i]}".encode())
                elif message.startswith("CHAT:"):
                    parts = message.split(":", 2)
                    sender = parts[1]
                    chat_msg = re.sub(r'^\d{1,2}:\d{1,2}:', '', parts[2])
                    broadcast = f"CHAT:{sender}:{chat_msg}"
                    for player in rooms[room_name]["players"]:
                        clients[player[1]].send(broadcast.encode())
            except Exception as e:
                print(f"[ERROR] {e}")
                break
        client_socket.close()
    
    def start_server():
        print("[SERVER STARTED]")
        while True:
            client_socket, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_socket, addr)).start()
    
    rooms[room_name] = {"players": [], "roles": []}
    threading.Thread(target=start_server, daemon=True).start()
    
    client_mode(username, room_name)

# Client Mode
def client_mode(username, room_name):
    global rooms, clients, ready_status
    host_ip = discover_host() if username and room_name else "127.0.0.1"
    if not host_ip:
        print("[ERROR] Could not discover host IP. Try again or input manually.")
        return
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host_ip, 5555))
    
    client.send(f"JOIN_ROOM:{room_name}:{username}".encode())
    response = client.recv(1024).decode()
    if response.startswith("JOINED_ROOM"):
        print(f"[JOINED ROOM] {room_name}")
    else:
        print("[ERROR] Room not found")
        client.close()
        return
    
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
    Button(root, text="Ready", font=("Helvetica", 12), command=send_ready).pack(pady=10)
    
    game_screen_loaded = False
    chat_display = None
    def load_game_screen(role):
        nonlocal game_screen_loaded, chat_display
        if game_screen_loaded:
            return
        game_screen_loaded = True
        for widget in root.winfo_children():
            widget.destroy()
        Label(root, text=f"Your Role: {role}", font=("Helvetica", 16, "bold"), bg="#f0f0f0").pack(pady=10)
        chat_display = Text(root, state=DISABLED, width=50, height=10, font=("Helvetica", 12))
        chat_display.pack(pady=5, padx=10)
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
        Button(entry_frame, text="Send", font=("Helvetica", 12), command=send_chat).pack(side=LEFT)
    
    def receive_messages():
        nonlocal game_screen_loaded, chat_display
        while True:
            try:
                message = client.recv(1024).decode()
                if message.startswith("ROLE_ASSIGNED"):
                    role = message.split(":", 1)[1]
                    root.after(0, load_game_screen, role)
                elif message.startswith("CHAT:"):
                    parts = message.split(":", 2)
                    sender = parts[1]
                    chat_msg = parts[2].strip()
                    display = f"{sender}: {chat_msg}\n"
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
    
    threading.Thread(target=receive_messages, daemon=True).start()
    root.mainloop()

def update_player_list(room_name):
    players = rooms[room_name]["players"]
    return "\n".join([f"{player[0]} - {'Ready' if ready_status.get(player[0], False) else 'Not Ready'}" for player in players])

if __name__ == "__main__":
    main_menu()