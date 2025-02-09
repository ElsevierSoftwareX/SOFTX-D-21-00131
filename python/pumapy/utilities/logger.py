import datetime
import os


def print_warning(warning_text):
    print(Colors.WARNING + warning_text + Colors.ENDC)


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Logger:

    def __init__(self):

        self.log = ""
        self.location = ""

        if not os.path.exists('logs'):
            os.mkdir('logs')

        now = datetime.datetime.now()
        self.location = "logs/pumapy_log_" + str(now.year) + "_" + str(now.month) + "_" + str(now.day) + "_" + \
            str(now.hour) + "_" + str(now.minute) + "_" + str(now.second) + ".txt"

    def set_location(self, location):
        self.location = location

    def log_section(self, name):
        self.log += "\n---------------------------- \n " + str(name) + "\n---------------------------- \n"

    def log_line(self, val):
        self.log += str(val) + "\n"

    def log_item(self, val):
        self.log += str(val) + " "

    def new_line(self):
        self.log += "\n"

    def log_bool(self, var_name, val):
        if val:
            self.log_line(str(var_name) + ": True")
        else:
            self.log_line(str(var_name) + ": False")

    def log_value(self, var_name, val):
        self.log_line(str(var_name) + ": " + str(val))

    def write_log(self):
        if self.location == "":
            return
        txt_file = open(self.location, "w")
        txt_file.write(self.log)
        txt_file.close()
