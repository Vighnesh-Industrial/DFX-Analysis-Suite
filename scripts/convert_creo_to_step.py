"""Utility to convert Creo files to STEP format"""

import argparse
import os
from pathlib import Path

def convert_creo_to_step(input_file, output_file=None):
    """
    Convert Creo .prt or .asm file to STEP format.
    
    Note: This requires Creo to be installed with Python integration.
    For development, this is a placeholder that shows the conversion pattern.
    
    Args:
        input_file (str): Path to Creo file (.prt or .asm)
        output_file (str): Path to output STEP file
    """
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Error: File '{input_file}' not found")
        return False
    
    if input_path.suffix.lower() not in ['.prt', '.asm']:
        print(f"❌ Error: File must be .prt or .asm, got {input_path.suffix}")
        return False
    
    if output_file is None:
        output_file = input_path.stem + '.STEP'
    
    output_path = Path(output_file)
    
    print(f"🔄 Converting {input_file} to STEP format...")
    
    try:
        # Method 1: Using Creo Python integration (requires Creo installed)
        try:
            import pro_engineer
            proe = pro_engineer.ProEngineer()
            proe.open(str(input_path))
            proe.export_step(str(output_path))
            proe.close()
            print(f"✅ Successfully converted to {output_file}")
            return True
        except ImportError:
            print("⚠️  Creo Pro/Engineer not available")
        
        # Method 2: Command-line Creo conversion (if Creo is installed)
        # Requires: c:/Program Files/PTC/Creo 8.0/bin/xtop.exe
        import subprocess
        creo_path = "c:/Program Files/PTC/Creo 8.0/bin/xtop.exe"
        
        if os.path.exists(creo_path):
            cmd = f'"{creo_path}" -i "{input_path}" -o "{output_path}" -t step'
            subprocess.run(cmd, check=True)
            print(f"✅ Successfully converted to {output_file}")
            return True
        else:
            print("❌ Creo not found at", creo_path)
        
        # Fallback: Use generic mesh conversion (lower quality)
        print("🔄 Using fallback mesh conversion (FreeCAD)...")
        try:
            import FreeCAD
            doc = FreeCAD.open(str(input_path))
            doc.saveAs(str(output_path), 'STEP')
            FreeCAD.closeDocument(doc.Name)
            print(f"✅ Conversion complete (mesh quality): {output_file}")
            return True
        except:
            print("❌ Conversion failed: Please install Creo or FreeCAD")
            return False
    
    except Exception as e:
        print(f"❌ Conversion error: {str(e)}")
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert Creo files to STEP format')
    parser.add_argument('input_file', help='Path to Creo file (.prt or .asm)')
    parser.add_argument('-o', '--output', help='Output STEP file path (optional)')
    
    args = parser.parse_args()
    
    success = convert_creo_to_step(args.input_file, args.output)
    exit(0 if success else 1)
