def get_hostname():
    """
    Shamelessly lifted from http://stackoverflow.com/questions/4271740/how-can-i-use-python-to-get-the-system-hostname
    :return: hostname
    """
    import socket
    if socket.gethostname().find('.') >= 0:
        name=socket.gethostname()
    else:
        name=socket.gethostbyaddr(socket.gethostname())[0]
    return name
