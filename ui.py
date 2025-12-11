import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import importlib.util
from config import GRID_SIZE

# Load client module from NEW/client.py dynamically
CLIENT_PATH = os.path.join(os.path.dirname(__file__), 'client.py')
spec = importlib.util.spec_from_file_location('client_mod', CLIENT_PATH)
client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_mod)

CELL_SIZE = 25
CANVAS_SIZE = CELL_SIZE * GRID_SIZE

COLOR_MAP = {
    0: "#4F4F4F",  # gray none
    1: '#FF4D4D',  # red p1
    2: '#4D79FF',  # blue p2
    3: '#4DFF88',  # green p3
    4: '#FFD24D',  # yellow p4
}

class GameUI:
    def __init__(self, root):
        self.root = root
        root.title('Grid Client UI')

        self.client = None

        self.top_frame = tk.Frame(root)
        self.top_frame.pack(padx=10, pady=10)

        self.connect_btn = tk.Button(self.top_frame, text='CONNECT TO SERVER', command=self.on_connect)
        self.connect_btn.pack()

        self.state_label = tk.Label(self.top_frame, text='State: not connected')
        self.state_label.pack(pady=(6,0))

        # Placeholder for grid frame
        self.grid_frame = None
        self.canvas = None
        self.rects = []

        self.updating = False

    def on_connect(self):
        if self.client is not None and self.client.state == 'connected':
            messagebox.showinfo('Info', 'Already connected')
            return
        try:
            self.client = client_mod.Client()
            self.client.start()
        except Exception as e:
            messagebox.showerror('Error', f'Failed to start client: {e}')
            self.client = None
            return

        # Replace top with grid
        self.connect_btn.config(state='disabled')
        self.build_grid()
        self.updating = True
        self.root.after(100, self.update_loop)

    def build_grid(self):
        if self.grid_frame:
            self.grid_frame.destroy()
        self.grid_frame = tk.Frame(self.root)
        self.grid_frame.pack(padx=10, pady=10)

        # Create top-left stats display (ping & packet loss)
        self.stats_text = tk.StringVar(value='Ping: -- | Loss: --%')
        self.stats_label = tk.Label(self.top_frame, textvariable=self.stats_text, fg='white', bg='black', font=('mono', 9), justify='left')
        #self.stats_label.place(x=5, y=5)
        self.stats_label.pack(pady=(12,0))


        self.canvas = tk.Canvas(self.grid_frame, width=CANVAS_SIZE, height=CANVAS_SIZE, bg='white')
        self.canvas.pack()

        # Place the stats label after packing the canvas and lift it
        # so the label appears above the canvas (canvas would otherwise cover it).
        self.stats_label.place(x=5, y=5)
        self.stats_label.lift()

        self.rects = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x0 = c * CELL_SIZE
                y0 = r * CELL_SIZE
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE
                rect = self.canvas.create_rectangle(x0, y0, x1, y1, fill=COLOR_MAP[0], outline='black')
                self.rects[r][c] = rect

        self.canvas.bind('<Button-1>', self.on_canvas_click)

    def on_canvas_click(self, event):
        if not self.client:
            return
        c = event.x // CELL_SIZE
        r = event.y // CELL_SIZE
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            # send action via client
            try:
                self.client.send_action(r, c)
            except Exception as e:
                print('Send action failed:', e)

    def update_loop(self):
        if not self.updating:
            return
        # update state text
        state_text = 'State: '
        if self.client:
            state_text += self.client.state
        else:
            state_text += 'not connected'
        self.state_label.config(text=state_text)

        # update stats (ping & packet loss) in top-left
        if self.client:
            ping = self.client.ping_ms
            with self.client.recv_stats_lock:
                total = self.client.packets_received + self.client.packets_lost
                loss_pct = 0.0
                if total > 0:
                    loss_pct = (self.client.packets_lost / total) * 100
            stats_str = f'Ping: {ping:.1f}ms | Loss: {loss_pct:.1f}%'
            self.stats_text.set(stats_str)

        # update grid from client data
        if self.client:
            grid = self.client.grid
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    owner = grid[r][c]
                    color = COLOR_MAP.get(owner, COLOR_MAP[0])
                    rect = self.rects[r][c]
                    self.canvas.itemconfig(rect, fill=color)

        self.root.after(100, self.update_loop)


if __name__ == '__main__':
    root = tk.Tk()
    app = GameUI(root)
    root.mainloop()
