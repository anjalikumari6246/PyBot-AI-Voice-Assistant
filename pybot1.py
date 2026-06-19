import random
import difflib  # Built-in library to compare text and catch typos
import os      # Built-in library to handle file paths
import threading  # Built-in library to run tasks in parallel without freezing the app
import tkinter as tk  # Built-in library for creating desktop windows
from tkinter import scrolledtext  # Built-in component for scrollable text fields
import speech_recognition as sr  # For listening
import pyttsx3  # For speaking
from google import genai  # Official Google AI framework library
from google.genai import types
import time  # For handling timing and delays


# ==========================================
# 1. CORE CHATBOT DATA & LOGIC
# ==========================================

GEMINI_API_KEY = "YOUR_API_KEY"

# Connect to Google's backend servers using your credentials
client = genai.Client(api_key=GEMINI_API_KEY)

# can Use the lightweight, high-speed gemini-2.5-flash model optimized for chats 
chat_session = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction="You are PyBot, a friendly and helpful desktop AI assistant. Keep responses brief since they are read aloud."
    )
)

# Function to automatically save the conversation to a text file
def save_to_history(speaker, message):
    with open("chat_history.txt", "a", encoding="utf-8") as file:
        file.write(f"{speaker}: {message}\n")

# Function to process user input and pick the best response
def get_bot_response(user_input):
    processed_input = user_input.lower().strip()
     # Check if the user is attempting to exit the program
    if processed_input.lower() in ["bye", "exit", "quit", "goodbye"]:
        return "bye", "Goodbye! Closing the interface window."
        
    try:
        # Stream the response live to the model instance session [1]
        response = chat_session.send_message(processed_input)
        return "chat", response.text
    except Exception as error_message:
         # Check if the error is a Rate Limit / Quota error
        if "429" in str(error_message) or "RESOURCE_EXHAUSTED" in str(error_message):
            return "quota_error", "⏳ System Busy: We have exceeded the free API rate limit. Please wait 20 seconds and try again!"
        
        # Gracefully handle unexpected internet cuts or empty keys
        return "error", f"System Error: Ensure your API key is pasted correctly. Detail: {error_message}"

# This helper function reads text out loud
def speak_text(text):
    import sys
    # 1. Initialize Windows audio thread framework
    if sys.platform == "win32":
        import pythoncom
        pythoncom.CoInitialize()
        
    try:
        # 2. Set up a completely temporary speaker instance
        local_engine = pyttsx3.init()
        local_engine.setProperty('rate', 185)
        
        # 3. Queue up the response
        local_engine.say(text)
        
        # 4. Use a non-blocking loop instead of runAndWait() to prevent freezing
        local_engine.startLoop(False)
        local_engine.iterate()
        local_engine.endLoop()
        
        # 5. Clean up the engine completely to free up your microphone pipeline
        local_engine.stop()
        del local_engine
        
    except Exception as e:
        print(f"Speech hardware collision error: {e}")


# ==========================================
# 2. VOICE LISTENING THREAD (The Magic)
# ==========================================
def listen_voice():
    recognizer = sr.Recognizer()
    
    # Update GUI to show it is listening
    chat_window.config(state=tk.NORMAL)
    chat_window.insert(tk.END, "📢 System: Listening to your microphone...\n\n", "system")
    chat_window.config(state=tk.DISABLED)
    chat_window.yview(tk.END)
    
    with sr.Microphone() as source:
        try:
            # Adjust for background room noise, then listen
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            
            # Convert audio to text using Google's free service
            spoken_text = recognizer.recognize_google(audio)
            
            # Put the recognized text into the input field and auto-submit it
            user_entry.delete(0, tk.END)
            user_entry.insert(0, spoken_text)
            send_message()
            
        except sr.WaitTimeoutError:
            show_system_message("System: No audio detected. Timed out.")
        except sr.UnknownValueError:
            show_system_message("System: Could not understand the audio.")
        except Exception as e:
            show_system_message(f"System Voice Error: {e}")

# Helper to start listening without freezing the app window
def start_voice_thread():
    threading.Thread(target=listen_voice, daemon=True).start()

def show_system_message(message):
    chat_window.config(state=tk.NORMAL)
    chat_window.insert(tk.END, f"⚠️ {message}\n\n", "system")
    chat_window.config(state=tk.DISABLED)
    chat_window.yview(tk.END)

# ==========================================
# 3. GUI INTERACTION LOGIC
# ==========================================

# This function triggers whenever the user clicks "Send" or presses Enter
def send_message():
    # Step A: Get text from the input bar and remove blank spaces
    user_text = user_entry.get().strip()
    
    # If the user typed absolutely nothing, do nothing and stop
    if not user_text:
        return

    # Step B: Temporarily unlock the text window to add the user's message
    chat_window.config(state=tk.NORMAL)
    chat_window.insert(tk.END, f"You: {user_text}\n", "user")
    
    # Clear out the typing input box so it's empty for the next message
    user_entry.delete(0, tk.END)
    
    # Save user message to file
    save_to_history("You", user_text)
    
 # Fetch response data dynamically from the cloud neural network model
    status_flag, bot_text = get_bot_response(user_text)
    
    chat_window.insert(tk.END, f" PyBot: {bot_text}\n\n", "bot")
    save_to_history("PyBot", bot_text)
    chat_window.config(state=tk.DISABLED)
    chat_window.yview(tk.END)
        
    # Run the voice speaking in a thread so the window doesn't freeze while talking
    threading.Thread(target=speak_text, args=(bot_text,), daemon=True).start()

    if status_flag == "bye":
        # Automatically close out visual frames if a closing keyword is intercepted
        root.after(2000, root.destroy)


