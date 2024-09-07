import subprocess
import argparse
import os
import colorama
import json
import sys
from modules.ai.huggingface_ai import HuggingFaceAI

colorama.init()

user_dir          = os.getcwd()
clarification_dir = os.path.dirname(os.path.realpath(__file__))

def print_info(str):
    print(f"{colorama.Fore.YELLOW}{str}{colorama.Style.RESET_ALL}")

def print_raw(str, is_error=False):
    str = str.rstrip('\n')
    if is_error:
        print(f"{colorama.Fore.RED}{str}{colorama.Style.RESET_ALL}")
    else:
        print(f"{colorama.Fore.LIGHTBLACK_EX}{str}{colorama.Style.RESET_ALL}")

def print_special(str):
    print(f"{colorama.Fore.CYAN}{str}{colorama.Style.RESET_ALL}")

def read_file(file_path):
    full_path = os.path.join(user_dir, file_path)
    print_info(f"  Reading file: {full_path}")
    if os.path.exists(full_path):
        with open(full_path, 'r') as file:
            return file.read()
    else:
        return None

def load_config():
    config_path = os.path.join(clarification_dir, 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as config_file:
                return json.load(config_file)
        except json.JSONDecodeError:
            print(f"Error parsing configuration file at {config_path}. Using default values.")
    return {}

def read_context_files(context_json_path):
    print_info(f"Reading context files (specified in {context_json_path})...")
    try:
        with open(context_json_path, 'r') as context_file:
            context = json.load(context_file)
        res = ""
        for file_path in context.get('context_files', []):
            full_path = os.path.join(user_dir, file_path)
            if os.path.isfile(full_path):
                res += f"Content of {file_path}:\n{read_file(file_path)}\n\n"
            else:
                print(f"Warning: Context file not found: {full_path}")
        print_info("Context files read complete")
        return res
    except json.JSONDecodeError as e:
        print(f"Error parsing context JSON file: {e}")
    except FileNotFoundError:
        print(f"Context JSON file not found: {context_json_path}")
    except Exception as e:
        print(f"Unexpected error reading context files: {e}")
    return ""

def get_ai(ai_type, config):
    access_token   = config.get('hf_access_token')
    max_new_tokens = config.get('max_new_tokens', 1024)
    temperature    = config.get('temperature', 0.7)

    model_map = {
        "distilgpt2": "distilgpt2",
        "gpt2":       "gpt2",
        "gpt2-large": "gpt2-large",
        "neo":        "EleutherAI/gpt-neo-1.3B",
        "j":          "EleutherAI/gpt-j-6B",
        "meta-llama": "meta-llama/Meta-Llama-3-8B-Instruct",
        "bloom":      "bigscience/bloom-560m",
        "flan-t5":    "google/flan-t5-base",
        "opt":        "facebook/opt-350m",
        "dolly":      "databricks/dolly-v2-3b",
        "pythia":     "EleutherAI/pythia-410m"
    }

    model_name = model_map.get(ai_type.lower(), 'meta-llama/Meta-Llama-3-8B-Instruct')

    print_info(f"Initialising AI client (model: '{model_name}', max_new_tokens: {max_new_tokens}, temperature: {temperature})...")
    ai = HuggingFaceAI(
        model_name     = model_name,
        max_new_tokens = max_new_tokens,
        temperature    = temperature,
        access_token   = access_token
    )
    print_info("AI client initialised")
    return ai

def run_command(command, suppress_output=False):
    print_info(f"Running command '{command}'...")
    try:
        os.chdir(user_dir)
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            bufsize=1, 
            universal_newlines=True
        )
        
        stdout_output = []
        stderr_output = []
        
        for stdout_line in process.stdout:
            stdout_output.append(stdout_line)
            if not suppress_output:    
                print_raw(stdout_line, is_error=False)
        
        for stderr_line in process.stderr:
            stderr_output.append(stderr_line)
            if not suppress_output:
                print_raw(stderr_line, is_error=True)

        process.wait()
        print_info("Command execution complete")
        return ''.join(stdout_output), ''.join(stderr_output)
    except Exception as e:
        return None, f"An error occurred while running the command: {e}"
    finally:
        # Change back to the Clarification script's directory
        os.chdir(clarification_dir)



def main():
    config = load_config()
    
    parser = argparse.ArgumentParser(description="Run a command and get AI-enhanced output.")
    parser.add_argument("command", type=str, help="The command to execute (e.g., a .bat file)")
    parser.add_argument("--model", type=str, default=config.get('model', 'meta-llama'), help="Specify AI model to use")
    parser.add_argument("--suppress-raw", action="store_true", help="Suppress raw output before AI analysis")
    
    args = parser.parse_args()

    ai = get_ai(args.model, config)
    
    ai.add_to_prompt("You are an AI assistant tasked with clarifying command outputs. ")
    ai.add_to_prompt("Your goal is to interpret the command output and present it in a human-readable form. ")
    ai.add_to_prompt("If provided, also consider the contents of the input file to provide more context in your analysis.\n\n")
    
    if os.path.isfile(os.path.join(user_dir, args.command)):
        print_info(f"Reading command file...")
        command_file_contents = read_file(args.command)
        if command_file_contents:
            ai.add_to_prompt(f"Input file contents:\n{command_file_contents}\n\n")

    context_json_path = os.path.join(user_dir, "clarification_context.json")
    if os.path.isfile(context_json_path):
        context_files_contents = read_context_files(context_json_path)
        if context_files_contents:
            ai.add_to_prompt(f"Context files contents:\n{context_files_contents}\n\n")
    
    stdout, stderr = run_command(command=args.command, suppress_output=args.suppress_raw)

    if stdout:
        ai.add_to_prompt(f"Command output:\n{stdout}\n\n")
    if stderr:
        ai.add_to_prompt(f"Error output:\n{stderr}\n\n")
    
    ai.add_to_prompt("Please provide a clear, concise interpretation of this output in human-readable form.")

    print_special("AI Analysis:")
    ai.print_response()
    print()
    print_special("End of AI Analysis")
    ai.clear_prompt()

if __name__ == "__main__":
    main()
