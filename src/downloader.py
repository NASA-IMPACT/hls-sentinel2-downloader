"""
downloader.py
Created On: Jan 28, 2020
Created By: Bibek Dahal
"""
import aria2p


class Downloader:
    """
    Interface to start downloading using aria2 (asynchronously).
    """
    def __init__(
        self,
        on_download_start=None,
        on_download_error=None,
        on_download_complete=None,
        callback_args=[],
    ):
        """
        on_download_start: Callback for when a download starts.
        on_download_error: Callback for when a download fails.
        on_download_complete: Callback for when a download completes.
        """

        self.aria = aria2p.API(
            aria2p.Client(
                host="http://localhost",
                port=6800,
                secret="",
            )
        )

        self.on_download_error = on_download_error
        self.on_download_start = on_download_start
        self.on_download_complete = on_download_complete
        self.callback_args = callback_args

        self.aria.listen_to_notifications(
            threaded=True,
            on_download_start=self._handle_download_start,
            on_download_error=self._handle_download_error,
            on_download_complete=self._handle_download_complete,
        )

    def start_download(self, url):
        """
        Start a new download. This method is asynchronous.

        url: URL to download from.
        """
        self.aria.add_uris([url])

    def get_download_filename(self, gid):
        """
        Get the path of a download file from given id.
        """
        return str(self.aria.get_download(gid).files[0].path)

    def get_download_error(self, gid):
        """
        Get the error message and code for a failed download.
        """
        download = self.aria.get_download(gid)
        return download.error_message, download.error_code

    def stop_listening(self):
        """
        Stop listening for download callbacks.
        """
        self.aria.stop_listening()

    def _handle_download_start(self, aria, gid):
        if self.on_download_start is not None:
            self.on_download_start(self, gid, *self.callback_args)

    def _handle_download_error(self, aria, gid):
        if self.on_download_error is not None:
            self.on_download_error(self, gid, *self.callback_args)

    def _handle_download_complete(self, aria, gid):
        if self.on_download_complete is not None:
            self.on_download_complete(self, gid, *self.callback_args)
