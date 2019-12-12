import obspython as obs
from pathlib import Path

verbose = False
config_path = ""
config_valid = False
signal_handler = None


def script_description():
    return "Sends OSC messages and/or bundles when specific sources are activated.\n\ngithub.com/ansse/OBS-OSC-Sender"


def load_config():
    global config_path
    global config_valid

    config_valid = False

    path = Path(config_path)
    try:
        path = path.resolve()
        print("Loading config file \"" + str(path) + "\"")
        if path.is_file():
            config_valid = True
    except Exception as e:
        print("ERROR: \"" + config_path + "\" is not a valid path.")
        print("Failed with exception", e)

    if config_valid:
        print("Config file loaded successfully.")
    else:
        print("Loading config failed.")


def reload_pressed(props, prop):
    load_config()


def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_text(props, "config_path", "Path to config file", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_bool(props, "verbose", "Verbose logging")
    obs.obs_properties_add_button(props, "reload", "Reload config", reload_pressed)

    return props


def script_defaults(settings):
    obs.obs_data_set_default_bool(settings, "verbose", False)


def script_update(settings):
    global verbose
    global config_path
    global config_valid

    if verbose:
        print("Script updating.")

    verbose = obs.obs_data_get_bool(settings, "verbose")
    config_path = obs.obs_data_get_string(settings, "config_path")

    if config_valid:
        if verbose:
            print("Current config valid. No need to reload")
    else:
        if verbose:
            print("Current config not valid.")
        load_config()




def source_activated(calldata):
    global verbose

    if config_valid:
        source = obs.calldata_source(calldata, "source")
        if source is not None:
            source_name =  obs.obs_source_get_name(source)
            if verbose:
                print("Source \"" + source_name + "\" activated.")


def disconnect_handler():
    global signal_handler

    if signal_handler is not None:
        obs.signal_handler_disconnect(signal_handler, "source_activate", source_activated)
    signal_handler = None


def connect_handler():
    global signal_handler

    disconnect_handler()

    signal_handler = obs.obs_get_signal_handler()
    obs.signal_handler_connect(signal_handler, "source_activate", source_activated)


def script_load(settings):
    global config_valid
    config_valid = False
    print("Script loading.")
    connect_handler()


def script_unload():
    global config_valid
    config_valid = False
    print("Script unloading.")
    disconnect_handler()
