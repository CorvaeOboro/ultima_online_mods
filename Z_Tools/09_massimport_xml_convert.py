# CLI program to convert a mulpatcher txt file to the UOFiddler MassImport xml format.
# Usage = python convert_data.py -i input.txt -o output.xml -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\"

# python 03_massimport_xml_convert.py -c "item" -i "D:\ULTIMA\MODS\ultima_online_mods\00_ART_ALL_ART_S.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_ART_ALL_ART_S.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 
# python 03_massimport_xml_convert.py -c "gump" -i "D:\ULTIMA\MODS\ultima_online_mods\00_UI_ALL_GUMP.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_UI_ALL_GUMP.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 
# python 03_massimport_xml_convert.py -c "landtile" -i "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_M.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_M.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 
# python 03_massimport_xml_convert.py -c "texture" -i "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_TEX.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_TEX.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 
# python 03_massimport_xml_convert.py -c "item" -i "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_S.txt" -o "D:\ULTIMA\MODS\ultima_online_mods\00_ENV_ALL_ART_S.xml" -p "D:\\ULTIMA\\MODS\\ultima_online_mods\\" 

import argparse
import sys
import os

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Convert data from one text file to another with specified formatting.')
    parser.add_argument('-i', '--input', required=True, help='Path to the input text file.')
    parser.add_argument('-o', '--output', required=True, help='Path to the output XML file.')
    parser.add_argument('-p', '--prefix', required=True, help='Prefix to add to the file paths.')
    parser.add_argument('-c', '--category', required=True, help='Category for the XML tags (e.g., item, gump, landtile, texture).')
    return parser.parse_args()

def process_line(line, prefix, category, line_number):
    """
    Process a single line of the input file.

    Parameters:
        line (str): The line to process.
        prefix (str): The prefix to add to the file paths.
        category (str): The category for the XML tags.
        line_number (int): The current line number in the input file.

    Returns:
        str or None: The formatted line to write to the output file, or None if the line is invalid.
    """
    line = line.strip()
    if not line:
        return None  # Skip empty lines

    # Split the line into item ID and file path
    try:
        item_id_str, file_path = line.split(None, 1)  # Split on the first whitespace
    except ValueError:
        print(f"Warning: Skipping invalid line {line_number}: '{line}'", file=sys.stderr)
        return None  # Skip lines that don't have both item ID and file path

    # Convert item ID from hexadecimal to decimal
    try:
        item_id = int(item_id_str, 16)
    except ValueError:
        print(f"Warning: Invalid item ID on line {line_number}: '{item_id_str}'", file=sys.stderr)
        return None  # Skip invalid item IDs

    # Ensure the prefix ends with a backslash or slash
    if not prefix.endswith(('/', '\\')):
        prefix += '\\'

    # Build the new file path by adding the prefix
    new_file_path = prefix + file_path

    # Return the formatted line using the category
    return f'  <{category} index="{item_id}" file="{new_file_path}" remove="False" />\n'

def convert_data(input_file, output_file, prefix, category):
    """
    Convert data from the input file and write to the output file.

    Parameters:
        input_file (str): Path to the input text file.
        output_file (str): Path to the output XML file.
        prefix (str): Prefix to add to the file paths.
        category (str): Category for the XML tags.
    """
    try:
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            outfile.write("<MassImport>")
            outfile.write("\n")
            for line_number, line in enumerate(infile, 1):
                result = process_line(line, prefix, category, line_number)
                if result:
                    outfile.write(result)
            outfile.write("\n")
            outfile.write("</MassImport>")
        print(f"Data has been successfully converted and written to '{output_file}'.")
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found. Please check the file path.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

def main():
    args = parse_arguments()
    convert_data(args.input, args.output, args.prefix, args.category)

if __name__ == '__main__':
    main()
