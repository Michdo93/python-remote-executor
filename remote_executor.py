import subprocess
import paramiko
import inspect
import sys

class RemoteExecutor(object):
    def __init__(self, remote_host, remote_user, remote_password):
        self.remote_host = remote_host
        self.remote_user = remote_user
        self.remote_password = remote_password

    def run_remote_command(self, function_str, *args, python_version="python3", sudo=False):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(self.remote_host, username=self.remote_user, password=self.remote_password)

        """
        if python_version == "python":
            if "subprocess.run" in function_str:
                function_str = function_str.replace("subprocess.run", "subprocess.call").replace(", check=", ", shell=")
        elif python_version == "python3":
            if "subprocess.call" in function_str:
                function_str = function_str.replace("subprocess.call", "subprocess.run").replace(", shell=", ", check=")
        """

        # Lade die Funktionen auf dem entfernten Rechner.
        with ssh.open_sftp().file("remote_execution.py", "w") as f:
            f.write("""{}
import subprocess
import sys

class Local(object):
                 
{}

# Führe die Funktion auf dem entfernten Rechner aus.
result = Local.ls({})
                    
if result:
    print(result)
""".format("# -*- coding: utf-8 -*-\n" if python_version != "python3" else "", function_str, ", ".join(args)))
            
        if sudo:
            ssh.exec_command('echo "{}" | sudo chown {}:{} remote_execution.py'.format(self.remote_password, self.remote_user, self.remote_user))

        # Führe die Funktionen auf dem entfernten Rechner aus.
        full_command = "{} remote_execution.py".format('echo "{}" | sudo {}'.format(self.remote_password, python_version) if sudo else python_version)
        stdin, stdout, stderr = ssh.exec_command(full_command)
        stdin.flush()
        print(stdout.read().decode('utf-8'))
        ssh.exec_command("echo {} | rm remote_execution.py".format(self.remote_password) if sudo else "rm remote_execution.py")
        ssh.close()

    def ls(self, *args, **kwargs):
        ls_function_str = inspect.getsource(Local.ls)
        self.run_remote_command(ls_function_str, *args, **kwargs)

class Local(RemoteExecutor):
    @staticmethod
    def ls(path=None, shell_check=True):
        command = ['ls']
        if path:
            command.append(path)
        if sys.version_info.major == 3:
            result = subprocess.run(command, check=shell_check)
        elif sys.version_info.major == 2:
            result = subprocess.call(command, shell=shell_check)
        return result.stdout.decode('utf-8') if not shell_check else None

if __name__ == "__main__":
    Local.ls()

    # Konvertiere die ls-Funktion in einen String

    """
    ls_function_str = inspect.getsource(Local.ls)

    remote = RemoteExecutor(remote_host='192.168.128.128', remote_user='ubuntu', remote_password='linux')
    remote.run_remote_command(ls_function_str, sudo=True)
    """

    Remote = RemoteExecutor(remote_host='192.168.128.128', remote_user='ubuntu', remote_password='linux')
    Remote.ls(python_version="python")
