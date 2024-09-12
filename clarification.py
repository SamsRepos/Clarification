import subprocess
import argparse
import os
import json

from modules.ai.huggingface_ai import HuggingFaceAI
from modules.util.print_util import print_info, print_raw, print_special

user_dir          = os.getcwd()
clarification_dir = os.path.dirname(os.path.realpath(__file__))

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

def parse_arguments(config):
    class CustomArgumentParser(argparse.ArgumentParser):
        def format_help(self):
            help_text = """
Usage: clarify [OPTIONS] COMMAND

Run a command and get AI-enhanced output.

Options:
  -m, --model MODEL       Specify AI model to use (default: meta-llama)
  -t, --temperature TEMP  Set the temperature for AI generation (default: 0.7)
  -l, --log               Enable logging and specify the log file name
  -u, --user-message      Provide an additional user message for the AI analysis
  -s, --suppress-raw      Suppress raw output before AI analysis
  -h, --help              Show this help message and exit

Arguments:
  COMMAND                 The command to execute (e.g., a .bat file)
"""
            return help_text

    parser = CustomArgumentParser(add_help=False)
    parser.add_argument('command', type=str, help="The command to execute (e.g., a .bat file)")
    parser.add_argument('-m', '--model', type=str, default=config.get('model', 'meta-llama'), help="Specify AI model to use")
    parser.add_argument('-t', '--temperature', type=float, default=config.get('temperature', 0.7), help="Set the temperature for AI generation")
    parser.add_argument('-l', '--log', type=str, help="Enable logging and specify the log file name")
    parser.add_argument('-u', '--user-message', type=str, help="Provide an additional user message for the AI analysis")
    parser.add_argument('-s', '--suppress-raw', action="store_true", help="Suppress raw output before AI analysis")
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Show this help message and exit')

    return parser.parse_args()

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

def get_ai(model, temperature, config):
    access_token   = config.get('hf_access_token')
    max_new_tokens = config.get('max_new_tokens', 1024)

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

    model_name = model_map.get(model.lower(), 'meta-llama/Meta-Llama-3-8B-Instruct')

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
        os.chdir(clarification_dir)



def main():
    config = load_config()
    
    args = parse_arguments(config)

    ai = get_ai(args.model, args.temperature, config)
    
    ai.add_to_prompt("You are an AI assistant tasked with clarifying command outputs. ")
    ai.add_to_prompt("Your goal is to interpret the command output and present it in a human-readable form. ")
    ai.add_to_prompt("If provided, also consider the contents of the input file and context files to provide more context in your analysis.")
    ai.add_to_prompt("If the command output seems to indicate an error, please clarify what the error is and suggest a solution to the problem.")
    ai.add_to_prompt("Please do not offer further assistance at the end of your response.\n\n")
    
    ai.add_to_prompt(f"Command:\n{args.command}\n\n")
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
    
    if args.user_message:
        ai.add_to_prompt(f"Additional user message: {args.user_message}\n\n")

    stdout, stderr = run_command(command=args.command, suppress_output=args.suppress_raw)

    if stdout:
        ai.add_to_prompt(f"Command output:\n{stdout}\n\n")
    if stderr:
        ai.add_to_prompt(f"Error output:\n{stderr}\n\n")
    
    ai.add_to_prompt("Please provide a clear, concise interpretation of this output in human-readable form.")

    print_special("AI Analysis:")
    response = ai.print_response()
    print()
    print_special("End of AI Analysis")

    if args.log:
        log_file_path = os.path.join(user_dir, args.log)
        with open(log_file_path, 'w', encoding='utf-8') as log_file:
            log_file.write("*" * 50 + "\n")
            log_file.write("*" * 19 + " AI Prompt " + "*" * 20 + "\n")
            log_file.write("*" * 50 + "\n\n")
            log_file.write(ai.get_prompt())
            log_file.write("\n\n" + "*" * 50 + "\n")
            log_file.write("*" * 18 + " AI Response " + "*" * 19 + "\n")
            log_file.write("*" * 50 + "\n\n")
            log_file.write(response)
        print_info(f"Log written to: {log_file_path}")

    ai.clear_prompt()

if __name__ == "__main__":
    main()
