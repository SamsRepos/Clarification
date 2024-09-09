import colorama

colorama.init()

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
