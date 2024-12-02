from tkinter import * 
from tkinter import ttk
from tkinter import filedialog as fd

import whisper 
import srt
from datetime import timedelta
import subprocess
import os
import sys
import threading

import sv_ttk



selected_file = ""

# Define the function to get the correct file paths in the bundled app
def get_bundle_path(filename):
    if getattr(sys, 'frozen', False):  # Running in a bundled executable
        base_path = sys._MEIPASS  # This points to the temporary folder where PyInstaller extracted files
    else:  # Running in development mode
        base_path = os.path.dirname(__file__)  # Current directory of the script
    return os.path.join(base_path, filename)


# Set ffmpeg_path based on the platform and bundle
if sys.platform == "win32":  # Windows
    ffmpeg_path = get_bundle_path('ffmpeg/ffmpeg.exe')
elif sys.platform == "darwin":  # macOS
    ffmpeg_path = get_bundle_path('ffmpeg/ffmpeg')
else:
    raise FileNotFoundError("FFmpeg path not found. Please ensure FFmpeg is bundled with the executable.")

# Function to check if the file type is allowed
ALLOWED_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv']
def allowed_file(filename):
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)

def select_file():
# Select input video file to be subtitled
    global selected_file
    selected_file = fd.askopenfilename(title="Select video file to subtitle")
    """ To auto sub without needing additional button
    if filename:  # Ensure a file was selected
    sub(filename) 
    """
    if allowed_file(selected_file):
        inputfile.set('Input video: '+os.path.basename(selected_file))
    else:
        inputfile.set(f"Invalid file type. Please select a file with one of the following extensions: {', '.join(ALLOWED_EXTENSIONS)}")
   

def sub():
# Transcribe and translate using whisper
    global selected_file
    if not selected_file:
        print("No file selected!")  # Handle case where no file is selected
        return
    # Start progress bar
    srt_prog_txt.set("Generating SRT")
    srt_prog.start(20)
    

    model = whisper.load_model('small')
    result = model.transcribe(selected_file, task="translate")
    segments = result['segments']

    srt_entries = []
    for idx, seg in enumerate(segments):
        start = timedelta(seconds=seg['start'])
        end = timedelta(seconds=seg['end'])
        srt_entry = srt.Subtitle(index=idx, start=start, end=end, content=seg['text'])
        srt_entries.append(srt_entry)

    srt_filename = selected_file + ".srt"
    with open(srt_filename, "w") as f:
        f.write(srt.compose(srt_entries))

    # End progress bar and update stats
    srt_prog.stop()
    srt_prog_txt.set("Created SRT")

def burn_subs():
    """Burn subtitles into the selected video using FFmpeg"""
    global selected_file
    if not selected_file:
        print("No file selected!")  # Handle case where no file is selected
        return

    root.after(0, lambda: burn_prog_txt.set('Burning subtitles'))  # Ensure the text update is done on the main thread
    root.after(0, lambda: burn_prog.start(20))

    # Generate the subtitle file if it doesn't exist
    srt_filename = selected_file + ".srt"
    if not os.path.exists(srt_filename):
        print("SRT file does not exist. Generating subtitles first.")
        sub()
    

    # Open a Save As dialog to select the output video file path
    output_file = fd.asksaveasfilename(defaultextension=".mp4",
                                       filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")],
                                       title="Save the subbed video as")
    if not output_file:
        print("No output file selected!")  # Handle case where no file is selected
        return

    # Construct the FFmpeg command to burn the subtitles into the video
    ffmpeg_command = [
        ffmpeg_path, 
        "-i", selected_file,  # Input video
        "-i", srt_filename,  # Input subtitle file
        "-c:v", "libx264",  # Video codec
        "-c:a", "aac",  # Audio codec
        "-c:s", "mov_text",  # Subtitle codec for MP4
        "-y",  # Overwrite output file if it already exists
        "-vf", f"subtitles={srt_filename}",  # Using subtitles filter for hardcoding subtitles
        output_file  # Output file path
    ]

    def run_ffmpeg():
        try:
            subprocess.run(ffmpeg_command, check=True)
            # Once FFmpeg finishes, stop the progress bar and update the text
            root.after(0, lambda: burn_prog.stop())
            root.after(0, lambda: burn_prog_txt.set('Finished'))
            print(f"Subtitles successfully burned into the video: {output_file}")
        except subprocess.CalledProcessError as e:
            root.after(0, lambda: burn_prog.stop())
            root.after(0, lambda: burn_prog_txt.set('Error'))
            print(f"Error burning subtitles into the video: {e}")

    # Start FFmpeg process in a separate thread to prevent blocking the GUI
    threading.Thread(target=run_ffmpeg).start()

# Setting up GUI 
root = Tk()
root.title("sub-gui")
#root.minsize(300,200)

# Setting up main window of gui
mainframe = ttk.Frame(root, padding=(10,10))
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))

# Settings for button column
row_w = 1
col_w = 0
b_pady = (10,15)
b_padx = 15
b_sticky = EW
# Settings for text/label/progress bar column 
t_pady = 20
t_padx = 15
t_sticky = NS
# Weight changes whether the rows/columns change when window size changes
mainframe.columnconfigure(1, weight=0)
mainframe.columnconfigure(2, weight=1)
mainframe.rowconfigure(1, weight=row_w)
mainframe.rowconfigure(2, weight=row_w)
mainframe.rowconfigure(3, weight=row_w)
mainframe.rowconfigure(4, weight=row_w)
mainframe.rowconfigure(5, weight=row_w)

# Building file selector for video input choice
input_video_button = ttk.Button(mainframe, text="Input video", command=select_file)
input_video_button.grid(column=1, row=1, columns=2, sticky=b_sticky, pady=b_pady, padx=b_padx)

generate_srt_button = ttk.Button(mainframe, text="Generate SRT (optional)", command=lambda: threading.Thread(target=sub).start())
generate_srt_button.grid(column=1, row=3, columns=2, sticky=b_sticky, pady=10, padx=b_padx)

sub_video_button = ttk.Button(mainframe, text="Generate subbed video", command=lambda: threading.Thread(target=burn_subs).start())
sub_video_button.grid(column=1, row=5, columns=2, sticky=b_sticky, pady=b_pady, padx=b_padx)

# Labels & progress bars 
inputfile = StringVar(mainframe, value='No input video selected')
input_label = ttk.Label(mainframe, textvariable=inputfile)
input_label.grid(column=1, row=2, rowspan=1, sticky = t_sticky, pady = 0, padx=t_padx)

# Generate SRT progress bar
srt_prog = ttk.Progressbar(mainframe, mode='indeterminate')
srt_prog.grid(column=1, row=4)
srt_prog_txt = StringVar(value='')
srt_prog_label = ttk.Label(mainframe, textvariable=srt_prog_txt)
srt_prog_label.grid(column=2, row=4, sticky=NS)

# Generate burning progress bar
burn_prog = ttk.Progressbar(mainframe, mode='indeterminate')
burn_prog.grid(column=1, row=6)
burn_prog_txt = StringVar(value='')
burn_prog_label = ttk.Label(mainframe, textvariable=burn_prog_txt)
burn_prog_label.grid(column=2, row=6)

sv_ttk.use_dark_theme()
root.mainloop()

# TO DO
# Progress bars for subtitling and burning 