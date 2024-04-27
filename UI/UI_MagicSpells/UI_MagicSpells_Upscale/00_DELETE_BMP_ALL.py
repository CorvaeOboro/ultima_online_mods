import os

def delete_bmp_files(folder_path):
    """
    Delete all BMP files in the specified folder.
    """
    for filename in os.listdir(folder_path):
        if filename.endswith(".bmp") or filename.endswith(".BMP"):
            file_path = os.path.join(folder_path, filename)
            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

def main():
    """
    Main function to delete BMP files in the current folder.
    """
    current_folder = os.getcwd()
    delete_bmp_files(current_folder)

if __name__ == "__main__":
    main()
