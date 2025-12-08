#!/bin/bash

# -----------------------------------------------------------------------------------------
# This setup script downloads the helper scripts from Github and builds the docker image.
# -----------------------------------------------------------------------------------------

# "strict" mode - exit immediately on any error, catch unset variables and catch any error in pipeline
set -euo pipefail

GITHUB_API_URL="https://api.github.com/repos/puggrammer/airgapper/contents/scripts"
NUM_STEPS="3"

OVERALL_SUCCESS=true   # Track overall status

# Initialise variables, to be set later from user input
PROJECT_DIR=""
VERSION=""
FULL_IMAGE_NAME=""
SAVE_TAR=""

IMAGE_NAME="airgapper"
TAG_NAME=""


# -------------------------------
# Functions
# -------------------------------

# Verify docker is installed
verify_docker_installed() {
  type "docker" &> /dev/null || \
  { echo "✖ Error: docker is not installed or not in PATH. Please install docker and try again.";
  exit 1; }
}


create_project_dir() {
  # Ask user for project directory name, with default
  read -r -p "➤ Enter project directory name (default: airgapper): " PROJECT_DIR
  PROJECT_DIR=${PROJECT_DIR:-airgapper}

  # Create project directory if it does not exist
  mkdir -p "$PROJECT_DIR"
}


# Get content from URL
fetch_url() {
  curl -s -H "Accept: application/vnd.github.v3+json" "$GITHUB_API_URL" \
  | grep '"download_url"' \
  | sed -E 's/.*"download_url": "(.*)",/\1/'
}


# Extract download URLs and download all files in scripts folder
download_files() {
  local dir=$1
  local success=true

  echo -e "\n[1/$NUM_STEPS] Downloading helper scripts to folder: $dir"
  fetch_url | while read -r url; do
    # Skip if URL is null or empty
    if [ -n "$url" ] && [ "$url" != "null" ]; then
      echo "        Downloading $url "
      if ! curl -s -L "$url" -o "$dir/$(basename "$url")"; then
        echo "        ✖ Error: Failed to download $url"
        success=false
        OVERALL_SUCCESS=false
      fi
    fi
  done

  if [ "$success" = true ]; then
    echo "   ✔  All files downloaded to folder: $dir"
  else
    echo "  ⚠️  Failed to download some files. Re-run this script to re-download all files."
  fi
}


# Build docker image
build_docker_image() {
  local dir=$1

  echo -e "\n[2/$NUM_STEPS] Building Docker image..."
  if [ -f "$dir/Dockerfile" ]; then
    read -r -p "        Enter image name for the Docker image (default: airgapper): " IMAGE_NAME
    IMAGE_NAME=${IMAGE_NAME:-airgapper}
    read -r -p "        Enter version tag for the Docker image (default: latest): " VERSION
    VERSION=${VERSION:-latest}
    FULL_IMAGE_NAME="$IMAGE_NAME:$VERSION"

    docker build -t "$FULL_IMAGE_NAME" "$PROJECT_DIR"
    echo "   ✔  Docker image '$FULL_IMAGE_NAME' built successfully."
  else
    echo "   ✖  No Dockerfile found in $PROJECT_DIR. Re-run this script to download the Dockerfile."
    OVERALL_SUCCESS=false
    exit 1
  fi
}

get_latest_release_version() {
  echo "        Fetching latest release information..."

  # Fetch release info
  if ! release_resp=$(curl -sS -f "https://api.github.com/repos/puggrammer/airgapper/releases/latest"); then
    echo "   ✖  Error: Failed to fetch latest release info from GitHub. Check internet connection and retry again..." >&2
    OVERALL_SUCCESS=false
    exit 1
  fi

  # Extract tag name
  TAG_NAME=$(echo "$release_resp" | grep "tag_name" | sed 's/^ *//;s/,*$//' | cut -d: -f2 | sed 's/^ *//' | tr -d '\"' )

  if [[ -z "$TAG_NAME" ]]; then
    echo "   ✖  Error: Failed to extract latest release tag_name using grep/sed/cut" >&2
    echo "  Response was: $release_resp" >&2
    exit 1
  fi

  echo "        Latest tag name is: $TAG_NAME"
  FULL_IMAGE_NAME="$IMAGE_NAME:$TAG_NAME"
}


# Pull docker image
pull_docker_image() {
  echo -e "\n[2/$NUM_STEPS] Pulling Docker image..."
  get_latest_release_version

  local image_url="ghcr.io/puggrammer/airgapper:$TAG_NAME"
  echo "        Pulling image from $image_url"
  docker pull "$image_url"
  echo "   ✔  Docker image airgapper:$TAG_NAME pulled successfully."
}


# Save docker image to tar file
save_tar() {
  local image_name=$1
  local tar_file_name=$2
  local dir=$3

  echo -e "\n[3/$NUM_STEPS] Saving Docker image..."
  read -p "        Do you want to save the image to a tar file? (y/n) (default: y): " SAVE_TAR
  SAVE_TAR=${SAVE_TAR:-y}

  if [[ "$SAVE_TAR" =~ ^[Yy](es)?$ ]]; then
    TAR_FILE="${dir}/${tar_file_name}.tar"
    echo "        Saving image to $TAR_FILE ..."
    docker save -o "$TAR_FILE" "$image_name"
    echo "   ✔  Image saved to $TAR_FILE"
  else
    echo "      Skipping tar save"
  fi
}


print_separator() {
  local char="${1:-"-"}"   # use first argument, default to '-'
  printf "\n%${2:-80}s\n" "" | tr " " "$char"
}

init() {
  print_separator
  echo "➤ Setting up airgapper..."

  create_project_dir
}

print_summary() {
  local status=$?
  print_separator "="
  if [ $status -eq 0 ] && [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "\n✅ COMPLETED setting up airgapper! 🎉🎉🎉"
    echo -e "\n➤➤➤ NEXT STEP: configure .env file before running airgapper.sh"
  else
    echo -e "\n▲ ERROR encountered! Please check the logs above "
    exit 1
  fi
}

# -------------------------------
# Main
# -------------------------------

# print custom error message before exiting
trap print_summary EXIT

verify_docker_installed
init
download_files "$PROJECT_DIR"
pull_docker_image
#build_docker_image "$PROJECT_DIR"
save_tar "$FULL_IMAGE_NAME" "$IMAGE_NAME" "$PROJECT_DIR"
