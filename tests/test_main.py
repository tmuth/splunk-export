
import sys,os


parent = os.path.abspath('..')
#print(parent)
sys.path.insert(1, parent)
#print(sys.path)
import splunk_export_parallel
#print(splunk_export_parallel.checksum_var('foo'))

def test_checksum():
    checksumOutput=splunk_export_parallel.checksum_var('foo')
    assert checksumOutput == 'acbd18db4cc2f85cedef654fccc4a4d8'

# def test_globals():
#     global global_vars
#     splunk_export_parallel.get_globals()
#     print(global_vars["job_id]"])

def test_create_file(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    print(tmp_path)
    assert 1