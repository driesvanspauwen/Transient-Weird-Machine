"""Generate optimized binaries for each gate using best configurations from grid search results."""
import subprocess
import re
import os
import sys

# Best configurations from grid search results
BEST_CONFIGS = {
    'AND': {'threshold': 225, 'delay': 128},
    'OR': {'threshold': 275, 'delay': 128},
    'ASSIGN': {'threshold': 250, 'delay': 128},
    'NOT': {'threshold': 150, 'delay': 512},
    'NAND': {'threshold': 100, 'delay': 512},
    'XOR': {'threshold': 275, 'delay': 1024},
    'MUX': {'threshold': 275, 'delay': 256}
}

GATE_FUNCTIONS = {
    'AND': ('do_and_gate', 2),
    'OR': ('do_or_gate', 2),
    'ASSIGN': ('do_assign_gate', 1),
    'NOT': ('do_not_gate', 1),
    'NAND': ('do_nand_gate', 2),
    'XOR': ('do_xor_gate', 2),
    'MUX': ('do_mux_gate', 3)
}

def create_optimized_binary(gate_name, threshold, delay):
    """Create an optimized binary for a specific gate with given threshold and delay"""
    print(f"Creating optimized binary for {gate_name} gate (T={threshold}, D={delay})...")
    
    # Get gate function and input count
    gate_function, input_count = GATE_FUNCTIONS[gate_name]
    
    # Read original compose.cpp
    with open('gates/compose.cpp', 'r') as f:
        content_compose = f.read()
    
    # Modify parameters in compose.cpp
    modified_content_compose = re.sub(r'#define THRESHOLD \d+', f'#define THRESHOLD {threshold}', content_compose)
    modified_content_compose = re.sub(r'#define DELAY \d+', f'#define DELAY {delay}', modified_content_compose)
    
    # Write temporary compose file
    temp_compose_file = f'gates/compose_{gate_name.lower()}.cpp'
    with open(temp_compose_file, 'w') as f:
        f.write(modified_content_compose)

    # Read original main.cpp
    with open('main.cpp', 'r') as f:
        content_main = f.read()
    
    # Modify parameters and gate-specific content in main.cpp
    modified_content_main = re.sub(r'#define THRESHOLD \d+', f'#define THRESHOLD {threshold}', content_main)
    modified_content_main = re.sub(r'#define DELAY \d+', f'#define DELAY {delay}', modified_content_main)
    modified_content_main = re.sub(r'#include "gates/compose.cpp"', f'#include "gates/compose_{gate_name.lower()}.cpp"', modified_content_main)
    
    # Replace the gate testing template
    modified_content_main = re.sub(r'test_gate\("GATE_NAME_PLACEHOLDER", GATE_FUNCTION_PLACEHOLDER, GATE_INPUTS_PLACEHOLDER\);', 
                                 f'test_gate("{gate_name}", {gate_function}, {input_count});', modified_content_main)

    # Write temporary main file
    temp_main_file = f'main_{gate_name.lower()}.cpp'
    with open(temp_main_file, 'w') as f:
        f.write(modified_content_main)
    
    try:
        # Clean previous builds
        subprocess.run(['make', 'clean'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Ensure build directory exists
        if not os.path.exists('build'):
            os.makedirs('build')
        
        # Ensure optimal-binaries directory exists
        if not os.path.exists('optimal-binaries'):
            os.makedirs('optimal-binaries')
            
        # Compile compose object file
        compose_obj = f'build/compose_{gate_name.lower()}.o'
        subprocess.run(['g++', '-O2', '-D', 'INTEL', '-c', '-o', compose_obj, temp_compose_file], 
                      check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Compile main program and place in optimal-binaries folder
        binary_name = f'optimal-binaries/main_{gate_name.lower()}.elf'
        subprocess.run(['g++', '-O2', '-D', 'INTEL', '-o', binary_name, temp_main_file, compose_obj, '-lm'], 
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"✓ Successfully created {binary_name}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error creating binary for {gate_name}: {e}")
        return False
        
    finally:
        # Clean up temporary files
        if os.path.exists(temp_main_file):
            os.remove(temp_main_file)
        if os.path.exists(temp_compose_file):
            os.remove(temp_compose_file)

def main():
    print("Generating optimized binaries for each gate...")
    print("=" * 50)
    
    successful_builds = 0
    total_builds = len(BEST_CONFIGS)
    
    for gate_name, config in BEST_CONFIGS.items():
        success = create_optimized_binary(gate_name, config['threshold'], config['delay'])
        if success:
            successful_builds += 1
        print()  # Add spacing between gates
    
    print("=" * 50)
    print(f"Build Summary: {successful_builds}/{total_builds} binaries created successfully")
    
    if successful_builds == total_builds:
        print("✓ All optimized binaries have been created in the 'optimal-binaries' folder")
    else:
        print("⚠ Some binaries failed to build. Check error messages above.")
    
    # List the created binaries
    if os.path.exists('optimal-binaries'):
        binaries = [f for f in os.listdir('optimal-binaries') if f.endswith('.elf')]
        if binaries:
            print("\nCreated binaries:")
            for binary in sorted(binaries):
                print(f"  - {binary}")

if __name__ == "__main__":
    main()