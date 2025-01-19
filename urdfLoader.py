import xml.etree.ElementTree as ET
import json

def parse_urdf_to_json(urdf_file_path, output_json_path=None):
    """
    Parses a URDF file and converts it to a JSON structure.
    
    Args:
        urdf_file_path (str): Path to the .urdf file.
        output_json_path (str, optional): Path to save the generated JSON file. Defaults to None.
    
    Returns:
        dict: JSON-like dictionary representation of the URDF file.
    """
    def parse_element(element):
        """
        Recursively parse an XML element into a dictionary.
        """
        parsed_data = {"tag": element.tag, "attributes": element.attrib, "children": []}
        for child in element:
            parsed_data["children"].append(parse_element(child))
        if element.text and element.text.strip():
            parsed_data["text"] = element.text.strip()
        return parsed_data

    try:
        
        tree = ET.parse(urdf_file_path)
        root = tree.getroot()
        urdf_json = parse_element(root)
        
        if output_json_path:
            with open(output_json_path, "w") as json_file:
                json.dump(urdf_json, json_file, indent=4)
        
        return urdf_json
    
    except Exception as e:
        print(f"Error parsing URDF file: {e}")
        return None


urdf_file = "r2b_control.urdf" 
output_json = "robot.json"  
urdf_data = parse_urdf_to_json(urdf_file, output_json)

if urdf_data:
    print("URDF successfully converted to JSON!")
