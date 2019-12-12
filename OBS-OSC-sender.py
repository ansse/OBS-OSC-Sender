import json
from pathlib import Path

import obspython as obs
from pythonosc import udp_client
from pythonosc import osc_message_builder
from pythonosc import osc_bundle_builder

verbose = False
config_path = ""
config_valid = False
config_dict = {}

signal_handler = None

osc_client = None
messages_and_bundles = {}
sources = {}

def script_description():
    return "Sends OSC messages and/or bundles when specific sources are activated.\n\ngithub.com/ansse/OBS-OSC-Sender"

def parse_bundle(bnd_id):
    success = True

    bnd_items = config_dict["BUNDLES"][bnd_id]
    if bnd_items is not None:
        if bnd_id in messages_and_bundles:
            print("ERROR: Bundle parsing failed. Name clashes with the message \"" + bnd_id + "\".")
            success = False
        else:
            osc_bnd = osc_bundle_builder.OscBundleBuilder(osc_bundle_builder.IMMEDIATELY)
            for item in bnd_items:
                if item in messages_and_bundles:
                    osc_bnd.add_content(messages_and_bundles[item])
                elif parse_bundle(item):
                    osc_bnd.add_content(messages_and_bundles[item])
                else:
                    print("ERROR: Bundle parsing failed. No message or bundle found with the name \"" + item + "\".")
                    success = False
                    break
            if success:
                messages_and_bundles[bnd_id] = osc_bnd.build()
                config_dict["BUNDLES"][bnd_id] = None

    return success

def parse_config():
    global config_dict
    global osc_client
    global messages_and_bundles
    global sources

    messages_and_bundles = {}

    success = True
    try:
        host = config_dict["HOST"]
        port = config_dict["PORT"]
        osc_client = udp_client.SimpleUDPClient(host, port)
    except Exception as e:
        print("ERROR: Invalid host/port config")
        print("Failed with exception", e)
        success = False

    if success:
        try:
            messages = config_dict["MESSAGES"]
            for msg_id in messages:
                msg = messages[msg_id]
                addr_id = msg["ADDRESS"]
                addr = config_dict["ADDRESSES"][addr_id]
                osc_msg = osc_message_builder.OscMessageBuilder(addr)
                for arg in msg["ARGUMENTS"]:
                    osc_msg.add_arg(arg)
                messages_and_bundles[msg_id] = osc_msg.build()

        except Exception as e:
            print("ERROR: Message parsing failed")
            print("Failed with exception", e)
            success = False

    if success:
        try:
            for bnd_id in config_dict["BUNDLES"]:
                success = parse_bundle(bnd_id)
                if not success:
                    break

        except Exception as e:
            print("ERROR: Bundle parsing failed")
            print("Failed with exception", e)
            success = False

    if success:
        for src_id in config_dict["SOURCES"]:
            msg_bnd_id = config_dict["SOURCES"][src_id]
            if msg_bnd_id in messages_and_bundles:
                sources[src_id] = msg_bnd_id
            else:
                print("ERROR: Source parsing failed. No message or bundle found with the name \"" + msg_bnd_id + "\".")
                success = False
                break

    return success


def load_config():
    global config_path
    global config_valid
    global config_dict

    config_dict = {}

    path = Path(config_path)
    try:
        path = path.resolve()
        print("Loading config file \"" + str(path) + "\"")
        if path.is_file():
            with open(path, "r") as file:
                config_dict = json.load(file)
                #print(config_dict)
                config_valid = parse_config()
    except Exception as e:
        print("ERROR: \"" + config_path + "\" is not a valid config file.")
        print("Failed with exception", e)
        config_valid = False

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
