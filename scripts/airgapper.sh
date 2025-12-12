#!/bin/bash

# Note: Tested this on Git Bash,
# Does not work in windows wsl2. It keeps complaining that it cannot find the .env file.

# -------------------------------------------------------------------------------------------------------
# This is a wrapper script that runs airgapper command in a docker container, see help msg for more info.
# -------------------------------------------------------------------------------------------------------

# Exit immediately if a command exits with a non-zero status or an unbound variable is used
set -euo pipefail

# -------------------------------
# Configuration & Path Logic
# -------------------------------

# Get the absolute path of the directory where the script is located,
# regardless of where it is called from or if it is symlinked.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
readonly ENV_FILE="${SCRIPT_DIR}/airgapper.env"

# Initialise variable
IMAGE_NAME=""


# -------------------------------
# Functions
# -------------------------------

# IMAGE="airgapper:latest"

# Display help information
show_help() {
  local exit_code="${1:-0}"
  cat <<EOF

Usage: $(basename "$0") [-i|--image <image_name>] [AIRGAPPER_ARGS...]

Run the airgapper Docker container with bind mounts and environment variables.

Options:
  -i, --image <image_name>  Override the Docker image name (default: from airgapper.env)
  -h, --help                Show this help message and exit

Arguments passed after the options are forwarded to the 'airgapper' command inside the container.

Examples:
  ./$(basename "$0") maven download pom.xml -o ./output-directory
  ./$(basename "$0") --image custom/airgapper:0.1.0 maven download pom.xml -o ./output-directory
EOF
  exit "$exit_code"
}


# Extract IMAGE_NAME name from airgapper.env file
get_image_name_from_env_file() {
  echo -e "\n➤  Extracting image name..."
  # Use awk to reliably extract the value, which won't fail if the line isn't found
  local value

  # Awk returns an empty string if nothing is found, which is safe with set -e
  value=$(awk -F'=' '/^IMAGE_NAME/{print $2}' "$ENV_FILE" | tr -d '"' | tr -d "'")

  if [[ -n "$value" ]]; then
    echo "✔  Extracted image name '$value' from $ENV_FILE"
    IMAGE_NAME="$value"
  fi
}


# Check for required dependencies like whether docker is installed
check_dependencies() {
  echo -e "\n➤  Checking dependencies..."

  if ! command -v docker &> /dev/null; then
    echo "✖ Error: docker is not installed or not in PATH. Please install docker and try again." >&2
    exit 1
  fi

  # Ensure airgapper.env exists
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "✖ Error: airgapper.env file not found in $SCRIPT_DIR" >&2
    exit 1
  fi

  echo -e "✔  All dependencies met!"
}


verify_image_name_exist() {
  if [[ -z "$IMAGE_NAME" ]]; then
    echo -e "\n✖ ERROR: Docker image name not found in airgapper.env file and arguments" >&2
    echo "> Set docker image name in airgapper.env file or in argument -i"
    print_separator "=" 100
    show_help 1
  fi
}

is_wsl() {
  if [[ -f /proc/sys/fs/binfmt_misc/WSLInterop ]]; then
    return 0 # True, it is WSL
  else
    return 1 # False, it is not WSL
  fi
}

