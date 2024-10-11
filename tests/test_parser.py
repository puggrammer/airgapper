import subprocess


def test_parser_missing_module_fail():
    proc = _run_airgapper(['download','package','-o','./output',''])
    print(proc.stderr)
    assert proc.returncode


def test_parser_missing_action_fail():
    proc = _run_airgapper(['docker', 'package', '-o', './output'])
    print(proc.stderr)
    assert proc.returncode == 2


def test_parser_missing_input_arg_fail():
    proc = _run_airgapper(['docker', 'download', '-o', './output'])
    print(proc.stderr)
    assert proc.returncode == 2


def test_parser_dl_missing_output_folder_fail():
    proc = _run_airgapper(['docker', 'download', 'package'])
    print(proc.stderr)
    assert proc.returncode == 2


def test_parser_dl_missing_output_flag_fail():
    proc = _run_airgapper(['docker', 'download', 'package', './output'])
    print(proc.stderr)
    assert proc.returncode == 2


def test_parser_up_missing_registry_fail():
    proc = _run_airgapper(['docker', 'upload', 'package'])
    print(proc.stderr)
    assert proc.returncode == 2


# def test_parser_up_missing_helm_registry_fail():
#     proc = _run_airgapper(['helm','upload','package','-r','registry.com'])
#     print(proc.stderr)
#     assert proc.returncode == 2


def _run_airgapper(extra_args: list):
    args = ['python', '-m', 'airgapper']
    args.extend(extra_args)
    print(args)
    return subprocess.run(args, capture_output=True, text=True, check=False)
