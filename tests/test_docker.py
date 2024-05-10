import subprocess
from pathlib import Path

from airgapper.modules.docker import _get_sanitized_tar_filename

# def test_dl_image_pass_single_file():
#     input = DownloadArgs(
#         module=Module.DOCKER,
#         input="alpine:latest",
#         output_directory="./test-outputs/docker"
#     )
#     download_docker_images(input)
    
#     assert Path(f"{input.output_directory}/))


# def test_docker_dl_package_pass():
#     output_dir = "./output"
#     image_name = "alpinelinux/gitlab-runner-helper:v0.0.1-x86_64"
#     output_tar = Path(f"output/{_get_sanitized_tar_filename(image_name)}")
#     try:
#         proc = subprocess.run(
#             ["python", "-m", "airgapper","docker","download",image_name,"-o", output_dir],
#             capture_output=True,
#             text=True
#         )
#         print(proc.stdout)
#         assert proc.returncode == 0

#         print(f"Checking if {output_tar} exists.")
#         assert output_tar.exists()
#     except Exception as ex:
#         print(proc.stderr)
#         raise ex
#     finally:
#         subprocess.run(["docker","rmi",image_name])
#         output_tar.unlink(missing_ok=True)


def test_docker_dl_directory_pass():
    output_dir = "./output"
    txt_file = "input/test/dl_docker.txt"

    with open(txt_file, 'r') as f:
        images = f.readlines()
        images_count = len(images)
    try:
        proc = subprocess.run(
            ["python", "-m", "airgapper","docker","download",txt_file,"-o",output_dir],
            capture_output=True,
            text=True
        )
        print(proc.stdout)
        assert proc.returncode == 0

        sanitized_tar_filenames = set([Path(f"{output_dir}/{_get_sanitized_tar_filename(image)}") for image in images])

        output_tars = list(Path(output_dir).iterdir())
        print(f"{output_tars=}")
        assert len(output_tars) == images_count
        assert sanitized_tar_filenames == set(output_tars)

    finally:
        for image in images:
            subprocess.run(["docker","rmi",image])
        for tar in output_tars:
            tar.unlink(missing_ok=True)


def test_docker_ul_package_pass():
    pass

def test_docker_ul_directory_pass():
    pass