# ==========================================
# 4. CREATING THE VISUAL INTERFACE (GUI Layout)
# ==========================================

# Design Color Palette Hex Codes
COLOR_BG = "#1e1e2e"         # Dark gray-blue background frame
COLOR_CHAT_BG = "#252538"    # Lighter contrast chat window background
COLOR_TEXT_USER = "#89b4fa"  # Calm blue text for user
COLOR_TEXT_BOT = "#a6e3a1"   # Soft mint green text for chatbot
COLOR_TEXT_BASE = "#cdd6f4"  # Default clean white-ish text color
COLOR_INPUT_BG = "#313244"   # Dark bar background for text entry box
COLOR_BTN_BG = "#11111b"     # Solid deep black button background
COLOR_BTN_HOVER = "#45475a"  # Slate accent when hovering mouse

# Initialize the primary application window window frame
root = tk.Tk()
root.title("PyBot Chat Interface")
root.geometry("420x550")  # Set screen dimensions (Width x Height)
root.configure(bg=COLOR_BG)  # Set the background color of the window

# Top Header Label Bar
header = tk.Label(root, text="🤖 PyBot Assistant", font=("Helvetica", 14, "bold"), bg=COLOR_BG, fg=COLOR_TEXT_BASE, pady=10)
header.pack(fill=tk.X)

# Large text block displaying the ongoing conversation history
chat_window = scrolledtext.ScrolledText(
    root, wrap=tk.WORD, state=tk.DISABLED,
    font=("Segoe UI", 11),
    bg=COLOR_CHAT_BG, 
    fg=COLOR_TEXT_BASE,
    insertbackground=COLOR_TEXT_BASE, # Text cursor pointer color
    bd=0,                             # Remove retro window borders
    padx=10, 
    pady=10)
chat_window.pack(padx=15, pady=(0, 10), fill=tk.BOTH, expand=True)

# Define visual tags to color-code text (User text is blue, Bot text is green)
chat_window.tag_config("user", foreground=COLOR_TEXT_USER, font=("Segoe UI", 11, "bold"))
chat_window.tag_config("bot", foreground=COLOR_TEXT_BOT, font=("Segoe UI", 11))
chat_window.tag_config("system", foreground="#f38ba8", font=("Segoe UI", 10, "italic")) # Red italic for status

# Frame layout container to hold the input field and button together at the bottom
entry_frame = tk.Frame(root, bg=COLOR_BG)
entry_frame.pack(padx=15, pady=(0,15), fill=tk.X)

# Text widget box where the user physically types messages
user_entry = tk.Entry(
    entry_frame, font=("Segoe UI", 12),
    bg=COLOR_INPUT_BG, 
    fg=COLOR_TEXT_BASE,
    insertbackground=COLOR_TEXT_BASE, 
    bd=0, 
    relief=tk.FLAT,
    highlightthickness=1,
    highlightbackground=COLOR_INPUT_BG,
    highlightcolor=COLOR_TEXT_USER # Border turns blue when user clicks inside box
)
user_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=8, padx=(0, 10))

# Event binding: Pressing the physical "Enter" key executes the send_message function
user_entry.bind("<Return>", lambda event: send_message())
user_entry.focus()  # Automatically focus the cursor in the input box on launch

# Interactive button that also triggers the send_message function when clicked
mic_button = tk.Button(
    entry_frame, text="🎤", command=start_voice_thread, 
    bg=COLOR_BTN_BG, fg=COLOR_TEXT_USER, font=("Helvetica", 12),
    bd=0, relief=tk.FLAT, padx=10
)
mic_button.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))

send_button = tk.Button(
    entry_frame, text="ASK AI", command=send_message,
    bg=COLOR_BTN_BG, 
    fg=COLOR_TEXT_USER, 
    font=("Helvetica", 10, "bold"),
    bd=0,
    relief=tk.FLAT,
    activebackground=COLOR_TEXT_USER,
    activeforeground=COLOR_BTN_BG,
    padx=15
    )
send_button.pack(side=tk.RIGHT, fill=tk.BOTH)

# Visual Hover Effects for Button Interactions
def on_enter(e): send_button.config(bg=COLOR_BTN_HOVER, fg=COLOR_TEXT_BASE)
def on_leave(e): send_button.config(bg=COLOR_BTN_BG, fg=COLOR_TEXT_USER)
send_button.bind("<Enter>", on_enter)
send_button.bind("<Leave>", on_leave)

# Initial execution: Post standard opening greeting inside the screen box on launch
chat_window.config(state=tk.NORMAL)
chat_window.insert(tk.END, " PyBot: Voice online. Click the 🎤 button to speak, or type normally!\n\n", "bot")
# save_to_history("PyBot", "Hello! Type a message below to start chatting.")
chat_window.config(state=tk.DISABLED)

# Keeps the visual engine constantly open, refreshing, and listening for clicks
root.mainloop()
