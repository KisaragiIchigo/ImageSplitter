import os
from PIL import Image
from utils import SUPPORTED_EXTENSIONS

class ImageProcessor:
    """画像処理のロジックを担当するクラス"""
    def __init__(self, progress_callback=None, status_callback=None, done_callback=None):
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.done_callback = done_callback

    def _split_one_image(self, image_path, split_direction, output_folder):
        """単一の画像を分割して保存します。"""
        try:
            with Image.open(image_path) as image:
                width, height = image.size
                half_width = width // 2

                if split_direction == "left_to_right":
                    part_a = image.crop((0, 0, half_width, height))
                    part_b = image.crop((half_width, 0, width, height))
                else:  # right_to_left
                    part_a = image.crop((half_width, 0, width, height))
                    part_b = image.crop((0, 0, half_width, height))

                file_base, file_ext = os.path.splitext(os.path.basename(image_path))
                filename_a = f"{file_base}_a{file_ext}"
                filename_b = f"{file_base}_b{file_ext}"

                part_a.save(os.path.join(output_folder, filename_a))
                part_b.save(os.path.join(output_folder, filename_b))
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"エラー: {os.path.basename(image_path)} - {e}")

    def _find_image_files(self, items):
        """指定されたパスから画像ファイルのリストを再帰的に検索します。"""
        image_files = []
        for item in items:
            if not item:
                continue
            if os.path.isdir(item):
                for root, _, files in os.walk(item):
                    for file in files:
                        if file.lower().endswith(SUPPORTED_EXTENSIONS):
                            image_files.append(os.path.join(root, file))
            elif os.path.isfile(item) and item.lower().endswith(SUPPORTED_EXTENSIONS):
                image_files.append(item)
        return image_files

    def process_images(self, items, split_direction):
        """指定されたアイテム（ファイル/フォルダ）の画像処理を開始します。"""
        if self.status_callback:
            self.status_callback("ファイルリストを作成中...")

        image_files_to_process = self._find_image_files(items)

        if not image_files_to_process:
            if self.status_callback:
                self.status_callback("対象の画像ファイルが見つかりません。")
            if self.done_callback:
                self.done_callback(False)
            return

        total_files = len(image_files_to_process)
        base_folder = os.path.dirname(image_files_to_process[0]) or "."
        output_folder = os.path.join(base_folder, "half")
        os.makedirs(output_folder, exist_ok=True)

        for index, image_path in enumerate(image_files_to_process, start=1):
            if self.status_callback:
                self.status_callback(f"処理中 ({index}/{total_files}): {os.path.basename(image_path)}")

            self._split_one_image(image_path, split_direction, output_folder)

            if self.progress_callback:
                progress_value = index / total_files
                self.progress_callback(progress_value)

        if self.done_callback:
            self.done_callback(True)
