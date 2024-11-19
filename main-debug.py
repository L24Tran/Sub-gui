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

import os
import sys
import shutil
import tempfile
import subprocess
import logging
import traceback


selected_file = ""

# Define the function to get the correct file paths in the bundled app
def get_bundle_path(filename):
    if getattr(sys, 'frozen', False):  # Running in a bundled executable
        base_path = sys._MEIPASS  # This points to the temporary folder where PyInstaller extracted files
    else:  # Running in development mode
        base_path = os.path.dirname(__file__)  # Current directory of the script
    return os.path.join(base_path, filename)

"""
# Set ffmpeg_path based on the platform and bundle
if sys.platform == "win32" or sys.platform == "win64":  # Windows
    ffmpeg_path = get_bundle_path('ffmpeg\\ffmpeg\\bin\\ffmpeg.exe')
elif sys.platform == "darwin":  # macOS
    ffmpeg_path = get_bundle_path('ffmpeg/ffmpeg')
else:
    srt_prog_txt.set("FFmpeg path not found. Issue with bundling.")
    raise FileNotFoundError("FFmpeg path not found. Please ensure FFmpeg is bundled with the executable.")
"""

def extract_ffmpeg():
    if sys.platform == "win32" or sys.platform == "win64":  # Windows
        # The relative path where FFmpeg is bundled within the PyInstaller package
        ffmpeg_bin = get_bundle_path('ffmpeg\\ffmpeg.exe')
        
        if not os.path.exists(ffmpeg_bin):
            raise FileNotFoundError(f"FFmpeg executable not found at expected location: {ffmpeg_bin}")

        # Create a temporary directory to store FFmpeg
        temp_dir = tempfile.mkdtemp()
        ffmpeg_temp_path = os.path.join(temp_dir, 'ffmpeg.exe')

        # Copy FFmpeg executable to the temp folder
        shutil.copy(ffmpeg_bin, ffmpeg_temp_path)

        # Add the directory containing FFmpeg to the system's PATH
        os.environ["PATH"] += os.pathsep + temp_dir
        
        return ffmpeg_temp_path
    else:
        # Handle macOS or Linux platform here
        ffmpeg_path = get_bundle_path('ffmpeg/ffmpeg')
        if not os.path.exists(ffmpeg_path):
            raise FileNotFoundError(f"FFmpeg executable not found: {ffmpeg_path}")
        return ffmpeg_path

def print_temp_dir():
    if getattr(sys, 'frozen', False):
        print(f"Running in a PyInstaller bundle, unpacked to: {sys._MEIPASS}")
    else:
        print("Not running in a PyInstaller bundle.")
        
print_temp_dir()

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


def log_error(message):
    print(message)  # Still print to console
    logging.error(message)

def check_file_exists(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
    return True

def sub():
# Transcribe and translate using whisper
    global selected_file
    if not selected_file:
        print("No file selected!")  # Handle case where no file is selected
        return
    
    ffmpeg_path = extract_ffmpeg() 

    # Start progress bar
    srt_prog_txt.set("Generating SRT")
    srt_prog.start(20)
    
    model = whisper.load_model('small')

    if not check_file_exists(selected_file):
        log_error(f"Video file not found: {selected_file}")
        srt_prog.stop()
        srt_prog_txt.set("Error")
        return
    
    
    print(f"FFmpeg path: {ffmpeg_path}")
    if not os.path.exists(ffmpeg_path):
        print("FFmpeg executable not found!")
    else:
        print("FFmpeg executable found.")

    #try:
    #    subprocess.run(['ffmpeg', '-version'], check=True)
    #except FileNotFoundError:
    #    print("Error: FFmpeg is not installed.")

    try:
        result = model.transcribe(selected_file, task="translate")
        print("Transcription successful")
        print(result)  # Check the result
    except Exception as e:
        print(f"Error transcribing file: {e}")
        traceback.print_exc()
        return

    #try:
        result = model.transcribe(selected_file, task="translate")
    #except OSError as e:
        print(f'OS ERROR: {e}')
        traceback.print_exc()
        return
    #except FileNotFoundError as e:
        print("File not found error:")
        print(f"Error details: {e}")
        traceback.print_exc()
        return
    #except Exception as e:
        log_error(f"An error occurred: {e}")
        srt_prog.stop()
        srt_prog_txt.set("Error")
        return

    segments = result['segments']

    srt_entries = []
    for idx, seg in enumerate(segments):
        start = timedelta(seconds=seg['start'])
        end = timedelta(seconds=seg['end'])
        srt_entry = srt.Subtitle(index=idx, start=start, end=end, content=seg['text'])
        srt_entries.append(srt_entry)

    srt_filename = selected_file + ".srt"
    with open(srt_filename, "w", encoding="utf-8") as f:
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

    ffmpeg_path = extract_ffmpeg() 
    ffmpeg_path = os.path.abspath(ffmpeg_path)
    srt_filename = os.path.abspath(srt_filename)  # Get absolute path of the SRT file
    output_file = os.path.abspath(output_file)  # Get absolute path of the output file
    if sys.platform == 'win32' or sys.platform =='win64':  # Only modify if running on Windows
        srt_filename = srt_filename[3:]  # Remove C: from the start of the path
        output_file = output_file[3:] 
        ffmpeg_path = ffmpeg_path[3:]
    ffmpeg_path = ffmpeg_path.replace("\\", "/")
    srt_filename = srt_filename.replace("\\", "/")  # Replace backslashes with forward slashes for FFmpeg
    output_file = output_file.replace("\\", "/")
    print('Forward slash FFmpeg path: ', ffmpeg_path)
    print('Forward slash SRT path: ', srt_filename)
    print('Forward slash output path: ', output_file)

    # Construct the FFmpeg command to burn the subtitles into the video
    ffmpeg_command = [
        ffmpeg_path, 
        "-i", selected_file,  # Input video
        #"-i", srt_filename,  # Input subtitle file
        #"-c:v", "libx264",  # Video codec
        #"-c:a", "aac",  # Audio codec
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