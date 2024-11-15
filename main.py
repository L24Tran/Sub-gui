from tkinter import * 
from tkinter import ttk
from tkinter import filedialog as fd

import whisper 
import srt
from datetime import timedelta
import subprocess
import os


selected_file = ""

def select_file():
# Select input video file to be subtitled
    global selected_file
    selected_file = fd.askopenfilename()
    """ To auto sub without needing additional button
    if filename:  # Ensure a file was selected
    sub(filename) 
    """

def sub():
# Transcribe and translate using whisper
    global selected_file
    if not selected_file:
        print("No file selected!")  # Handle case where no file is selected
        return

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

def burn_subs():
    """Burn subtitles into the selected video using FFmpeg"""
    global selected_file
    if not selected_file:
        print("No file selected!")  # Handle case where no file is selected
        return

    # Generate the subtitle file if it doesn't exist
    srt_filename = selected_file + ".srt"
    if not os.path.exists(srt_filename):
        print("SRT file does not exist. Please generate subtitles first.")
        return

    # Open a Save As dialog to select the output video file path
    output_file = fd.asksaveasfilename(defaultextension=".mp4",
                                       filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")],
                                       title="Save the subbed video as")
    if not output_file:
        print("No output file selected!")  # Handle case where no file is selected
        return

    # Construct the FFmpeg command to burn the subtitles into the video
    ffmpeg_command = [
        "ffmpeg", 
        "-i", selected_file,  # Input video
        "-i", srt_filename,  # Input subtitle file
        "-c:v", "libx264",  # Video codec
        "-c:a", "aac",  # Audio codec
        "-c:s", "mov_text",  # Subtitle codec for MP4
        "-y",  # Overwrite output file if it already exists
        "-vf", f"subtitles={srt_filename}",  # Using subtitles filter for hardcoding subtitles
        output_file  # Output file path
    ]


    try:
        # Run the FFmpeg command using subprocess
        subprocess.run(ffmpeg_command, check=True)
        print(f"Subtitles successfully burned into the video: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error burning subtitles into the video: {e}")


root = Tk()
root.title("sub-gui")

# Setting up main window of gui
mainframe = ttk.Frame(root, padding=(10,20))
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Building file selector for video input choice
input_video_button = ttk.Button(root, text="Input video", command=select_file)
input_video_button.grid(columns=1, rows=1)

generate_srt_button = ttk.Button(root, text="Generate SRT", command=sub)
generate_srt_button.grid(columns=1, rows=2)

sub_video_button = ttk.Button(root, text="Generate subbed video", command=burn_subs)
sub_video_button.grid(columns=1, rows=3)

root.mainloop()
