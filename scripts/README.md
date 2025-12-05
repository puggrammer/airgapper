# Tools

-----

## 🖥️ Overview
This folder contains helper tools to run airgapper in both online and offline environments without downloading each dependency:
- `Dockerfile`: builds image with all dependencies required 
- `airgapper.sh`: wrapper script for running airgapper commands
- `.sample.env`: sample configuration file for credentials and registry URLs


## ⚙️️ Prerequisites
- 🐳 Docker engine on both internet and offline machine
- 💻 Git Bash on both internet and offline machine
- 📄 `.env` file in the project root (see `.sample.env` for the list of environment variables)
- Offline environment has Nexus repository to host the Docker images


## 🔧 Set Up
### 🌐 Set Up Internet Machine
📜 Download the setup script and run it. It is an interactive script that helps you:
- set up airgapper on your internet machine
- prepare the resources to transfer to offline machine to set up airgapper

``` sh
curl -L https://raw.githubusercontent.com/puggrammer/airgapper/master/scripts/setup.sh -o setup.sh | bash
```


Alternatively, you can download the contents of this folder and build the Docker image yourself.
``` sh
# Download Dockerfile
curl -L https://raw.githubusercontent.com/puggrammer/airgapper/master/scripts/Dockerfile -o Dockerfile

# Build image
docker build -t airgapper .
```
The Dockerfile uses the latest release of airgapper on pypi.

### 📰 Set Up Offline Machine
For developers:
transfer the scripts folder to the offline machine. 

For developers, run `setup-offline.sh`. This assumes that your offline development environment has a Nexus repository

For system administrator, After setting up the internet machine to download the scripts and build the docker image, t

- Download the files in this folder OR
- Pull docker image from self-hosted harbour registry




## 🚀 Usage
1. Configure the settings in `.env` file. Copy the `.sample.env` and edit it accordingly.
    ``` sh
    cp .sample.env .env
    ```

2. Run `airgapper.sh` in the project directory like how you were using airgapper! <br>
You may provide/overwrite the image name using `-i` or `--image` flag but `.env` must still be present in the project directory.

Examples:
```bash
./airgapper.sh maven download pom.xml -o ./output

./airgapper.sh -i airgapper:latest pypi download requests -o output

./airgapper.sh --image airgapper:latest docker download input/dl_docker.txt -o output
```




## 🔒 Security Notes
- The wrapper script uses docker-in-docker to expose the Docker installed on host for docker commands.
- Docker container is using root user to get the folder permissions right.
- Do not commit .env — it contains usernames and passwords. Add it to .gitignore.

Secrets are injected into containers via --env-file .env, not hardcoded in scripts.

## 📦 Getting Started