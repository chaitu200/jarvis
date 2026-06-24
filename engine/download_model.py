import os
import urllib.request
import zipfile

def download_and_extract_model():
    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    zip_path = "vosk-model.zip"
    extract_dir = "model"
    
    if os.path.exists(extract_dir):
        print("Model already exists.")
        return
        
    print("Downloading Vosk model (~40MB)... This might take a minute.")
    urllib.request.urlretrieve(model_url, zip_path)
    print("Download complete. Extracting...")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(".")
        
    os.rename("vosk-model-small-en-us-0.15", extract_dir)
    os.remove(zip_path)
    print("Model extraction complete.")

if __name__ == "__main__":
    download_and_extract_model()
