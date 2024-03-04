import subprocess
import paramiko
import inspect
import sys
import ast

class RemoteExecutor(object):
    def __init__(self, remote_host, remote_user, remote_password):
        self.remote_host = remote_host
        self.remote_user = remote_user
        self.remote_password = remote_password

    def __get_function_info(self, function_str):
        lines = function_str.split('\n')
        min_indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
        function_str_fixed = '\n'.join(line[min_indent:] for line in lines)

        tree = ast.parse(function_str_fixed)

        function_node = tree.body[0]

        if isinstance(function_node, ast.FunctionDef):
            function_name = function_node.name
            parameters = [param.arg for param in function_node.args.args]

            return function_name, parameters

        return None, None
    
    def __remove_from_tuple(self, tpl, entry):
        lst = list(tpl)
        if entry in lst:
            lst.remove(entry)
        return tuple(lst)

    def run_remote_command(self, function_str, *args, **kwargs):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        function_name, parameters = self.__get_function_info(function_str)

        if "python_version" in kwargs.keys():
            python_version = kwargs["python_version"]
            kwargs.pop("python_version")
        else:
            python_version = "python3"

        if "sudo" in kwargs.keys():
            sudo = kwargs["sudo"]
            kwargs.pop("sudo")
        else:
            sudo = False
        
        if "shell_check" in kwargs.keys():
            shell_check = kwargs["shell_check"]
        else:
            shell_check = True

        parameters_string = ""
        for key, value in kwargs.items():
            if key in parameters:
                if key != "shell_check":
                    parameters_string += ", {}={}".format(key, '"{}"'.format(value) if isinstance(value, str) else value)
                else:
                    parameters_string += ", {}={}".format(key, True)
            else:
                kwargs.pop(key)

        if parameters_string != "":
            parameters_string = parameters_string[2:]
        
        ssh.connect(self.remote_host, username=self.remote_user, password=self.remote_password)

        # Lade die Funktionen auf dem entfernten Rechner.
        with ssh.open_sftp().file("remote_execution.py", "w") as f:
            f.write("""{}
import subprocess
import sys

class Local(object):
                 
{}

# Führe die Funktion auf dem entfernten Rechner aus.
result = Local.{}({})
                    
if result:
    print(result)
""".format("# -*- coding: utf-8 -*-\n" if python_version != "python3" else "", function_str, function_name, parameters_string))
            
        if sudo:
            ssh.exec_command('echo "{}" | sudo chown {}:{} remote_execution.py'.format(self.remote_password, self.remote_user, self.remote_user))

        # Führe die Funktionen auf dem entfernten Rechner aus.
        full_command = "{} remote_execution.py".format('echo "{}" | sudo {}'.format(self.remote_password, python_version) if sudo else python_version)
        stdin, stdout, stderr = ssh.exec_command(full_command)
        stdin.flush()

        result_stdout = stdout.read().decode('utf-8')
        
        if shell_check:
            print(result_stdout)
            return_value = None
        else:
            return_value = str(result_stdout)
        
        #ssh.exec_command("echo {} | rm remote_execution.py".format(self.remote_password) if sudo else "rm remote_execution.py")
        ssh.close()
        return str(return_value)

    def ls(self, path=None, shell_check=True, *args, **kwargs):
        if "python_version" not in kwargs.keys():
            kwargs["python_version"] = "python3"
        else:
            if "python" in args and not "python3" in args:
                kwargs["python_version"] = "python"
                args = self.__remove_from_tuple(args, "python")
            else:
                kwargs["python_version"] = "python3"
                args = self.__remove_from_tuple(args, "python3")

        if "sudo" not in kwargs.keys():
            kwargs["sudo"] = False
        else:
            for arg in args:
                if isinstance(arg, bool):
                    kwargs["sudo"] = arg
                    args = self.__remove_from_tuple(args, arg)

        ls_function_str = inspect.getsource(Local.ls)
        return self.run_remote_command(ls_function_str, path=path, shell_check=shell_check, *args, **kwargs)

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
