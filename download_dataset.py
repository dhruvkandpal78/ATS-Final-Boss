import kagglehub
import shutil
import os

def main():
    print("Downloading dataset from Kaggle...")
    path = kagglehub.dataset_download("snehaanbhawal/resume-dataset")
    print("Downloaded to:", path)

    dest_dir = os.path.join("data", "raw", "resume-dataset")
    os.makedirs(dest_dir, exist_ok=True)
    
    print(f"Copying to project folder: {dest_dir}")
    shutil.copytree(path, dest_dir, dirs_exist_ok=True)
    print("Copy complete!")

if __name__ == "__main__":
    main()
