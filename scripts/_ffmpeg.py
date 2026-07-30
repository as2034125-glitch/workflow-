"""解析 ffmpeg / ffprobe 執行檔位置。

優先用系統安裝版（功能較全，且有 ffprobe）；沒有的話退回 imageio-ffmpeg
內建的 ffmpeg。注意 imageio-ffmpeg 只附 ffmpeg，不含 ffprobe。
"""

import shutil

__all__ = ["FFMPEG", "FFPROBE"]


def _resolve() -> tuple[str, str | None]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg:
        return ffmpeg, ffprobe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe(), ffprobe


FFMPEG, FFPROBE = _resolve()