# Run docker container
run_container() {
  echo -e "\n➤  Running airgapper container using image: $IMAGE_NAME"

  # Instantiate variables for linux environment first
  local execution_prefix=""
  local script_dir=$SCRIPT_DIR
  local env_file_path=$ENV_FILE

  # Environment Detection and Path Handling
  if [[ "$(uname -s)" =~ MINGW64.* ]]; then
    # in Git Bash (Windows)
    echo -e "  ℹ️  Running in Git Bash (Windows). Applying path fixes for Git Bash\n"

    # Convert paths to Windows format
    script_dir=$(cygpath -w "$SCRIPT_DIR")
    env_file_path=$(cygpath -w "$ENV_FILE")

    # use double slash // to handle how Git Bash translates paths on Windows,
    # preventing permission errors by pointing directly to the Docker Desktop socket path
    # rather than a relative path inside the C:\Program Files\Git\ directory
    readonly DOCKER_SOCKET_PATH="//var/run/docker.sock" # Windows/Git Bash compatible path

    # Use winpty bash -c for reliable execution of the Windows docker client
    execution_prefix="winpty bash -c"

  elif is_wsl; then
    # in wsl environment
    echo -e "  ℹ️  Detected WSL environment. Applying path fixes using wslpath\n"

    # convert paths using wslpath -w to translate Linux path (/mnt/d/...) to Windows format (D:\...)
    script_dir=$(wslpath -w "$SCRIPT_DIR")
    env_file_path=$(wslpath -w "$ENV_FILE")
    readonly DOCKER_SOCKET_PATH="//var/run/docker.sock"

  else
    # in Linux or macOS (POSIX environment)
    echo -e "  ℹ️  Running in a standard POSIX environment. No path fixes required\n"
    readonly DOCKER_SOCKET_PATH="/var/run/docker.sock"
  fi

  # Build the base docker run command as a Bash array
  local docker_cmd=(
    docker run --rm -it
    -v \"$DOCKER_SOCKET_PATH\":/var/run/docker.sock
    -v \"$script_dir\":/app
    --env-file \"$env_file_path\"
    "$IMAGE_NAME"
    airgapper
  )

  # Append the remaining command-line arguments ($@) to the array
  # This robustly adds each argument as a separate item in the array
  docker_cmd+=("$@")

  # Execute command
  if [[ -n "$execution_prefix" ]]; then
    # Windows/Git Bash: Convert array to a single robust command string for bash -c
    local full_command_string="${docker_cmd[*]}"
    echo -e "  ●  DEBUG: full_command_string = $full_command_string\n"
    $execution_prefix "$full_command_string"
  else
    # Linux/macOS: Execute the array directly
    "${docker_cmd[@]}"
  fi

}


# Handle -h or --help first, regardless of other options or dependencies
process_help_arg() {
  for arg in "$@"; do
    if [[ "$arg" == "-h" || "$arg" == "--help" ]]; then
      show_help
    fi
  done
}


print_separator() {
  local char="${1:-"-"}"   # use first argument, default to '-'
  printf "\n%${2:-80}s\n" "" | tr " " "$char"
}

# -------------------------------
# Main
# -------------------------------

main() {
  # 1. PROCESS HELP ARGUMENT FIRST AND EXIT IMMEDIATELY
  process_help_arg "$@"

  # 2. RUN REQUIRED CHECKS AND EXTRACT CONFIGURATION
  # print_separator
  check_dependencies
  get_image_name_from_env_file

  # 3. PARSE REMAINING ARGUMENTS
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -i|--image)
        if [[ -n "$2" ]]; then
          echo "   Overriding image name with argument: $2"
          IMAGE_NAME="$2"
          shift 2 # Consume the flag (-i) and the value (image name)
        else
          echo "✖ Error: missing value for $1 " >&2
          print_separator "=" 100
          show_help 1
        fi
        ;;
      *)
        # Stop processing options and leave the rest of the arguments ($@) for the container command
        # NOTE: The remaining arguments are still in the positional parameters ($@)
        break
        ;;
    esac
  done

  # Shift positional parameters so that $@ only contains arguments meant for the 'airgapper' command inside the container.
  shift "$((OPTIND - 1))" || true

  # 4. VERIFY CRITICAL INFO EXIST
  verify_image_name_exist  # add a default value for image name?

  # 5. EXECUTE with the arguments ($@) to be passed to 'airgapper'
#  chmod o+w "$SCRIPT_DIR"
  run_container "$@"
 # chmod o-w "$SCRIPT_DIR"
}

# Call the main function with all command-line arguments passed to the script
main "$@"