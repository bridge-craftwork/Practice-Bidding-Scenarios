import os
import argparse

parser = argparse.ArgumentParser(description="Extract dealer code")
parser.add_argument("--scenario", type=str, help="Name of scenario is required")
parser.add_argument("--pbn", type=str, help="PBN file to process (default: ../pbn/<scenario>.pbn)")
args = parser.parse_args()
scenario = str(args.scenario)

def process():
    '''
    /*************  ✨ Codeium Command ⭐  *************/
    
    Processes the given file by reading its content, splitting it into lines,
    and prepending '% ' to each line that is not a blank line or a PBN keyword/value.
    Lines starting with '#' will have the '#' replaced with '%'.
    The processed lines are then written back to the file.

    Args:
        filepath (str): The path to the file to be processed.
    
    /******  2cb70efe-8b28-4953-a2f2-46826fe61a9e  *******/
    '''

    with open(file_path, 'r') as i_file:
        # Split the string into individual lines
        content = i_file.read()
        lines = content.strip().split('\n')

        # Prepend '% ' to each line that is not a blank line or a pbn keyword/value [...]
        processed_lines = []
        for line in lines:
            if not (line.startswith('[') or line.strip() == ''):
                if line.startswith('#'):
                    line = '%' + line[1:]
                elif not line.startswith('%'):
                    line = '% ' + line
            processed_lines.append(line)

    with open(file_path, 'w') as o_file:
        # Join the processed lines back into a single string
        result = '\n'.join(processed_lines)
        o_file.write(result)

# Do a single scenario
filename = scenario + '.pbn'
file_path = args.pbn or os.path.join('..', 'pbn', filename)
if os.path.isfile(file_path):
    process()
else:
    print(f"Scenario does not exist: {scenario}")

