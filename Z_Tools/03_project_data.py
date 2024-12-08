import os

TARGET_FOLDER = "D:/ULTIMA/MODS/ultima_online_mods"

def gather_folder_data(root_folder):
    groups = []
    objects = []
    
    # Traverse the main folder and its subfolders
    for folder_name in os.listdir(root_folder):
        folder_path = os.path.join(root_folder, folder_name)
        
        # Check if it's a directory and one of the main folders
        if os.path.isdir(folder_path) and folder_name in ['ART', 'UI', 'ENV']:
            # Iterate through subfolders (objects)
            for subfolder_name in os.listdir(folder_path):
                subfolder_path = os.path.join(folder_path, subfolder_name)
                
                # Check if the subfolder is a directory
                if os.path.isdir(subfolder_path):
                    groups.append(folder_name)
                    objects.append(subfolder_name)

    return groups, objects

def write_to_file(file_name, data_list):
    # Write each item from the data list to a new line in the text file
    with open(file_name, 'w') as f:
        for item in data_list:
            f.write(f"{item}\n")

def main():
    # Set the root folder where the script is run
    root_folder = os.getcwd()  # Or specify the root folder if needed
    root_folder = TARGET_FOLDER

    # Gather group and object data
    groups, objects = gather_folder_data(root_folder)
    
    # Write the data to their respective files
    write_to_file('group.txt', groups)
    write_to_file('object.txt', objects)
    
    print("Data successfully saved to group.txt and object.txt")

if __name__ == "__main__":
    main()
