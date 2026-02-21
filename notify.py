from winotify import Notification, audio


def windows_notify(message: str, title: str = __file__, appid=__file__):
    toast = Notification(app_id=appid, title=title, msg=message)
    toast.set_audio(audio.Default, False)
    toast.show()


if __name__ == "__main__":
    windows_notify("Hello World")
