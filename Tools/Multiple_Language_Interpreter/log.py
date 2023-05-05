import logging
from logging.handlers import RotatingFileHandler
import colorlog
import time
import os

cur_path = os.path.dirname(os.path.realpath(__file__))
log_path = os.path.join(cur_path, 'logs')
log_name = os.path.join(log_path, '%s.log' % time.strftime('%Y-%m-%d'))

log_colors_config = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red',
}

class Log:
    def __init__(self, log_name=log_name):
        self.log_name = log_name
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.colorful_formatter = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] [%(levelname)s] - %(message)s',
            log_colors=log_colors_config, datefmt='%Y-%m-%d %H:%M:%S')
        self.default_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
        self.__init_log()

    def __init_log(self):
        log_path = os.path.dirname(os.path.realpath(self.log_name))
        if not os.path.exists(log_path): os.mkdir(log_path)

    def __file_handler(self):
        # FileHandler => local
        # RotatingFileHandler backup
        fh = RotatingFileHandler(filename=self.log_name, mode='a', maxBytes=1024 * 1024 * 5, backupCount=5,
                                 encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(self.default_formatter)
        return fh

    def __console_handler(self):
        # StreamHandler => console
        ch = colorlog.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(self.colorful_formatter)
        return ch

    def __file(self, level, message):
        fh = self.__file_handler()
        self.logger.addHandler(fh)
        self.__log(level, message)
        self.logger.removeHandler(fh)
        fh.close()

    def __console(self, level, message):
        ch = self.__console_handler()
        self.logger.addHandler(ch)
        self.__log(level, message)
        self.logger.removeHandler(ch)

    def __all(self, level, message):
        fh = self.__file_handler()
        ch = self.__console_handler()
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
 
        self.__log(level, message)
       
        # prevent duplicate log
        self.logger.removeHandler(ch)
        self.logger.removeHandler(fh)

        fh.close()
    
    def __log(self, level, message):
        if level == 'info':
            self.logger.info(message)
        elif level == 'debug':
            self.logger.debug(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)

    def debug(self, message):
        self.__all('debug', message)

    def info(self, message):
        self.__all('info', message)

    def warning(self, message):
        self.__all('warning', message)

    def error(self, message):
        self.__all('error', message)

    def file_debug(self, message):
        self.__file('debug', message)

    def file_info(self, message):
        self.__file('info', message)

    def file_warning(self, message):
        self.__file('warning', message)

    def file_error(self, message):
        self.__file('error', message)

    def console_debug(self, message):
        self.__console('debug', message)

    def console_info(self, message):
        self.__console('info', message)

    def console_warning(self, message):
        self.__console('warning', message)

    def console_error(self, message):
        self.__console('error', message)

if __name__ == "__main__":
    log = Log()
    log.debug("---begin----")
    log.info("info message")
    log.warning("----done----")
    log.error("----ERROR----")