import tkinter as tk, socket, qrcode
from PIL import Image, ImageTk

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8",80))
    return s.getsockname()[0]

ip = get_ip()
url = f"http://{ip}:5000"

qrcode.make(url).save("/tmp/qr.png")

root = tk.Tk()
root.title("ME Camera Setup")
root.geometry("420x560")

tk.Label(root, text="MangiafestoElectronics LLC").pack()
tk.Label(root, text="ME Camera Setup", font=("Arial",20)).pack()

img = ImageTk.PhotoImage(Image.open("/tmp/qr.png").resize((300,300)))
tk.Label(root, image=img).pack()

tk.Label(root, text=url).pack()
root.mainloop()
