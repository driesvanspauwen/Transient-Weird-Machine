"""Test combinations of threshold and delay values for all gates"""
import subprocess
import re
import os
import sys
import time

GATE_NAMES = ['AND', 'OR', 'ASSIGN', 'NOT', 'NAND', 'XOR', 'MUX']
THRESHOLDS = range(100, 301, 25)
DELAYS = [32, 48, 64, 96, 128, 192, 256, 512, 1024]

# Number of trials of main.elf for every combination of threshold and delay
AMT_TRIALS = 10 # (see `static struct argp_option options[]` in main.cpp)

def test_parameters(threshold, delay):
    """Test a specific combination of threshold and delay values for all gates"""
    # Modify parameters in compose.cpp
    with open('gates/compose.cpp', 'r') as f:
        content_compose = f.read()
    
    modified_content_compose = re.sub(r'#define THRESHOLD \d+', f'#define THRESHOLD {threshold}', content_compose)
    modified_content_compose = re.sub(r'#define DELAY \d+', f'#define DELAY {delay}', modified_content_compose)
    
    with open('gates/compose_temp.cpp', 'w') as f:
        f.write(modified_content_compose)

    # Modify parameters in main.cpp
    with open('main.cpp', 'r') as f:
        content_main = f.read()
    
    modified_content_main = re.sub(r'#define THRESHOLD \d+', f'#define THRESHOLD {threshold}', content_main)
    modified_content_main = re.sub(r'#define DELAY \d+', f'#define DELAY {delay}', modified_content_main)
    modified_content_main = re.sub(r'#include "gates/compose.cpp"', r'#include "gates/compose_temp.cpp"', modified_content_main)

    with open('main_temp.cpp', 'w') as f:
        f.write(modified_content_main)
    
    # Compile the modified file
    try:
        subprocess.run(['make', 'clean'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Ensure build directory exists
        if not os.path.exists('build'):
            os.makedirs('build')
            
        # Compile compose.o
        subprocess.run(['g++', '-O2', '-D', 'INTEL', '-c', '-o', 'build/compose.o', 'gates/compose.cpp'], 
                      check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Compile main program
        subprocess.run(['g++', '-O2', '-D', 'INTEL', '-o', 'main_temp.elf', 'main_temp.cpp', 'build/compose.o', '-lm'], 
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Run the executable
        result = subprocess.run(['./main_temp.elf', '-t', str(AMT_TRIALS)], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Extract accuracy for all gates
        gate_accuracies = {}
        
        for line in result.stdout.splitlines():
            if "Correct rate: (avg, std)" in line:
                idx = result.stdout.splitlines().index(line)
                prev_line = result.stdout.splitlines()[idx-1]
                for gate in GATE_NAMES:
                    if f"=== {gate} gate" in prev_line:
                        accuracy = float(re.search(r'\(([0-9.]+)%', line).group(1))
                        gate_accuracies[gate] = accuracy
                        break
        
        return gate_accuracies
    
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation or execution: {e}")
        return {}
    finally:
        # Clean up
        if os.path.exists('main_temp.cpp'):
            os.remove('main_temp.cpp')
        if os.path.exists('main_temp.elf'):
            os.remove('main_temp.elf')
        if os.path.exists('gates/compose_temp.cpp'):
            os.remove('gates/compose_temp.cpp')

def main():
    # Create a separate file for each gate to store results
    result_files = {}
    for gate in GATE_NAMES:
        filename = f"grid-search-results/{gate.lower()}_results.txt"
        result_files[gate] = open(filename, "w")
        result_files[gate].write(f"# Results for {gate} gate\n")
        
        # Fixed-width format for header row - using proper alignment
        header = "T\\D".ljust(10)
        for delay in DELAYS:
            header += str(delay).ljust(10)
        result_files[gate].write(header + "\n")
    
    print("Testing combinations of threshold and delay values for all gates...")
    print(f"Total combinations to test: {len(THRESHOLDS) * len(DELAYS)}")
    
    counter = 0
    total = len(THRESHOLDS) * len(DELAYS)
    
    start_time = time.time()
    
    # Test each combination
    for threshold in THRESHOLDS:
        # Initialize a row for each gate with fixed-width format
        rows = {gate: str(threshold).ljust(10) for gate in GATE_NAMES}
        
        for delay in DELAYS:
            counter += 1
            
            # Calculate and display ETA
            elapsed = time.time() - start_time
            if counter > 1:
                eta = elapsed / counter * (total - counter)
                eta_min = int(eta / 60)
                eta_sec = int(eta % 60)
                print(f"Testing combination {counter}/{total} (T={threshold}, D={delay}), ETA: {eta_min}m {eta_sec}s", end="\r")
            else:
                print(f"Testing combination {counter}/{total} (T={threshold}, D={delay})", end="\r")
            
            gate_accuracies = test_parameters(threshold, delay)
            
            # Add results to each gate's row with fixed-width format
            for gate in GATE_NAMES:
                accuracy = gate_accuracies.get(gate, 0)
                rows[gate] += f"{accuracy:.1f}".ljust(10)
        
        # Write each gate's completed row to its result file
        for gate in GATE_NAMES:
            result_files[gate].write(rows[gate] + "\n")
            result_files[gate].flush()  # Ensure data is written even if the script is interrupted
    
    print("\nTesting complete. Results saved to individual files.")
    
    # Close all result files
    for file in result_files.values():
        file.close()
    
    # Generate a summary of the best configurations and save to output.txt
    best_configs = []
    print("\nBest configurations for each gate:")
    for gate in GATE_NAMES:
        best_threshold = 0
        best_delay = 0
        best_accuracy = 0
        
        with open(f"grid-search-results/{gate.lower()}_results.txt", "r") as f:
            lines = f.readlines()[2:]  # Skip header lines
            
            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue
                    
                threshold = int(parts[0])
                
                # Extract all accuracy values (every value after the threshold)
                accuracies = []
                for value in parts[1:]:
                    try:
                        accuracies.append(float(value))
                    except ValueError:
                        pass
                
                # Find best accuracy in this row
                for i, accuracy in enumerate(accuracies):
                    if i < len(DELAYS) and accuracy > best_accuracy:
                        best_accuracy = accuracy
                        best_threshold = threshold
                        best_delay = DELAYS[i]
        
        result_line = f"{gate}: Threshold={best_threshold}, Delay={best_delay}, Accuracy={best_accuracy:.1f}%"
        print(result_line)
        best_configs.append(result_line)
    
    # Write best configurations to output.txt
    with open("output.txt", "w") as f:
        f.write("Best configurations for each gate:\n")
        for config in best_configs:
            f.write(config + "\n")
    
    print("\nBest configurations saved to output.txt")

if __name__ == "__main__":
    main()