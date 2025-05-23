try:
    import plexhints  # noqa: F401
except ImportError:
    pass
else:  # the code is running outside of Plex
    from plexhints.log_kit import Log  # log kit
    from plexhints.prefs_kit import Prefs  # prefs kit


class Logging(object):
    def debug(self, message, *args):
        # type: (str, *str) -> None
        """
            Prints passed message with DEBUG TYPE,
            when DEBUG pref enabled.
        """
        if Prefs['logging_level'] == "DEBUG":
            try:
                return Log.Debug(message, *args)
            except Exception:
                return self.warn('Cant log that message it seems not to be a string')

    # Prints any message you give
    def info(self, message, *args):
        # type: (str, *str) -> None
        """
            Prints passed message with INFO TYPE,
            when INFO or DEBUG pref enabled.
        """
        if Prefs['logging_level'] == "DEBUG" or (
            Prefs['logging_level'] == "INFO"
        ):
            try:
                return Log(message, *args)
            except Exception:
                return self.warn('Cant log that message it seems not to be a string')

    def warn(self, message, *args):
        # type: (str, *str) -> None
        """
            Prints passed message with INFO TYPE,
            when DEBUG, INFO or WARN pref enabled.
        """
        if Prefs['logging_level'] == "DEBUG" or (
            Prefs['logging_level'] == "INFO") or (
                Prefs['logging_level'] == "WARN"
        ):
            try:
                # No builtin warn, so use info level for it
                return Log(message, *args)
            except Exception:
                return self.warn('Cant log that message it seems not to be a string')

    def error(self, message, *args):
        # type: (str, *str) -> None
        """
            Prints passed message with ERROR TYPE,
            when DEBUG, INFO, WARN or ERROR pref enabled.
        """
        if Prefs['logging_level'] == "DEBUG" or (
            Prefs['logging_level'] == "INFO") or (
                Prefs['logging_level'] == "WARN") or (
                    Prefs['logging_level'] == "ERROR"
        ):
            try:
                return Log.Error(message, *args)
            except Exception:
                return self.warn('Cant log that message it seems not to be a string')

    def log_output(self, key, val, log_level):
        # type: (str, str, str) -> None
        """
            Logs key/value pair with passed log level.
        """
        output = "{key:<20}{val}".format(
            key=key,
            val=val
        )
        if log_level.lower() == "debug":
            self.debug(output)
        else:
            self.info(output)

    # For the below logging:
    # Default level is info
    # Set debug by calling (msg='sometext', log_level='debug')

    def separator(self, msg=None, log_level="info"):
        # type: (str, str) -> None
        """
            Prints a bunch of divider chars like ---,
            with optional message.
        """
        divider = "-" * 35
        output = divider + divider
        # Override output with message if passed
        if msg:
            output = divider + msg + divider

        if log_level.lower() == "debug":
            return self.debug(output)
        return self.info(output)

    def metadata(self, dict_arr, log_level="info"):
        # type: (list, str) -> None
        """
            Logs key/value pairs from array of dictionaries.
        """
        # Loop through dicts in array
        for log_type in dict_arr:
            # Loop through each key/value
            for key, val in log_type.items():
                if val:
                    self.log_output(key, val, log_level)

    def metadata_arrs(self, dict_arr, log_level="info"):
        # type: (list, str) -> None
        """
            Logs key/value pairs from array of dictionaries,
            where value is an array.
        """
        # Loop through dicts in array
        for log_type in dict_arr:
            # Loop through each key/value
            for key, val in log_type.items():
                if val:
                    # Loop through dict's array
                    for item in val:
                        self.log_output(item, key, log_level)
