import argparse
import json
import os
import shutil
import subprocess
import sys

# TODO: Make this more configurable.
#       Maybe check if the libs exist elsewhere in the os.
files_to_remove = [
    "aws_completer",
    "awscli/data/ac.index",
]

# TODO: CLI doesn't start when these services are removed.
#       Possibly related to customizations/aliases
required_services = [
    'codedeploy',
    'opsworkscm',
    'config'
]


def check_base_dir_is_ok(base_dir):
    base_dir_exists = os.path.isdir(base_dir)
    aws_cli_exists = os.path.isfile(os.path.join(base_dir, 'aws'))
    return base_dir_exists and aws_cli_exists

def can_strip_files():
    try:
        subprocess.run(['strip', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def _strip_files_in_directory(directory):
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            print(f"stripping {filepath}")
            subprocess.run(['strip', '-s', filepath])

def strip_files(base_dir):
    _strip_files_in_directory(base_dir)

    lib_dynload_path = os.path.join(base_dir, "lib-dynload")
    if os.path.exists(lib_dynload_path):
        _strip_files_in_directory(lib_dynload_path)

    # Try both the old and new path patterns
    crypto_paths = [
        os.path.join(base_dir, "cryptography/hazmat/bindings"),  # Old path
        os.path.join(os.path.dirname(base_dir), "cryptography/hazmat/bindings")  # New path (outside dist)
    ]

    for crypto_path in crypto_paths:
        if os.path.exists(crypto_path):
            _strip_files_in_directory(crypto_path)
            break

def remove_examples(base_dir, services_to_keep):
    directory = os.path.join(base_dir, "awscli/examples")
    examples_removed=0
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path) and os.path.basename(item) not in services_to_keep:
            shutil.rmtree(item_path)
            examples_removed+=1
    print(f"removed {examples_removed} examples")

def remove_services(base_dir, services_to_keep):
    for s in services_to_keep:
        print(f"keeping {s}")

    directory = os.path.join(base_dir, "awscli/botocore/data")
    services_removed=0
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path) and os.path.basename(item) not in services_to_keep:
            shutil.rmtree(item_path)
            services_removed+=1
    print(f"removed {services_removed} services")

def clean_endpoints(base_dir, services_to_keep):
    path_to_endpoints = os.path.join(base_dir, "awscli/botocore/data/endpoints.json")
    endpoints = {}
    endpoints_cleaned=0
    with open(path_to_endpoints, 'r') as file:
        endpoints = json.load(file)
        for partition in endpoints['partitions']:
            for service in list(partition['services'].keys()):
                if service not in services_to_keep:
                    del partition['services'][service]

    with open(path_to_endpoints, 'w') as file:
        print(json.dump(endpoints, file, separators=(',', ':')))
        endpoints_cleaned+=1
    print(f"removed {endpoints_cleaned} endpoints")

def delete_files(base_dir, file_to_remove):
    files_removed=0
    for file_path in file_to_remove:
        full_path = os.path.join(base_dir, file_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
            files_removed+=1
    print(f"removed {files_removed} files")

def minify_json(base_dir):
    files_minified=0
    for dirpath, _, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.endswith('.json'):
                file_path = os.path.join(dirpath, filename)
                with open(file_path, 'r') as file:
                    content = json.load(file)

                with open(file_path, 'w') as file:
                    json.dump(content, file, separators=(',', ':'))
                    files_minified+=1
    print(f"minified {files_minified} json files")

# A list of service names (as they appear in awscli/boto3/data)
# separated by newlines.
def load_services_to_keep(file_path):
    with open(file_path, 'r') as file:
        return [line.rstrip('\n') for line in file.readlines()]

def minify(base_dir, to_keep):
    remove_examples(base_dir, to_keep)
    remove_services(base_dir, to_keep)
    clean_endpoints(base_dir, to_keep)
    minify_json(base_dir)
    delete_files(base_dir, files_to_remove)
    if can_strip_files():
        strip_files(base_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Minify the aws cli.')
    parser.add_argument('base_dir', type=str, help='Where the aws-cli has been unziped to.')
    parser.add_argument('--services_to_keep', type=str, default=None, help='Comma-separated list of services to keep (optional).')
    parser.add_argument('--filename', type=str, default=None, help='The filename to process (optional).')

    args = parser.parse_args()

    to_keep = []
    if args.services_to_keep:
        to_keep = args.services_to_keep.split(',')
    else:
        print("loading services to keep from minify.keep")
        to_keep = load_services_to_keep("minify.keep")

    if len(to_keep) == 0:
        print("provide a minify.keep file or --services_to_keep param")
        print("otherwise the cli will have no commands")
        sys.exit(1)
    to_keep = to_keep + required_services

    base_dir = os.path.join(args.base_dir, 'dist')

    if not check_base_dir_is_ok(base_dir):
        print(f"invalid base directory: {base_dir}, expected dist/aws to exist")
        sys.exit(1)

    minify(base_dir, to_keep)
