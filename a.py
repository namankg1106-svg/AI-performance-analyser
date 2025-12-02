import tkinter as tk
import time
import threading
from PIL import ImageTk, Image

# ---------- Setup window ----------
root = tk.Tk()
root.title("Mood Booster 3000 💙")
root.geometry("600x650")
root.config(bg="#ADD8E6")

# ---------- Title ----------
title = tk.Label(
    root,
    text="💫 Welcome to the Mood Booster 3000 💫",
    font=("Comic Sans MS", 16, "bold"),
    bg="#ADD8E6",
    fg="#003366"
)
title.pack(pady=15)

# ---------- Emoji ----------
emoji = tk.Label(root, text="💙", font=("Arial", 150), bg="#ADD8E6")
emoji.pack(pady=10)

# ---------- Ask for mood ----------
question = tk.Label(
    root,
    text="Hey there! How are you feeling today? 😊",
    font=("Comic Sans MS", 13),
    bg="#ADD8E6",
    fg="#003366"
)
question.pack()

mood_entry = tk.Entry(root, font=("Comic Sans MS", 12), justify="center")
mood_entry.pack(pady=5)

# ---------- Output Text ----------
output = tk.Label(
    root,
    text="",
    font=("Comic Sans MS", 12, "bold"),
    bg="#ADD8E6",
    fg="#003366",
    justify="center"
)
output.pack(pady=20)

# ---------- Photo Display for "missing naman" Mode ----------
photo_label = tk.Label(root, bg="#ADD8E6")
photo_label.pack(pady=5)

# ---------- Images + Messages for "missing naman" ----------
missing_images = [
    "Snapchat-89217430.jpg",
    "Snapchat-876808747.jpg",
    "Snapchat-933287791.jpg",
    "Snapchat-1731653558.jpg",
    "Snapchat-923267954.jpg"
]

missing_msgs = [
    "🥺 Missing you a lot...",
    "💙 You make everything feel better...",
    "🤗 Wish you were here right now...",
    "✨ Every moment with you feels special...",
    "❤️ You mean more to me than you know..."
]


# ---------- Functionality ----------
def run_booster():
    mood = mood_entry.get().lower().strip()
    mood_entry.config(state="disabled")
    question.config(text="Running mood_booster.exe... 💻")

    def loading_animation():
        output.config(text="")
        photo_label.config(image="")  # Clear previous image

        for i in range(0, 101, 20):
            output.config(text=f"✨ Happiness loading... {i}%")
            time.sleep(0.5)

        # ----- If sad -----
        if "sad" in mood:
            lines = [
                "💖 Sending virtual hugs 🤗 and have bread jam 🍪",
                "Beep boop... happiness loading... 😄 100% complete!",
                "You’re amazing just as you are 💕",
                "YOU ARE ALWAYS PERFECT BABE ❤️..dont be upset bchaa!!!🤗"
            ]
            output.config(text="")
            for index, line in enumerate(lines):
                current_text = output.cget("text")
                output.config(text=current_text + "\n" + line)

                # Increase font on the last line
                if index == len(lines) - 1:
                    output.config(font=("Comic Sans MS", 16, "bold"))
                else:
                    output.config(font=("Comic Sans MS", 12, "bold"))

                time.sleep(1)

        # ----- If missing naman -----
        elif "missing naman" in mood:
            output.config(text="")
            question.config(text="Loading sweet memories... 💙")

            for idx in range(5):
                try:
                    img = Image.open(missing_images[idx])
                    img = img.resize((260, 260))
                    img_tk = ImageTk.PhotoImage(img)

                    photo_label.config(image=img_tk)
                    photo_label.image = img_tk  # Keep reference

                    output.config(text=missing_msgs[idx])
                    time.sleep(2)

                except Exception as e:
                    output.config(text=f"Error loading image: {missing_images[idx]}")
                    time.sleep(1)

        # ----- Default happy mode -----
        else:
            output.config(font=("Comic Sans MS", 12, "bold"))
            message = (
                "🌈 You’re already awesome 😎 Keep shining bright!\n"
                "✨ Today’s vibe: unstoppable energy! ⚡\n"
                "💙 Stay happy, stay you 💕"
            )
            output.config(text=message)

        question.config(text="💙 Mood Boost Complete 💙")

    threading.Thread(target=loading_animation).start()


# ---------- Pulse animation ----------
size = 150
growing = True
def pulse():
    global size, growing
    if growing:
        size += 2
        if size > 170:
            growing = False
    else:
        size -= 2
        if size < 150:
            growing = True
    emoji.config(font=("Arial", size))
    root.after(80, pulse)

# ---------- Button ----------
btn = tk.Button(
    root,
    text="Boost My Mood 💕",
    font=("Comic Sans MS", 12, "bold"),
    bg="#003366",
    fg="white",
    relief="raised",
    bd=4,
    command=run_booster
)
btn.pack(pady=10)

pulse()
root.mainloop()
