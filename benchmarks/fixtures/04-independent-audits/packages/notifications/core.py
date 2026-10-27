"""Message templates and an in-memory outbox."""
import string


def _channel_ok(channel):
    return channel in ("email", "sms", "push")


def render_template(template, **values):
    """Fill $placeholders; a missing value raises KeyError."""
    return string.Template(template).substitute(**values)


def queue_message(outbox, channel, recipient, body):
    """Append a message to the outbox list and return it."""
    if not _channel_ok(channel):
        raise ValueError(f"unknown channel: {channel}")
    message = {"channel": channel, "to": recipient, "body": body, "sent": False}
    outbox.append(message)
    return message


def send_all(outbox, sender):
    """Call sender(message) for each unsent message; return how many were sent."""
    count = 0
    for message in outbox:
        if not message["sent"]:
            sender(message)
            message["sent"] = True
            count += 1
    return count
