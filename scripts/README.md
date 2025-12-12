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
- 📄 `airgapper.env` file in the project root (see `sample.env` for the list of environment variables)
- Offline environment has Nexus repository to host the Docker images


## 🔧 Set Up
### 🌐 Set Up Internet Machine
📜 Download the setup script and run it. It is an interactive script that helps you:
- set up airgapper on your internet machine
- prepare the resources to transfer to offline machine to set up airgapper

``` sh
curl -L https://raw.githubusercontent.com/puggrammer/airgapper/master/scripts/setup.sh -o setup.sh | bash
```


### 📰 Set Up Offline Machine
After running `setup.sh` on the internet machine, you should have `airgapper.sh`, `sample.env` and optionally, the tar file for airgapper docker image. Transfer these files to the offline machine.

If the airgapper docker image is hosted on your nexus/harbor, pull the image from the repo. Else, load the image from the tar file.

Your have now completed setting up your offline machine.


## 🚀 Usage
1. Configure the settings in `airgapper.env` file. Copy the `sample.env` and edit it accordingly.
    ``` sh
    cp sample.env airgapper.env
    ```

2. Run `airgapper.sh` in the project directory like how you were using airgapper!  
You may provide/overwrite the image name using `-i` or `--image` flag but `airgapper.env` must still be present in the project directory.


Examples:
```bash
./airgapper.sh maven download pom.xml -o ./output

./airgapper.sh -i airgapper:latest pypi download requests -o output

./airgapper.sh --image airgapper:latest docker download input/dl_docker.txt -o output

./airgapper.sh pypi upload output/requests-2.32.5-py3-none-any.whl -a nexus --repo pypi-hosted
```

> [!NOTE]
>
> Only the parent folder of the `airgapper.sh` script is mounted to the docker container. Ensure that the directories and files for airgapper to use are within this folder.
>
>    Example folder structure:
>   ```text
>   airgapper
>   └── scripts
>       ├── airgapper.sh
>       ├── airgapper.env
>       └── input
>       │   └── requirements.txt
>       └── output
>           └── requests-2.32.5-py3-none-any.whl 
>   ```
> 


## 🔒 Security Notes
- The wrapper script uses docker-in-docker to expose the Docker installed on host for docker commands.
- Docker container is using root user to get the folder permissions right.
