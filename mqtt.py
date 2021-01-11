import paho.mqtt.client as mqtt
from config import get_settings, get_topic
from influx import write_influx
from log import save_event

selected_topics = []


def subscribe(_selected_topics):
    """if _selected_topics is empty means subscribe to all topic"""
    global selected_topics
    selected_topics = _selected_topics


def connection_to_broker():
    # Settings
    mqtt_settings = get_settings("mqtt_settings")
    broker_url = mqtt_settings.broker_url
    broker_port = mqtt_settings.broker_port
    mqtt_login = mqtt_settings.mqtt_login
    mqtt_pass = mqtt_settings.mqtt_pass

    # Connection
    _client = mqtt.Client()
    _client.on_connect = on_connect
    _client.on_disconnect = on_disconnect
    _client.on_message = on_message
    _client.username_pw_set(username=mqtt_login, password=mqtt_pass)

    try:
        _client.connect(broker_url, broker_port, keepalive=10)
        print("Connection to mqtt: Successful")
    except Exception as err:
        _client = None
        error_message = f"Connection to mqtt: Fail; Reason: {str(err)}"
        print(error_message)
        save_event(error_message)

    return _client


def subscribe_to_topic(_client, topic, qos=1):  # qos = 1 - At Least Once
    _client.subscribe(topic, qos=qos)


def subscribe_to_all(_client, qos=1):
    for value in get_settings("topics"):
        subscribe_to_topic(_client, value, qos)


def on_connect(_client, userdata, flags, rc):
    """Connect and subscribe. Debug mode - only selected topics"""
    label = get_settings("mqtt_connection_status")[rc] if rc in range(0, 6) else "Currently unused"
    print(f"Connection to broker: {label}")

    if selected_topics:  # Debug mode
        for topic in selected_topics:
            subscribe_to_topic(_client, get_topic(topic))
    else:
        subscribe_to_all(_client)


def on_disconnect(_client, userdata, rc):
    print("Client Got Disconnected")


def on_message(_client, userdata, message):
    try:
        value = message.payload.decode()
    except UnicodeDecodeError:
        return

    if message.retain == 1:
        save_event(message.topic, "retain message", value)
        return

    if selected_topics:  # Debug mode
        print(f"Message received. Topic: {message.topic}, value: {value}")

    write_influx(message.topic, value)


def start_mqtt(client):
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Client Got Disconnected")
