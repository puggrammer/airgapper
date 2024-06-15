import subprocess
import glob
from pathlib import Path

def test_pypi_dl_missing_file_and_package():
    proc = subprocess.run(
        ["./airgapper.sh","pypi","download"],
        capture_output=True,
        text=True
    )
    assert proc.returncode == 1
    assert "E: [DOWNLOAD] Either package or text file is required" in proc.stderr

def test_pypi_dl_missing_output_directory():
    proc = subprocess.run(
        ["./airgapper.sh","pypi","download","iniconfig==2.0.0"],
        capture_output=True,
        text=True
    )
    assert proc.returncode == 1
    assert "E: [DOWNLOAD] Output directory destination is required" in proc.stderr

def test_pypi_dl_package_pass():
    output_filepath = Path(f"output/iniconfig-2.0.0-py3-none-any.whl")
    try:
        proc = subprocess.run(
            ["./airgapper.sh","pypi","download","iniconfig==2.0.0","-o","./output"],
            capture_output=True,
            text=True
        )
        print(proc.stdout)
        assert proc.returncode == 0
        assert output_filepath.exists()
    finally:
        output_filepath.unlink(missing_ok=True)